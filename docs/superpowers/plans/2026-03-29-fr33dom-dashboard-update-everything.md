# Fr33d0m Dashboard Update Everything Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe `Update Everything` action to the Fr33d0m dashboard that updates the full Fr33d0m/Hermes application stack on the VM without touching the OS or reboot behavior.

**Architecture:** Keep `Update Everything` as a detached, phased background job exposed through the existing dashboard `Runtime Controls` surface. The WebUI backend owns job start/lock/status APIs, while the `Fr33dom_bot` repo owns the on-disk updater script that performs repo sync, Hermes/core and extension refresh, packaged install refresh, staged dashboard refresh, service reload, and post-checks.

**Tech Stack:** FastAPI, Pydantic, pytest, React 19, TypeScript, TanStack Query, Vitest, Python `unittest`, Bash, systemd user services

---

## File Map

### Hermes WebUI backend

- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/webui/routers/admin_actions.py`
- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/webui/schemas/admin_actions.py`
- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/tests/test_admin_actions.py`

### Hermes WebUI frontend

- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/frontend/src/components/admin/RuntimeControls.tsx`
- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/frontend/src/components/admin/RuntimeControls.test.tsx`
- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/frontend/src/api/client.ts`
- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/frontend/src/api/types.ts`

### Fr33dom_bot packaging repo

- Create: `/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/bin/fr33d0m-update-everything`
- Modify: `/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/install.sh`
- Modify: `/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/README.md`
- Modify: `/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/USER_MANUAL.md`
- Modify: `/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/patches/hermes-webui.patch`
- Create: `/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/tests/test_update_everything.py`

## Task 1: Add backend update-everything job APIs and lock semantics

**Files:**
- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/webui/routers/admin_actions.py`
- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/webui/schemas/admin_actions.py`
- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/tests/test_admin_actions.py`

- [ ] **Step 1: Write failing admin-action tests for update job start, status, and lockout**

Add tests for:

```python
def test_update_everything_starts_background_job(client, monkeypatch):
    ...

def test_update_everything_status_returns_phase_payload(client, monkeypatch):
    ...

def test_update_everything_rejects_when_refresh_running(client, monkeypatch):
    ...

def test_update_everything_rejects_when_doctor_running(client, monkeypatch):
    ...

def test_refresh_rejects_when_update_everything_running(client, monkeypatch):
    ...

def test_doctor_rejects_when_update_everything_running(client, monkeypatch):
    ...

def test_doctor_fix_rejects_when_update_everything_running(client, monkeypatch):
    ...

def test_update_everything_marks_stale_job_failed(client, monkeypatch):
    ...
```

- [ ] **Step 2: Run the focused backend test file to confirm the new tests fail**

Run:

```bash
cd "/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors"
.venv/bin/python -m pytest tests/test_admin_actions.py -q
```

Expected: missing route/model fields or lock/status behavior failures

- [ ] **Step 3: Add update job schemas**

Extend `webui/schemas/admin_actions.py` with:

- `UpdateEverythingPhaseStatus`
- `UpdateEverythingStatusResponse`
- any small supporting enums/fields needed for:
  - overall state
  - current phase
  - per-phase state/start/end/summary
  - log output
  - currently running job type for `409` lock responses

Use this concrete payload shape:

```python
class UpdateEverythingPhaseStatus(BaseModel):
    name: str
    state: Literal["pending", "running", "success", "failed", "skipped"]
    started_at: float | None = None
    completed_at: float | None = None
    summary: str = ""


class UpdateEverythingStatusResponse(BaseModel):
    job_type: Literal["update-everything"]
    state: Literal["idle", "running", "success", "partial_failure", "failed"]
    running: bool
    pid: int | None = None
    current_phase: str | None = None
    phases: list[UpdateEverythingPhaseStatus] = Field(default_factory=list)
    started_at: float | None = None
    completed_at: float | None = None
    stale_after_seconds: int = 900
    log: str = ""
```

For start-lock conflicts, use a concrete `409` response body shape such as:

```json
{
  "detail": {
    "code": "job_already_running",
    "job_type": "refresh-dashboard",
    "state": "running"
  }
}
```

Apply that same machine-readable `409` shape consistently to every mutually exclusive start path involved in this feature:

- `POST /api/admin/update-everything`
- `POST /api/admin/dashboard/refresh`
- `POST /api/admin/doctor`

