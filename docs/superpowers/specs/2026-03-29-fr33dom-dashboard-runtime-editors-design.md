# Fr33d0m Dashboard Runtime Editors Design

Date: 2026-03-29
Status: Approved for planning

## Summary

Add two new pages to the existing Fr33d0m dashboard:

- `Personality`: a curated editor for the live runtime personality files under `~/.hermes`
- `Files`: a separate file manager for allowlisted local roots with inline text editing and common file actions

This is a runtime-local operator workflow. User-facing editing must never push to git or update GitHub. Changes stay on the VM unless a maintainer later performs repo work outside the dashboard.

## Context

The current Fr33d0m VM dashboard is based on a customized `hermes-webui` install that lives at:

- runtime install: `~/.hermes/extensions/hermes-webui`
- source-of-truth repo: `~/Fr33dom_bot`
- customization patch: `~/Fr33dom_bot/patches/hermes-webui.patch`

The dashboard already provides a branded shell with routes for dashboard, gateway, terminal, neurovision, config, cron, and skills. The next gap is local runtime editing:

- base personality files need a direct editor
- agent-created and downloaded files need a dedicated browser file manager

The user approved a dedicated `Personality` page and a separate `Files` page.

## Goals

- Let operators edit the live runtime personality files without leaving the dashboard
- Provide a separate file manager for local files the agent creates or downloads
- Keep the UX inside the existing Fr33d0m dashboard shell and sidebar
- Restrict all filesystem access to explicit allowlists
- Keep all user-facing changes local to the VM
- Support a local dashboard refresh workflow after maintainers update dashboard code on disk

## Non-goals

- No git commit, push, pull request, or GitHub actions in the dashboard
- No automatic repo sync from runtime personality edits into `~/Fr33dom_bot`
- No arbitrary whole-home filesystem browser
- No backup/history/versioning layer in v1
- No agent-facing editing of every prompt-bearing file in `~/.hermes`

## Core Decisions

### Page split

The feature is split into two first-class routes:

- `/personality`
- `/files`

The personality workflow is guided and curated. The file manager is broader, but still constrained to named allowlisted roots.

### Runtime-only content editing

The dashboard must treat runtime content as local state:

- `Personality` writes only to live files in `~/.hermes`
- `Files` writes only to the local file currently being edited
- `~/Fr33dom_bot` is not modified by user-facing personality editing
- user-facing editing never publishes or pushes anywhere

### No repo access in Files v1

The file manager is for local runtime/operator files, not dashboard source maintenance.

- `file_roots` must not include `~/Fr33dom_bot`
- `file_roots` must not include any parent directory that would indirectly expose `~/Fr33dom_bot`
- repo-owned dashboard code and patch files stay outside the user-facing file manager in v1

### Local deployment model

Dashboard code is still maintained separately from runtime content:

- maintainers may update `~/Fr33dom_bot`
- maintainers may refresh the installed dashboard locally on the VM
- runtime content editing is distinct from dashboard-code deployment

The dashboard may expose a local refresh action for the installed WebUI, but not any remote git workflow.

## User Experience

### Personality page

The `Personality` page is driven by a curated registry rather than filesystem browsing.

Layout:

- left rail: curated personality file list
- main pane: text editor
- top metadata strip: file label, exact runtime path, file type, save state
- actions: `Save`, `Open in Files`, `Copy path`

Behavior:

- only curated entries appear here
- editing is direct-save to the live runtime file
- the UI clearly shows the exact path being edited
- if a file is missing, the page shows a clear missing-file state

Registry entries should be configuration-driven and include:

- id
- label
- runtime path
- file type
- description
- optional ordering/group metadata

The initial registry should start conservative. It must include `~/.hermes/SOUL.md`. Additional base personality files can be added through the registry without changing the page architecture.

### Files page

The `Files` page is a separate operator tool for named local roots.

Layout:

- root picker for allowlisted roots
- folder/file browser pane
- main preview/editor pane
- metadata/action panel

Supported v1 actions:

- browse directories
- preview files
- inline edit text files
- upload files
- create folders
- rename files and folders
- delete files and folders
- download files

Behavior:

- roots come from settings, not ad hoc user input
- non-text files are preview/download only
- text files open in an inline editor
- destructive actions require confirmation
- images may preview inline in v1
- PDFs and other non-text files default to metadata plus download
- personality-managed paths are excluded from normal file browsing and direct editing in `/files`
- if the user reaches a personality-managed path through a stale link or direct request, the backend returns a `managed in Personality` error instead of opening a second editor

## Configuration Model

The dashboard needs one effective runtime config file for its own behavior. This controls what the installed dashboard is allowed to expose, without mixing user content changes into repo edits.

Recommended effective runtime location:

- `~/.hermes/fr33d0m-dashboard.yaml`

Maintainers may seed or refresh this file from `Fr33dom_bot`, but the installed dashboard should read one local runtime config path only.

Recommended config sections:

### Personality registry

Defines exact runtime files shown in `/personality`.

Suggested shape:

```yaml
personality_files:
  - id: soul
    label: SOUL.md
    path: ~/.hermes/SOUL.md
    kind: markdown
    description: Primary runtime persona file
```

### File roots allowlist

Defines named roots shown in `/files`.

Suggested shape:

```yaml
file_roots:
  - id: runtime
    label: Runtime
    path: ~/.hermes
    editable: true
  - id: downloads
    label: Downloads
    path: ~/Downloads
    editable: true
  - id: custom
    label: Custom roots
    path: /some/maintainer-defined/path
    editable: true
```

