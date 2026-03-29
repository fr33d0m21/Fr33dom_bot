# Fr33d0m Dashboard Update Everything Design

Date: 2026-03-29
Status: Approved for planning

## Summary

Add an `Update Everything` control to the existing Fr33d0m dashboard so an authenticated operator can update the full Fr33d0m/Hermes application stack from the dashboard without touching the OS package manager or reboot behavior.

This update flow is app-level only. It must not:

- run Ubuntu package upgrades
- reboot the machine
- commit, push, or otherwise manage git remotes from the dashboard

## Context

The dashboard already has:

- `Runtime Controls` UI
- detached background job handling for `Refresh Dashboard`
- staged `hermes-webui` refresh with status/log reporting
- local packaging and update flow rooted in `~/Fr33domBot`

The user wants a single dashboard button that updates the Fr33d0m/Hermes software stack, including:

- `Fr33dom_bot` repo state on the server
- packaged dashboard/WebUI updates
- Python and Node dependencies
- Hermes extension repos
- Hermes core install
- relevant systemd user services

But explicitly not:

- OS package updates
- automatic reboot

## Goals

- Provide one operator-facing `Update Everything` action in the dashboard
- Update the full Fr33d0m/Hermes application stack on the VM
- Run as a detached background job with live phase/log polling
- Surface exact phase progress and failures in the UI
- Prevent concurrent update-style jobs from overlapping
- Keep the current running dashboard safe until an updated stack is ready to switch over

## Non-goals

- No `apt upgrade`, kernel updates, or other OS-level package changes
- No reboot orchestration
- No git push, PR creation, or remote repo management from the dashboard
- No false “atomic” guarantee across every repo, dependency, and service in the stack

## Placement

Add `Update Everything` to the existing `Runtime Controls` card in the dashboard.

Buttons in that control surface become:

- `Start`
- `Stop`
- `Restart`
- `Refresh Dashboard`
- `Update Everything`
- `Doctor`
- `Doctor Fix`

`Update Everything` uses the same detached-job pattern as dashboard refresh:

- explicit confirmation before start
- backend starts a background job and returns immediately
- UI polls status/log output
- control stays disabled while the update job is active

This keeps the operator workflow simple: one button, one status surface, and one source of truth for update progress.

## Update Scope

The update job covers these app-level layers:

1. `Fr33dom_bot` repo sync on the server
2. packaged install refresh
3. Hermes core update
4. Hermes extensions update
5. Python and Node dependency refresh for the packaged stack
6. staged dashboard/WebUI refresh
7. service reload/restart
8. post-update health checks

It does not cover Ubuntu package management.

## Job Model

`Update Everything` is a separate background job type from `Refresh Dashboard`.

Each job has its own:

- status file
- log file
- lifecycle state

Only one update-style job may run at a time:

- if `Refresh Dashboard` is running, `Update Everything` cannot start
- if `Update Everything` is running, `Refresh Dashboard` cannot start
- if `Doctor` or `Doctor Fix` is running, `Update Everything` cannot start
- if `Update Everything` is running, `Doctor` and `Doctor Fix` cannot start

This lockout must be enforced server-side, not only in the UI.

If a second start request is made while an update-style job is already active, the backend returns `409` and includes which job type is currently running.

## Stale Job Recovery

The job system must handle interrupted or stale runs safely.

Required behavior:

- every active job writes a heartbeat or last-updated timestamp
- if a job is marked `running` but its worker process is gone and no heartbeat/log progress has occurred within the stale timeout window, the backend marks it `failed`
- the status payload must let the UI distinguish between a truly running job and a stale/failed one

The exact timeout can be finalized in planning, but stale-job recovery itself is required.

## Phase Pipeline

The update pipeline runs in this order:

### 1. Preflight

Check:

- required local paths exist
- expected commands are available
- enough disk space is available for staging
- no other update-style job is running

If preflight fails, the job ends immediately with a failed state.

### 2. Repo Sync

Refresh `~/Fr33dom_bot` on the server with a fast-forward-only update.

Expected work:

- fetch latest origin state
- pull latest `main`

If this phase fails, later phases do not run.

Dirty-tree or non-fast-forward rules:

- if `~/Fr33dom_bot` has local modifications that would prevent a fast-forward update, this phase fails immediately
- the updater does not stash, reset, or auto-merge repo state during `Repo Sync`
- the phase summary must make the failure reason explicit

### 3. Packaged Install Refresh

Refresh the packaged local assets from the repo:

- scripts
- seeded runtime config
- packaged patch artifact
- docs/assets as needed