- [ ] **Step 4: Implement detached update job scheduling in `admin_actions.py`**

Add:

- `POST /api/admin/update-everything`
- `GET /api/admin/update-everything/status`
- shared helpers for:
  - status file path
  - log file path
  - lock acquisition
  - stale-job recovery
  - running-job-type detection across `Refresh Dashboard`, `Update Everything`, `Doctor`, and `Doctor Fix`

The detached worker must run the concrete packaged updater at:

```python
Path.home() / ".local" / "bin" / "fr33d0m-update-everything"
```

Run it with the same runtime environment pattern already used for other admin commands (`HERMES_HOME`, local bin on `PATH`, user systemd bus variables).

Use the same detached-process pattern as dashboard refresh, but as a distinct job type and status file.

- [ ] **Step 5: Enforce lock semantics**

Server-side rules to encode:

- `Update Everything` cannot start while refresh is running
- `Update Everything` cannot start while doctor/doctor-fix is running
- refresh cannot start while update-everything is running
- doctor/doctor-fix cannot start while update-everything is running
- return `409` with the active job type in the response detail/body

- [ ] **Step 6: Implement stale job recovery**

Add heartbeat/last-updated handling so a stuck `running` update job is marked `failed` when the worker process is gone and the stale timeout has elapsed.

Use a concrete stale timeout of `900` seconds.

Use a concrete on-disk status contract:

- the backend scheduler creates the JSON status file immediately before/after spawning the detached updater and records `job_type`, `state`, `pid`, `started_at`, and initial `last_updated_at`
- the updater script owns all subsequent updates to `current_phase`, `phases[]`, `state`, `completed_at`, and `last_updated_at`
- it updates `last_updated_at` again immediately before and after any long-running shell command
- stale detection reads `pid`, `state`, and `last_updated_at`

Treat the backend-testing requirement from the spec as satisfied by a combination of:

- WebUI backend API tests in `tests/test_admin_actions.py` for lock/status/start semantics
- Fr33dom_bot updater harness tests in `tests/test_update_everything.py` for phase ordering, failure propagation, and staged dashboard refresh usage

- [ ] **Step 7: Re-run focused admin tests and then the full backend suite**

Run:

```bash
cd "/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors"
.venv/bin/python -m pytest tests/test_admin_actions.py -q
.venv/bin/python -m pytest -q
```

Expected: all tests pass

- [ ] **Step 8: Commit only if explicitly requested later**

Do not commit during implementation unless the user asks.

## Task 2: Create the repo-side `fr33d0m-update-everything` script and harness

**Files:**
- Create: `/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/bin/fr33d0m-update-everything`
- Create: `/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/tests/test_update_everything.py`
- Modify: `/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/install.sh`

- [ ] **Step 1: Write failing Python harness tests for the updater script**

Cover:

```python
def test_update_everything_runs_repo_sync_first(): ...
def test_update_everything_runs_packaged_install_refresh_after_repo_sync(): ...
def test_update_everything_fails_on_dirty_repo_sync(): ...
def test_update_everything_updates_extensions_before_dependency_refresh(): ...
def test_update_everything_calls_staged_dashboard_refresh(): ...
def test_update_everything_stops_after_blocking_phase_failure(): ...
def test_update_everything_restarts_non_webui_services_after_dashboard_refresh(): ...
def test_update_everything_marks_postcheck_degradation_as_partial_failure(): ...
```

Use the same style as `tests/test_refresh_dashboard.py` and `tests/test_install_update_flow.py`: temp dirs, stub commands, command log assertions.

- [ ] **Step 2: Run the harness tests and confirm they fail**

Run:

```bash
cd "/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything"
python3 -m unittest discover -s tests -p 'test_update_everything.py'
```

Expected: script missing / expected commands not yet observed

- [ ] **Step 3: Implement `bin/fr33d0m-update-everything`**

The script should:

1. preflight
2. repo sync (`git -C "$HOME/Fr33dom_bot" fetch origin main` + `git -C "$HOME/Fr33dom_bot" pull --ff-only origin main`)
3. packaged install refresh for repo-owned local assets
4. Hermes core update
5. extension updates
6. dependency refresh
7. staged dashboard refresh via `fr33d0m-refresh-dashboard`
8. non-webui service reload/restart
9. post-checks