Rules:

- roots must resolve to local runtime/operator directories only
- roots must not expose `~/Fr33dom_bot` or any parent directory that contains it
- if `~/.hermes` is included, the dashboard must still exclude personality-managed paths from `/files`

This config is for dashboard implementation and deployment, not for end-user live editing.

## Backend Design

Add two new router groups to the WebUI backend.

### Personality router

Responsibilities:

- list curated personality entries
- read one curated file
- save one curated file
- return metadata such as file size, modified time, and path

Proposed endpoints:

- `GET /api/personality`
- `GET /api/personality/:id`
- `PUT /api/personality/:id`

This router never accepts arbitrary file paths from the user. It resolves ids through the curated registry only.

### Files router

Responsibilities:

- list available roots
- browse directories inside a root
- read file metadata
- read text file content
- write text file content
- upload files
- create folders
- rename files and folders
- delete files and folders

Proposed endpoints:

- `GET /api/files/roots`
- `GET /api/files/tree`
- `GET /api/files/content`
- `PUT /api/files/content`
- `POST /api/files/upload`
- `POST /api/files/folder`
- `POST /api/files/rename`
- `DELETE /api/files`

The exact request shape can be finalized in planning, but every request must resolve against a named root plus a relative path, never a freeform absolute path from the client.

### Shared filesystem helper layer

Create a helper module that centralizes:

- root lookup
- path normalization
- path traversal prevention
- text vs binary detection
- max file size checks for inline editing
- hidden path filtering rules
- managed-path exclusion for Personality-owned files
- optimistic concurrency checks based on file revision metadata
- common error formatting

Both routers must use the same helper layer instead of implementing path validation separately.

## Authorization Model

The current dashboard has a single authenticated operator role based on the dashboard token. V1 should keep that model explicit:

- any authenticated dashboard user is treated as a full local operator on that VM
- `Personality` save is allowed for authenticated users
- `Files` CRUD is allowed for authenticated users
- local refresh is allowed for authenticated users, but must require an explicit confirmation step in the UI

There is no separate multi-role permissions model in v1.

## Frontend Design

### Navigation

Add both pages to the existing sidebar in the admin section:

- `Personality`
- `Files`

### Shared editing primitives

Use shared frontend utilities/components where possible:

- file editor pane
- save status banner
- metadata row
- confirmation dialog
- error callout

The `Personality` page should feel simpler and more opinionated than `Files`, even if both reuse the same editor component underneath.

## Local Refresh Workflow

The dashboard may expose a local refresh action for dashboard code maintenance, but it must remain separate from runtime content editing.

This action should:

- run a local, repo-owned refresh command on the VM
- reapply the Fr33d0m customization to the installed WebUI
- rebuild the frontend if needed
- restart `fr33d0m-webui`
- return the logs/status to the UI

This is a local maintenance operation only. It does not commit, push, or pull from a remote.

Success and failure rules:

- the running service must not be restarted until patch/apply/build steps have succeeded
- if refresh fails before restart, the existing running dashboard should remain untouched
- if restart fails after a successful rebuild, the UI must surface that explicitly as a restart failure
- the UI should show stage-by-stage output so operators can see whether the failure happened during apply, build, or restart

## Error Handling

Every filesystem action should return clear operator-facing errors.

Required cases:

- path outside allowed root
- personality id not found
- file missing
- permission denied
- unsupported binary edit
- file too large for inline editing
- file changed on disk since load
- managed in Personality
- invalid rename target
- delete failed
- upload failed
- refresh command failed

The UI should show exact local paths and exact action results wherever that helps the operator understand what happened.

Save semantics:

- both editors should load and display revision metadata such as mtime or a derived revision token
- save requests must include the last-seen revision token
- if the file changed on disk after load, the backend returns a conflict error instead of silently overwriting
- the UI should offer reload and retry rather than last-write-wins without warning

## Security and Safety

- All file access must be root-restricted and path-normalized on the backend
- `Personality` never exposes arbitrary browsing
- dotfiles inside allowed roots may be shown in v1 because operators may need them
- a denylist may still block explicitly sensitive or unsupported paths
- only text files are editable inline
- non-text files remain preview/download only
- delete and rename require explicit confirmation
- direct-save is allowed, but never outside the configured roots
- default v1 inline editing cap is 1 MB per text file
- default v1 upload cap is 50 MB per file

## Testing Strategy

### Backend

Add focused tests for:

- allowed-root enforcement
- relative-path normalization
- personality registry lookup
- missing curated files
- text vs binary handling
- file CRUD edge cases
- local refresh command result handling

### Frontend

Add light workflow tests for:

- opening a curated personality file
- saving a curated file
- browsing an allowlisted root
- editing and saving a text file
- handling save failures cleanly

Manual verification should also cover:

- exact sidebar placement
- path display clarity
- non-text preview behavior
- destructive action confirmations
- local refresh output visibility

## Implementation Notes

- The existing dashboard codebase already has route-based admin pages, shared API client code, and backend routers; this feature should extend those patterns rather than inventing a parallel app
- The curated registry should be easy to expand without changing frontend structure
- The file manager should be powerful enough for operators, but visibly bounded to the configured local roots
- Runtime-local editing and dashboard-code deployment are separate concerns and must remain separate in the UI

## Open Items For Planning

- exact initial curated personality file registry beyond `SOUL.md`
- exact command/script name for the local dashboard refresh action