This keeps the runtime packaging side consistent before deeper updates run.

### 4. Hermes Core Update

Update the Hermes Agent core install when a newer local target is available or when the packaged update flow requires it.

The exact command can be finalized in planning, but this phase must be explicit and separately logged.

### 5. Extensions Update

Update cloned extension repos under `~/.hermes/extensions`.

Each extension update should be logged clearly enough that operators can see which extension failed if one update breaks.

This phase runs before dependency refresh so the dependency step can refresh against the final checked-out extension code rather than stale repos.

### 6. Dependency Refresh

Refresh:

- Python dependencies
- Node dependencies

for the packaged Fr33d0m/Hermes stack as required by the updated code.

### 7. Dashboard/WebUI Refresh

Use the existing staged dashboard refresh path:

- prepare updated `hermes-webui` in staging
- apply packaged patch in staging
- refresh backend dependencies in staging
- build frontend in staging
- swap live tree only at the end
- restart only `fr33d0m-webui`
- attempt rollback on failed post-swap startup

This phase must not fall back to mutating the running live tree in place.

### 8. Service Reload

Restart or reload the relevant user services:

- `fr33d0m-gateway`
- `fr33d0m-terminal`
- `fr33d0m-neurovision-web`

These should run as late as possible.

`fr33d0m-webui` is intentionally excluded from phase 8 because phase 7 already owns the staged swap and restart for the dashboard itself.

### 9. Post-checks

Run health/status checks after the update:

- dashboard health endpoint
- service activity checks
- any lightweight runtime sanity checks chosen in planning

## Failure Model

This is a phased best-effort job, not a full-stack atomic transaction.

Rules:

- every phase has `pending`, `running`, `success`, `failed`, or `skipped`
- if a required phase fails, the job stops there
- later phases do not continue after a blocking failure
- the final job state is one of:
  - `success`
  - `partial failure`
  - `failed`

Use `partial failure` when some work completed successfully but one or more non-terminal parts still require operator attention.

Default interpretation:

- blocking failure in phases 1-8 => `failed`
- post-check degradation after earlier phases succeed => `partial failure`
- explicitly optional/skipped work may still yield `success` if the resulting stack is healthy

## Status and Log Reporting

The backend should persist:

- overall state
- current phase
- per-phase timestamps
- per-phase summaries
- rolling log output

Each phase should record:

- phase name
- start time
- end time
- state
- short summary line

Skip rules:

- `Preflight`: never skipped
- `Repo Sync`: never skipped
- `Packaged Install Refresh`: never skipped
- `Hermes Core Update`: skipped only if no update is needed
- `Extensions Update`: skipped only if no managed extensions exist or no updates are needed
- `Dependency Refresh`: skipped only if dependency refresh is provably unnecessary
- `Dashboard/WebUI Refresh`: never skipped
- `Service Reload`: never skipped
- `Post-checks`: never skipped

The UI should poll a single update-status endpoint and render:

- overall job state
- current phase
- per-phase progress summary
- log stream

Unlike the earlier refresh button behavior, the operator should be able to understand where the updater is in the pipeline without reading opaque shell output only.

## UI Behavior

The `Update Everything` UX should be:

1. click button
2. confirmation dialog summarizes scope
3. backend schedules detached update job
4. button becomes disabled while the update is running
5. status area shows:
   - running state
   - current phase
   - completed phases
   - live log output
6. final state remains visible after completion

If a second operator tries to start another update while one is active, the UI should show a clear “already running” message.

## Safety Constraints

- app-level only, no OS updates
- no reboot
- no remote git management from the dashboard
- no overlapping update jobs
- no fallback to in-place dashboard rebuilds for the update path
- current live dashboard should remain untouched until the staged replacement is ready

## Testing Strategy

### Backend

Add tests for:

- update job lockout against active `Refresh Dashboard`
- update job lockout against active `Update Everything`
- phase ordering
- phase failure propagation
- status/log payload shape
- staged dashboard refresh still used in the update pipeline

### Frontend

Add tests for:

- confirmation before start
- disabled button while running
- status polling updates
- success display
- failure display
- partial failure display

### Integration

Add a lightweight local harness where practical to verify:

- existing install path uses the staged refresh path for already provisioned dashboards
- update flow does not mutate the running dashboard tree until swap time
- service checks run after the update job

## Open Items For Planning

- exact command(s) used for Hermes core update
- exact policy for updating each extension repo
- which phase failures are `failed` vs `partial failure`
- exact shape of the update status file and API payload
- whether service restarts happen individually per phase or once near the end