Write clear phase logs to stdout for backend log capture.

`bin/fr33d0m-update-everything` is the owner of the phase-progress updates in the JSON status file after the backend scheduler has created the initial record and stored the detached worker `pid`.

Use local-only operations. No OS package updates. No reboot.

- [ ] **Step 4: Decide and encode exact app-layer commands**

Use the smallest practical commands that match the approved design:

- preflight must check local paths, required commands, disk space, and active-job lock state
- packaged install refresh must explicitly run `bash install.sh` in a new packaged-only mode, for example `FR33DOM_INSTALL_MODE=packaged-only bash install.sh`, so repo-owned files (scripts, seeded config, patch artifact, installer-managed assets) are refreshed without duplicating the full update-everything flow
- Hermes core update command is `"$HOME/.local/bin/fr33d0m" update`
- if that CLI command is missing or fails to start, the Hermes core phase fails; it is not treated as a skipped phase
- if the CLI exits `0` and stdout indicates no work was needed (for example a stable, explicit “already up to date” message), the summary should say “no update needed” and the phase records `skipped`
- otherwise, an exit code of `0` records `success`
- extensions update policy: iterate git repos directly under `~/.hermes/extensions`, skip `hermes-webui`, and run `git -C "$repo" pull --ff-only`
- dependency refresh commands are concrete:
  - refresh Hermes core Python environment as needed through the Hermes core update step
  - refresh packaged WebUI backend/frontend dependencies through the packaged install refresh and staged dashboard refresh
  - for extension repos that ship Python requirements or a `pyproject.toml`, run the minimal package-manager refresh required by that repo inside the update script after the git pull for that extension
- service reload must explicitly target:
  - `fr33d0m-gateway.service`
  - `fr33d0m-terminal.service`
  - `fr33d0m-neurovision-web.service`
  and must exclude `fr33d0m-webui.service` here because the staged refresh already owns it
- post-check commands are concrete:
  - `systemctl --user is-active fr33d0m-webui`
  - `systemctl --user is-active fr33d0m-gateway`
  - `systemctl --user is-active fr33d0m-terminal`
  - `systemctl --user is-active fr33d0m-neurovision-web`
  - authenticated request to `http://127.0.0.1:8643/api/health`, with the updater reading the dashboard token from `~/.hermes/auth.json`
- skip rules are fixed:
  - preflight: never skipped
  - repo sync: never skipped
  - packaged install refresh: never skipped
  - Hermes core update: skipped only when the update command reports that no core update is needed
  - extensions update: skipped only when no managed extension repos exist or no updates are needed
  - dependency refresh: skipped only when packaged-install refresh and staged WebUI refresh already covered all required dependency work
  - staged dashboard refresh: never skipped
  - service reload: never skipped
  - post-checks: never skipped

- [ ] **Step 5: Install the new updater in `install.sh`**

Add copy/chmod for `bin/fr33d0m-update-everything` into `~/.local/bin`.

- [ ] **Step 6: Add or update a safe installer path if needed**

Update `install.sh` so it has an explicit packaged-only mode used by `fr33d0m-update-everything`, and make sure already provisioned installs can use the staged-safe update path while fresh installs keep the current bootstrap behavior.

If splitting `install.sh` cleanly into a packaged-only mode proves infeasible, implement the packaged-install-refresh phase directly inside `fr33d0m-update-everything` using the same repo-owned copy/install steps instead of abandoning the phase.

- [ ] **Step 7: Finish `fr33d0m-update-everything` against the packaged-only installer mode**

After Step 6 exists, finish or adjust `bin/fr33d0m-update-everything` so the packaged-install-refresh phase actually calls the now-implemented packaged-only `install.sh` mode rather than depending on a not-yet-existing behavior.

- [ ] **Step 8: Run script harness and shell checks**

Run:

```bash
cd "/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything"
python3 -m unittest discover -s tests -p 'test_*.py'
bash -n install.sh
bash -n bin/fr33d0m-refresh-dashboard
bash -n bin/fr33d0m-update-everything
```

Expected: all pass

## Task 3: Add frontend `Update Everything` button, status polling, and UI states

**Files:**
- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/frontend/src/components/admin/RuntimeControls.tsx`
- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/frontend/src/components/admin/RuntimeControls.test.tsx`
- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/frontend/src/api/client.ts`
- Modify: `/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/frontend/src/api/types.ts`

- [ ] **Step 1: Write failing UI tests for update-everything start, disable, and phase rendering**

Add tests for:

- confirmation before start
- no API call when confirm is cancelled
- disabled button while update is `running`
- phase/status rendering from the polled update-everything status payload
- `409 already running` presentation
- `partial failure` display

- [ ] **Step 2: Run the targeted frontend tests and confirm failure**

Run:

```bash
cd "/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/frontend"
npm test -- --run src/components/admin/RuntimeControls.test.tsx
```

Expected: missing client/types/UI behavior failures

- [ ] **Step 3: Extend API types and client methods**

Add:

- `UpdateEverythingPhaseStatus`
- `UpdateEverythingStatusResponse`
- `adminUpdateEverything()`
- `adminUpdateEverythingStatus()`

- [ ] **Step 4: Update `RuntimeControls.tsx`**

Add:

- `Update Everything` button
- confirmation dialog text
- polling query for update-everything status
- disabled state while running
- phase summary rendering
- rolling log rendering
- distinct handling for `success`, `failed`, and `partial failure`

Preserve the existing refresh/doctor/gateway controls.

- [ ] **Step 5: Keep job-type lock behavior visible**

If the backend returns `409` because another update-style job is active, surface a clear operator-facing message instead of a generic fetch error.

- [ ] **Step 6: Re-run targeted tests, full frontend tests, build, and lint**

Run:

```bash
cd "/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/frontend"
npm test -- --run
npm run build
npm run lint
```

Expected:

- tests pass
- build passes
- lint may still fail on pre-existing unrelated files; if so, note that explicitly and confirm touched files are clean

## Task 4: Sync packaging/docs/patch and run final verification

**Files:**
- Modify: `/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/README.md`
- Modify: `/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/USER_MANUAL.md`
- Modify: `/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/patches/hermes-webui.patch`

- [ ] **Step 1: Update packaging docs**

Document:

- what `Update Everything` updates
- what it explicitly does not update
- no OS updates / no reboot
- no git push/commit flow from the dashboard
- staged safety guarantees and failure reporting

- [ ] **Step 2: Regenerate `patches/hermes-webui.patch` from the final Hermes WebUI worktree**

Run:

```bash
SOURCE_TREE="/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors"
PATCH_OUT="/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything/patches/hermes-webui.patch"
TMP_INDEX="$(mktemp)"
trap 'rm -f "$TMP_INDEX"' EXIT

GIT_INDEX_FILE="$TMP_INDEX" git -C "$SOURCE_TREE" read-tree HEAD
GIT_INDEX_FILE="$TMP_INDEX" git -C "$SOURCE_TREE" add -A
GIT_INDEX_FILE="$TMP_INDEX" git -C "$SOURCE_TREE" diff --cached --binary HEAD > "$PATCH_OUT"

rm -f "$TMP_INDEX"
trap - EXIT
```

Treat this as a working-tree export against the vanilla `HEAD` checkout of the local `hermes-webui` patch source, but stage into a throwaway index first so modified, deleted, and untracked source files are all captured in the generated patch. Regenerate the patch before any optional commit so the packaged patch always reflects the final uncommitted worktree state being tested and shipped.

This packaged patch is intentionally the full current Fr33d0m customization for `hermes-webui`, not an incremental patch that contains only update-everything hunks. Regenerating it from the current customized source worktree is expected to carry forward the already-shipped runtime-editor/dashboard features alongside the new update-everything changes.

- [ ] **Step 3: Final verification**

Run:

```bash
cd "/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors"
.venv/bin/python -m pytest -q

cd "/Users/fr33d0m21/.hermes/extensions/hermes-webui/.worktrees/runtime-editors/frontend"
npm test -- --run
npm run build

cd "/Users/fr33d0m21/Fr33dom_bot/.worktrees/update-everything"
python3 -m unittest discover -s tests -p 'test_*.py'
bash -n install.sh
bash -n bin/fr33d0m-refresh-dashboard
bash -n bin/fr33d0m-update-everything
```

Expected: all relevant feature verification passes

- [ ] **Step 4: If the user later asks for deployment, use the packaged staged updater path on the server**

Do not push or deploy during implementation unless explicitly requested.
