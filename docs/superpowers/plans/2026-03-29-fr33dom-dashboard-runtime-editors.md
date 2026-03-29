# Fr33d0m Dashboard Runtime Editors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add runtime-local `Personality` and `Files` pages to the Fr33d0m dashboard, plus a local dashboard refresh action, without exposing git or remote publish workflows.

**Architecture:** Extend the existing patched `hermes-webui` install in `~/.hermes/extensions/hermes-webui` with two new backend routers, a shared safe-filesystem helper, and two new React routes. Seed runtime behavior from a local YAML config at `~/.hermes/fr33d0m-dashboard.yaml`, keep user-facing edits strictly local to runtime roots, and package the new maintenance command plus config seed in `~/Fr33dom_bot`.

**Tech Stack:** FastAPI, Pydantic, pytest, React 19, TypeScript, TanStack Query, Vite, Vitest, Testing Library, shell scripts, local systemd restart via existing runtime command model

---

## File Map

### Repo-managed files

- Create: `~/Fr33dom_bot/config/fr33d0m-dashboard.yaml`
- Create: `~/Fr33dom_bot/bin/fr33d0m-refresh-dashboard`
- Modify: `~/Fr33dom_bot/install.sh`
- Modify: `~/Fr33dom_bot/.gitignore`
- Modify: `~/Fr33dom_bot/README.md`
- Modify: `~/Fr33dom_bot/USER_MANUAL.md`
- Modify: `~/Fr33dom_bot/patches/hermes-webui.patch`

### Backend files in installed `hermes-webui`

- Create: `~/.hermes/extensions/hermes-webui/webui/dashboard_settings.py`
- Create: `~/.hermes/extensions/hermes-webui/webui/runtime_fs.py`
- Create: `~/.hermes/extensions/hermes-webui/webui/routers/personality.py`
- Create: `~/.hermes/extensions/hermes-webui/webui/routers/files.py`
- Create: `~/.hermes/extensions/hermes-webui/webui/schemas/personality.py`
- Create: `~/.hermes/extensions/hermes-webui/webui/schemas/files.py`
- Modify: `~/.hermes/extensions/hermes-webui/webui/routers/admin_actions.py`
- Modify: `~/.hermes/extensions/hermes-webui/webui/schemas/admin_actions.py`
- Modify: `~/.hermes/extensions/hermes-webui/webui/server.py`

### Frontend files in installed `hermes-webui`

- Create: `~/.hermes/extensions/hermes-webui/frontend/src/pages/Personality.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/pages/Files.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/components/editor/TextFileEditor.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/components/personality/PersonalityEntryList.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/components/files/FileBrowser.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/components/files/FileMetadataPanel.tsx`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/App.tsx`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/components/layout/Sidebar.tsx`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/components/admin/RuntimeControls.tsx`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/api/client.ts`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/api/types.ts`

### Test files

- Modify: `~/.hermes/extensions/hermes-webui/tests/conftest.py`
- Create: `~/.hermes/extensions/hermes-webui/tests/test_dashboard_settings.py`
- Create: `~/.hermes/extensions/hermes-webui/tests/test_runtime_fs.py`
- Create: `~/.hermes/extensions/hermes-webui/tests/test_personality_router.py`
- Create: `~/.hermes/extensions/hermes-webui/tests/test_files_router.py`
- Create: `~/.hermes/extensions/hermes-webui/tests/test_admin_actions.py`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/package.json`
- Create: `~/.hermes/extensions/hermes-webui/frontend/vitest.config.ts`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/test/setup.ts`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/test/test-utils.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/pages/Personality.test.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/pages/Files.test.tsx`

## Task 1: Add runtime dashboard settings and safe filesystem foundation

**Files:**
- Modify: `~/.hermes/extensions/hermes-webui/tests/conftest.py`
- Create: `~/.hermes/extensions/hermes-webui/tests/test_dashboard_settings.py`
- Create: `~/.hermes/extensions/hermes-webui/tests/test_runtime_fs.py`
- Create: `~/.hermes/extensions/hermes-webui/webui/dashboard_settings.py`
- Create: `~/.hermes/extensions/hermes-webui/webui/runtime_fs.py`

- [ ] **Step 1: Write the failing settings tests**

```python
def test_dashboard_settings_reads_runtime_yaml(tmp_path, monkeypatch):
    cfg = tmp_path / ".hermes" / "fr33d0m-dashboard.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        "personality_files:\n"
        "  - id: soul\n"
        "    label: SOUL.md\n"
        "    path: ~/.hermes/SOUL.md\n"
        "    kind: markdown\n"
        "file_roots:\n"
        "  - id: runtime\n"
        "    label: Runtime\n"
        "    path: ~/.hermes\n"
        "    editable: true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(cfg.parent))

    from webui.dashboard_settings import get_dashboard_settings

    data = get_dashboard_settings()
    assert data.personality_files[0].id == "soul"
    assert data.file_roots[0].id == "runtime"
```

- [ ] **Step 2: Write the failing filesystem tests**

```python
def test_resolve_root_path_blocks_escape(tmp_path):
    from webui.runtime_fs import resolve_relative_path, RuntimeRoot

    root = RuntimeRoot(id="runtime", label="Runtime", path=tmp_path, editable=True)
    resolve_relative_path(root, "notes/todo.md")

    with pytest.raises(ValueError):
        resolve_relative_path(root, "../secrets.txt")
```

```python
def test_rejects_repo_root_or_parent(tmp_path):
    from webui.runtime_fs import validate_root_path

    repo_root = tmp_path / "Fr33dom_bot"
    repo_root.mkdir()

    with pytest.raises(ValueError):
        validate_root_path(repo_root, repo_root)

    with pytest.raises(ValueError):
        validate_root_path(tmp_path, repo_root)
```

```python
def test_personality_paths_are_hidden_from_files(tmp_path):
    from webui.runtime_fs import build_managed_path_set

    managed = build_managed_path_set([tmp_path / "SOUL.md"])
    assert (tmp_path / "SOUL.md").resolve() in managed
```

- [ ] **Step 3: Run the backend tests to verify they fail**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui"
python -m pytest tests/test_dashboard_settings.py tests/test_runtime_fs.py -q
```

Expected: `ImportError` or `ModuleNotFoundError` for `webui.dashboard_settings` / `webui.runtime_fs`

- [ ] **Step 4: Extend the test fixture with runtime config and personality files**

Add to `tests/conftest.py`:

```python
# Keep the existing config.yaml fixture from temp_hermes_home; add the runtime-editor files below.
(hermes_home / "SOUL.md").write_text("# Fr33d0m Agent\n\nStay local.\n", encoding="utf-8")
(hermes_home / "fr33d0m-dashboard.yaml").write_text(
    yaml.dump(
        {
            "personality_files": [
                {
                    "id": "soul",
                    "label": "SOUL.md",
                    "path": str(hermes_home / "SOUL.md"),
                    "kind": "markdown",
                    "description": "Primary runtime persona file",
                }
            ],
            "file_roots": [
                {"id": "runtime", "label": "Runtime", "path": str(hermes_home), "editable": True},
                {"id": "downloads", "label": "Downloads", "path": str(tmp_path / "Downloads"), "editable": True},
            ],
        }
    ),
    encoding="utf-8",
)
(tmp_path / "Downloads").mkdir()
```

- [ ] **Step 5: Implement the minimal settings loader**

Create `webui/dashboard_settings.py`:

```python
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from webui.hermes_bridge import HERMES_HOME


class PersonalityEntry(BaseModel):
    id: str
    label: str
    path: str
    kind: str
    description: str = ""


class FileRootEntry(BaseModel):
    id: str
    label: str
    path: str
    editable: bool = True


class DashboardSettings(BaseModel):
    personality_files: list[PersonalityEntry] = Field(default_factory=list)
    file_roots: list[FileRootEntry] = Field(default_factory=list)


def get_dashboard_settings_path() -> Path:
    return HERMES_HOME / "fr33d0m-dashboard.yaml"


def get_dashboard_settings() -> DashboardSettings:
    path = get_dashboard_settings_path()
    if not path.exists():
        return DashboardSettings()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return DashboardSettings.model_validate(data)
```

- [ ] **Step 6: Implement the minimal safe-filesystem helper**

Create `webui/runtime_fs.py`:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RuntimeRoot:
    id: str
    label: str
    path: Path
    editable: bool = True


def resolve_relative_path(root: RuntimeRoot, relative_path: str) -> Path:
    candidate = (root.path / relative_path).resolve()
    if root.path.resolve() not in candidate.parents and candidate != root.path.resolve():
        raise ValueError("outside allowed root")
    return candidate


def build_managed_path_set(paths: list[Path]) -> set[Path]:
    return {path.resolve() for path in paths}
```

- [ ] **Step 7: Add the rest of the helper behavior needed by the spec**

Extend `webui/runtime_fs.py` to cover:

- revision token generation from `stat().st_mtime_ns`
- text/binary detection
- dotfile handling
- root lookup by id
- managed-path exclusion
- max inline-edit size checks
- symlink resolution that still enforces final resolved location under the allowed root
- root validation that rejects `~/Fr33dom_bot` and any parent directory that would expose it

- [ ] **Step 8: Run the backend tests and make sure they pass**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui"
python -m pytest tests/test_dashboard_settings.py tests/test_runtime_fs.py -q
```

Expected: `2 passed` (or more, depending on added cases)

- [ ] **Step 9: Create a checkpoint commit if the user explicitly asked for commits**

```bash
git -C "$HOME/.hermes/extensions/hermes-webui" add tests/conftest.py tests/test_dashboard_settings.py tests/test_runtime_fs.py webui/dashboard_settings.py webui/runtime_fs.py
git -C "$HOME/.hermes/extensions/hermes-webui" commit -m "feat: add dashboard runtime settings foundation"
```

## Task 2: Build the `Personality` backend API with conflict-aware saves

**Files:**
- Create: `~/.hermes/extensions/hermes-webui/webui/schemas/personality.py`
- Create: `~/.hermes/extensions/hermes-webui/webui/routers/personality.py`
- Modify: `~/.hermes/extensions/hermes-webui/webui/server.py`
- Create: `~/.hermes/extensions/hermes-webui/tests/test_personality_router.py`

- [ ] **Step 1: Write the failing router tests**

```python
def test_list_personality_entries(client):
    response = client.get("/api/personality")
    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["id"] == "soul"
    assert data["items"][0]["path"].endswith("SOUL.md")
```

```python
def test_update_personality_file(client):
    detail = client.get("/api/personality/soul").json()
    response = client.put(
        "/api/personality/soul",
        json={"content": "# Updated soul\n", "revision": detail["revision"]},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert client.get("/api/personality/soul").json()["content"] == "# Updated soul\n"
```

```python
def test_update_personality_rejects_stale_revision(client):
    response = client.put(
        "/api/personality/soul",
        json={"content": "stale", "revision": "old-token"},
    )
    assert response.status_code == 409
```

- [ ] **Step 2: Run the router tests to verify they fail**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui"
python -m pytest tests/test_personality_router.py -q
```

Expected: route not found / import error

- [ ] **Step 3: Add personality response models**

Create `webui/schemas/personality.py`:

```python
from pydantic import BaseModel, Field


class PersonalityListItem(BaseModel):
    id: str
    label: str
    path: str
    kind: str
    description: str = ""
    exists: bool
    size_bytes: int | None = None
    modified_at: str | None = None


class PersonalityListResponse(BaseModel):
    items: list[PersonalityListItem] = Field(default_factory=list)


class PersonalityDetailResponse(PersonalityListItem):
    content: str
    revision: str


class PersonalityUpdateRequest(BaseModel):
    content: str
    revision: str


class PersonalityUpdateResponse(BaseModel):
    success: bool
    id: str
    path: str
    revision: str
```

- [ ] **Step 4: Implement the minimal personality router**

Create `webui/routers/personality.py`:

```python
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from webui.auth import require_auth
from webui.dashboard_settings import get_dashboard_settings
from webui.runtime_fs import read_text_file, write_text_file_with_revision
from webui.schemas.personality import (
    PersonalityDetailResponse,
    PersonalityListResponse,
    PersonalityListItem,
    PersonalityUpdateRequest,
    PersonalityUpdateResponse,
)

router = APIRouter(prefix="/api/personality", tags=["personality"], dependencies=[Depends(require_auth)])


@router.get("", response_model=PersonalityListResponse)
async def list_personality():
    items = []
    for entry in get_dashboard_settings().personality_files:
        target = Path(entry.path).expanduser()
        stat = target.stat() if target.exists() else None
        items.append(
            PersonalityListItem(
                **entry.model_dump(),
                exists=target.exists(),
                size_bytes=stat.st_size if stat else None,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat() if stat else None,
            )
        )
    return PersonalityListResponse(items=items)
```

- [ ] **Step 5: Implement detail + save with revision checks**

Complete the router with:

- `GET /api/personality/{entry_id}`
- `PUT /api/personality/{entry_id}`
- `404` for unknown ids
- `exists=false` plus metadata fields in list responses when a registry entry is missing on disk
- `404` or a clear missing-file detail response when a requested curated file is absent
- `409` for stale revisions
- `400` / `500` for invalid writes

Use `read_text_file()` / `write_text_file_with_revision()` from `webui.runtime_fs` so the logic stays shared.

- [ ] **Step 6: Register the router in the FastAPI app**

Modify `webui/server.py`:

```python
from webui.routers import admin_actions, config_editor, cron, gateway_config, gateway_status, health, personality, search, sessions, skills

app.include_router(personality.router)
```

For this task, only import/register `personality.router`; `files.router` comes in Task 3.

- [ ] **Step 7: Run the personality backend tests and make sure they pass**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui"
python -m pytest tests/test_personality_router.py -q
```

Expected: `3 passed` (or the updated count)

- [ ] **Step 8: Create a checkpoint commit if the user explicitly asked for commits**

```bash
git -C "$HOME/.hermes/extensions/hermes-webui" add tests/test_personality_router.py webui/schemas/personality.py webui/routers/personality.py webui/server.py
git -C "$HOME/.hermes/extensions/hermes-webui" commit -m "feat: add personality runtime api"
```

## Task 3: Build the allowlisted `Files` backend API

**Files:**
- Create: `~/.hermes/extensions/hermes-webui/webui/schemas/files.py`
- Create: `~/.hermes/extensions/hermes-webui/webui/routers/files.py`
- Modify: `~/.hermes/extensions/hermes-webui/webui/server.py`
- Create: `~/.hermes/extensions/hermes-webui/tests/test_files_router.py`

- [ ] **Step 1: Write the failing file API tests**

```python
def test_list_file_roots(client):
    response = client.get("/api/files/roots")
    assert response.status_code == 200
    assert {root["id"] for root in response.json()["roots"]} == {"runtime", "downloads"}
```

```python
def test_read_file_content(client):
    response = client.get("/api/files/content", params={"root_id": "runtime", "path": "config.yaml"})
    assert response.status_code == 200
    assert "model" in response.json()["content"]
```

```python
def test_reject_escape_and_managed_path(client):
    blocked = client.get("/api/files/content", params={"root_id": "runtime", "path": "../config.yaml"})
    assert blocked.status_code == 400

    managed = client.get("/api/files/content", params={"root_id": "runtime", "path": "SOUL.md"})
    assert managed.status_code in {400, 409}
```

- [ ] **Step 2: Run the files router tests to verify they fail**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui"
python -m pytest tests/test_files_router.py -q
```

Expected: route not found / import error

- [ ] **Step 3: Add file API schemas**

Create `webui/schemas/files.py`:

```python
from pydantic import BaseModel, Field


class FileRootInfo(BaseModel):
    id: str
    label: str
    path: str
    editable: bool


class FileNode(BaseModel):
    name: str
    path: str
    node_type: str
    size: int | None = None


class FileRootsResponse(BaseModel):
    roots: list[FileRootInfo] = Field(default_factory=list)


class FileContentResponse(BaseModel):
    root_id: str
    path: str
    absolute_path: str
    content: str
    revision: str
    content_type: str | None = None
```

- [ ] **Step 4: Implement the minimal files router**

Create `webui/routers/files.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query

from webui.auth import require_auth
from webui.dashboard_settings import get_dashboard_settings
from webui.runtime_fs import get_root_by_id, list_directory, read_text_file
from webui.schemas.files import FileContentResponse, FileRootsResponse, FileRootInfo

router = APIRouter(prefix="/api/files", tags=["files"], dependencies=[Depends(require_auth)])


@router.get("/roots", response_model=FileRootsResponse)
async def list_roots():
    roots = [
        FileRootInfo(**root.model_dump())
        for root in get_dashboard_settings().file_roots
    ]
    return FileRootsResponse(roots=roots)
```

- [ ] **Step 5: Add tree/content/write/upload/folder/rename/delete endpoints**

Implement:

- `GET /api/files/tree?root_id=...&path=...`
- `GET /api/files/content?root_id=...&path=...`
- `GET /api/files/download?root_id=...&path=...`
- `PUT /api/files/content`
- `POST /api/files/upload`
- `POST /api/files/folder`
- `POST /api/files/rename`
- `DELETE /api/files`

Rules to enforce in code:

- all requests resolve `root_id` + relative path
- deny traversal outside resolved root
- deny access to Personality-managed runtime paths
- inline editing only for UTF-8 text files under the size cap
- reject uploads larger than 50 MB
- allow dotfiles inside allowed roots
- return explicit errors for `managed in Personality`, binary, too large, or permission denied

- [ ] **Step 6: Register the files router**

Modify `webui/server.py` to include `files.router` after the import and before SPA fallback.

- [ ] **Step 7: Run the files backend tests and make sure they pass**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui"
python -m pytest tests/test_files_router.py -q
```

Expected: all file API tests pass

- [ ] **Step 8: Create a checkpoint commit if the user explicitly asked for commits**

```bash
git -C "$HOME/.hermes/extensions/hermes-webui" add tests/test_files_router.py webui/schemas/files.py webui/routers/files.py webui/server.py
git -C "$HOME/.hermes/extensions/hermes-webui" commit -m "feat: add allowlisted file manager api"
```

## Task 4: Add the local dashboard refresh command and admin endpoint

**Files:**
- Create: `~/Fr33dom_bot/bin/fr33d0m-refresh-dashboard`
- Modify: `~/Fr33dom_bot/install.sh`
- Modify: `~/.hermes/extensions/hermes-webui/webui/schemas/admin_actions.py`
- Modify: `~/.hermes/extensions/hermes-webui/webui/routers/admin_actions.py`
- Create: `~/.hermes/extensions/hermes-webui/tests/test_admin_actions.py`

- [ ] **Step 1: Write the failing admin refresh test**

```python
def test_dashboard_refresh_action(client, monkeypatch):
    import webui.routers.admin_actions as admin_actions

    def fake_run_local_command(action, command, timeout=180):
        assert action == "dashboard:refresh"
        assert command[-1].endswith("fr33d0m-refresh-dashboard")
        return admin_actions.CommandActionResponse(
            success=True,
            action=action,
            exit_code=0,
            stdout="apply ok\nbuild ok\nrestart ok",
            stderr="",
        )

    monkeypatch.setattr(admin_actions, "_run_local_command", fake_run_local_command)
    response = client.post("/api/admin/dashboard/refresh")
    assert response.status_code == 200
    assert response.json()["success"] is True
```

- [ ] **Step 2: Run the admin action test to verify it fails**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui"
python -m pytest tests/test_admin_actions.py -q
```

Expected: route not found

- [ ] **Step 3: Add the local refresh shell command**

Create `~/Fr33dom_bot/bin/fr33d0m-refresh-dashboard`:

```bash
#!/usr/bin/env bash
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
REPO_DIR="${FR33DOM_BOT_DIR:-$HOME/Fr33dom_bot}"
TARGET_DIR="$HERMES_HOME/extensions/hermes-webui"
PATCH_FILE="$REPO_DIR/patches/hermes-webui.patch"

echo "[refresh] resetting installed hermes-webui clone"
git -C "$TARGET_DIR" reset --hard HEAD
git -C "$TARGET_DIR" clean -fd

echo "[refresh] applying Fr33d0m patch"
git -C "$TARGET_DIR" apply --whitespace=nowarn "$PATCH_FILE"

echo "[refresh] building frontend"
(cd "$TARGET_DIR/frontend" && npm install --silent && npx vite build)

echo "[refresh] restarting fr33d0m-webui"
systemctl --user restart fr33d0m-webui
```

- [ ] **Step 4: Install the refresh command from `install.sh`**

Modify `~/Fr33dom_bot/install.sh` so it copies the new script into `~/.local/bin`:

```bash
cp "$SCRIPT_DIR/bin/fr33d0m-refresh-dashboard" "$LOCAL_BIN/fr33d0m-refresh-dashboard"
chmod +x "$LOCAL_BIN/fr33d0m-refresh-dashboard"
```

- [ ] **Step 5: Add the admin refresh endpoint**

Modify `webui/routers/admin_actions.py`:

```python
@router.post("/dashboard/refresh", response_model=CommandActionResponse)
async def dashboard_refresh() -> CommandActionResponse:
    refresh_script = Path.home() / ".local" / "bin" / "fr33d0m-refresh-dashboard"
    return _run_local_command("dashboard:refresh", [str(refresh_script)], timeout=600)
```

If `admin_actions.py` does not already have `_run_local_command()`, add it once and reuse it for this endpoint instead of duplicating subprocess logic inline.

- [ ] **Step 6: Reuse the existing action schema**

Do not create a new response model. Keep `CommandActionResponse` for refresh logs so `stdout` / `stderr` can already power the UI.

- [ ] **Step 7: Run the admin tests and shell syntax checks**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui"
python -m pytest tests/test_admin_actions.py -q

bash -n "$HOME/Fr33dom_bot/bin/fr33d0m-refresh-dashboard"
bash -n "$HOME/Fr33dom_bot/install.sh"
```

Expected: pytest passes and both shell files produce no syntax output

- [ ] **Step 8: Create a checkpoint commit if the user explicitly asked for commits**

```bash
git -C "$HOME/.hermes/extensions/hermes-webui" add tests/test_admin_actions.py webui/routers/admin_actions.py webui/schemas/admin_actions.py
git -C "$HOME/.hermes/extensions/hermes-webui" commit -m "feat: add local dashboard refresh action"
```

## Task 5: Add frontend test harness, API types, routes, and navigation

**Files:**
- Modify: `~/.hermes/extensions/hermes-webui/frontend/package.json`
- Create: `~/.hermes/extensions/hermes-webui/frontend/vitest.config.ts`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/test/setup.ts`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/test/test-utils.tsx`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/api/client.ts`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/api/types.ts`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/components/admin/RuntimeControls.tsx`

- [ ] **Step 1: Add the frontend test tooling**

In `frontend/package.json`, add:

```json
{
  "scripts": {
    "test": "vitest"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "latest",
    "@testing-library/react": "latest",
    "jsdom": "latest",
    "vitest": "latest"
  }
}
```

Then install them with:

```bash
cd "$HOME/.hermes/extensions/hermes-webui/frontend"
npm install
```

- [ ] **Step 2: Create the Vitest setup files**

Create `frontend/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
})
```

Create `frontend/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom'
```

- [ ] **Step 3: Create the shared render helper**

Create `frontend/src/test/test-utils.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { render } from '@testing-library/react'

export function renderWithAppProviders(ui: React.ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}
```

- [ ] **Step 4: Write a failing refresh-control smoke test**

Write a small test that asserts `RuntimeControls` renders a `Refresh Dashboard` action and prompts before calling `api.adminDashboardRefresh()`.

Example stub:

```tsx
vi.mock('../api/client', () => ({
  api: {
    health: vi.fn().mockResolvedValue({ status: 'ok', version: '1.0.0' }),
    adminDashboardRefresh: vi.fn(),
  },
}))
```

- [ ] **Step 5: Run the frontend tests to verify they fail**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui/frontend"
npm run test -- --run
```

Expected: missing API client methods, missing refresh control, or failing confirmation assertions

- [ ] **Step 6: Add the shared API methods and types**

Modify `frontend/src/api/types.ts` to add types like:

```ts
export interface PersonalityListItem { id: string; label: string; path: string; kind: string; description: string; exists: boolean }
export interface PersonalityListResponse { items: PersonalityListItem[] }
export interface PersonalityDetailResponse extends PersonalityListItem { content: string; revision: string }
export interface PersonalityUpdateResponse { success: boolean; id: string; path: string; revision: string }
export interface FileRootInfo { id: string; label: string; path: string; editable: boolean }
export interface FileRootsResponse { roots: FileRootInfo[] }
export interface FileTreeResponse { root_id: string; path: string; entries: Array<{ name: string; path: string; node_type: string; size?: number }> }
export interface FileContentResponse { root_id: string; path: string; absolute_path: string; content: string; revision: string; content_type?: string | null }
export interface FileWriteResponse { success: boolean; root_id: string; path: string; revision: string }
```

Modify `frontend/src/api/client.ts` to add:

```ts
personalityList: () => request<import('./types').PersonalityListResponse>('/personality'),
personalityDetail: (id: string) => request<import('./types').PersonalityDetailResponse>(`/personality/${id}`),
updatePersonality: (id: string, payload: { content: string; revision: string }) =>
  request<import('./types').PersonalityUpdateResponse>(`/personality/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
fileRoots: () => request<import('./types').FileRootsResponse>('/files/roots'),
fileTree: (rootId: string, path = '') => request<import('./types').FileTreeResponse>(`/files/tree?root_id=${encodeURIComponent(rootId)}&path=${encodeURIComponent(path)}`),
fileContent: (rootId: string, path: string) => request<import('./types').FileContentResponse>(`/files/content?root_id=${encodeURIComponent(rootId)}&path=${encodeURIComponent(path)}`),
updateFileContent: (payload: { root_id: string; path: string; content: string; revision: string }) =>
  request<import('./types').FileWriteResponse>('/files/content', { method: 'PUT', body: JSON.stringify(payload) }),
adminDashboardRefresh: () => request<import('./types').CommandActionResponse>('/admin/dashboard/refresh', { method: 'POST' }),
```

Before Task 7 is considered complete, extend `client.ts` and `types.ts` for the full file-manager action set:

- `downloadFile`
- `uploadFile`
- `createFolder`
- `renameFile`
- `deleteFile`

- [ ] **Step 7: Add the refresh button wiring with explicit confirmation**

Modify `frontend/src/components/admin/RuntimeControls.tsx` to add a `Refresh Dashboard` action that:

- shows `confirm('Refresh the installed dashboard now?')`
- only calls `api.adminDashboardRefresh()` after confirmation
- renders the returned stdout/stderr so the stage logs stay visible in the UI

- [ ] **Step 8: Run the frontend tests and lints**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui/frontend"
npm run test -- --run
npm run lint
```

Expected: green tests and no lint errors

- [ ] **Step 9: Create a checkpoint commit if the user explicitly asked for commits**

```bash
git -C "$HOME/.hermes/extensions/hermes-webui" add frontend/package.json frontend/vitest.config.ts frontend/src/test/setup.ts frontend/src/test/test-utils.tsx frontend/src/api/client.ts frontend/src/api/types.ts frontend/src/components/admin/RuntimeControls.tsx
git -C "$HOME/.hermes/extensions/hermes-webui" commit -m "feat: add frontend test harness and refresh control"
```

## Task 6: Build the `Personality` page UI

**Files:**
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/pages/Personality.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/components/personality/PersonalityEntryList.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/components/editor/TextFileEditor.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/pages/Personality.test.tsx`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/App.tsx`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Write the failing `Personality` page test**

```tsx
it('loads the curated personality file', async () => {
  vi.mocked(api.personalityList).mockResolvedValue({
    items: [{ id: 'soul', label: 'SOUL.md', path: '/tmp/.hermes/SOUL.md', kind: 'markdown', description: 'Primary runtime persona file', exists: true }],
  })
  vi.mocked(api.personalityDetail).mockResolvedValue({
    id: 'soul',
    label: 'SOUL.md',
    path: '/tmp/.hermes/SOUL.md',
    kind: 'markdown',
    description: 'Primary runtime persona file',
    exists: true,
    content: '# Soul\n',
    revision: 'rev-1',
  })

  renderWithAppProviders(<Personality />)

  expect(await screen.findByText('SOUL.md')).toBeInTheDocument()
  expect(await screen.findByDisplayValue('# Soul\n')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui/frontend"
npm run test -- --run src/pages/Personality.test.tsx
```

Expected: missing component or failing query

- [ ] **Step 3: Implement the shared text editor shell**

Create `frontend/src/components/editor/TextFileEditor.tsx`:

```tsx
export function TextFileEditor({
  title,
  path,
  value,
  onChange,
  onSave,
  saveDisabled,
}: {
  title: string
  path: string
  value: string
  onChange: (next: string) => void
  onSave: () => void
  saveDisabled?: boolean
}) {
  return (
    <div className="rounded-xl border p-4 space-y-3" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
      <div>
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>{path}</p>
      </div>
      <textarea className="w-full min-h-[420px] rounded-lg border p-3 font-mono text-sm" value={value} onChange={(e) => onChange(e.target.value)} />
      <button className="rounded-lg px-4 py-2 text-sm font-medium" onClick={onSave} disabled={saveDisabled}>Save</button>
    </div>
  )
}
```

- [ ] **Step 4: Implement the personality list + page**

Create `frontend/src/components/personality/PersonalityEntryList.tsx` and `frontend/src/pages/Personality.tsx` with:

- query for `api.personalityList()`
- auto-load first available entry
- detail query for the selected id
- mutation for `api.updatePersonality()`
- clear success/error notice handling
- `Copy path` button implemented with `navigator.clipboard.writeText(selected.path)`
- `Open in Files` button that links to `/files` with root/path query params only after the Files page exists

Modify `frontend/src/App.tsx` and `frontend/src/components/layout/Sidebar.tsx` to add the `Personality` route and sidebar item once this page exists.

- [ ] **Step 5: Handle stale revisions and missing files in the UI**

Show explicit messages for:

- missing curated file
- save conflict (`409`)
- permission denied
- generic failure

Use a reload action when the save fails with a stale revision.

- [ ] **Step 6: Run the page test, lint, and build**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui/frontend"
npm run test -- --run src/pages/Personality.test.tsx
npm run lint
npm run build
```

Expected: all pass

- [ ] **Step 7: Create a checkpoint commit if the user explicitly asked for commits**

```bash
git -C "$HOME/.hermes/extensions/hermes-webui" add frontend/src/components/editor/TextFileEditor.tsx frontend/src/components/personality/PersonalityEntryList.tsx frontend/src/pages/Personality.tsx frontend/src/pages/Personality.test.tsx frontend/src/App.tsx frontend/src/components/layout/Sidebar.tsx
git -C "$HOME/.hermes/extensions/hermes-webui" commit -m "feat: add personality editor page"
```

## Task 7: Build the `Files` page UI

**Files:**
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/pages/Files.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/components/files/FileBrowser.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/components/files/FileMetadataPanel.tsx`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/components/editor/TextFileEditor.tsx`
- Create: `~/.hermes/extensions/hermes-webui/frontend/src/pages/Files.test.tsx`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/App.tsx`
- Modify: `~/.hermes/extensions/hermes-webui/frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Write the failing `Files` page test**

```tsx
it('loads roots, opens a text file, and saves edits', async () => {
  vi.mocked(api.fileRoots).mockResolvedValue({
    roots: [{ id: 'runtime', label: 'Runtime', path: '/tmp/.hermes', editable: true }],
  })
  vi.mocked(api.fileTree).mockResolvedValue({
    root_id: 'runtime',
    path: '',
    entries: [{ name: 'config.yaml', path: 'config.yaml', node_type: 'file', size: 120 }],
  })
  vi.mocked(api.fileContent).mockResolvedValue({
    root_id: 'runtime',
    path: 'config.yaml',
    absolute_path: '/tmp/.hermes/config.yaml',
    content: 'model:\n  default: nous/hermes-3\n',
    revision: 'rev-1',
    content_type: 'text/yaml',
  })

  renderWithAppProviders(<Files />)

  expect(await screen.findByText('Runtime')).toBeInTheDocument()
  expect(await screen.findByText('config.yaml')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui/frontend"
npm run test -- --run src/pages/Files.test.tsx
```

Expected: missing component or failing query

- [ ] **Step 3: Implement the file browser and metadata panel**

Create `frontend/src/components/files/FileBrowser.tsx`:

```tsx
export function FileBrowser({ entries, onOpen }: { entries: Array<{ name: string; path: string; node_type: string }>; onOpen: (path: string) => void }) {
  return (
    <div className="rounded-xl border p-3 space-y-1" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
      {entries.map((entry) => (
        <button key={entry.path} className="w-full text-left rounded px-2 py-1.5" onClick={() => onOpen(entry.path)}>
          {entry.node_type === 'dir' ? '📁' : '📄'} {entry.name}
        </button>
      ))}
    </div>
  )
}
```

Create `frontend/src/components/files/FileMetadataPanel.tsx`:

```tsx
export function FileMetadataPanel({ absolutePath, rootLabel }: { absolutePath: string; rootLabel: string }) {
  return (
    <div className="rounded-xl border p-4 space-y-2" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
      <div className="text-xs uppercase tracking-wide" style={{ color: 'var(--color-text-muted)' }}>File details</div>
      <div className="text-sm font-medium">{rootLabel}</div>
      <p className="text-xs font-mono break-all" style={{ color: 'var(--color-text-muted)' }}>{absolutePath}</p>
    </div>
  )
}
```

- [ ] **Step 4: Implement the files page workflow**

Create `frontend/src/pages/Files.tsx` with:

- root query from `api.fileRoots()`
- tree query from `api.fileTree(rootId, path)`
- text file query from `api.fileContent(rootId, filePath)`
- download link/button wired to `GET /api/files/download`
- save mutation via `api.updateFileContent()`
- upload wired to the upload endpoint
- new folder wired to the folder-create endpoint
- rename wired to the rename endpoint
- delete wired to the delete endpoint with confirmation before execution

Use `TextFileEditor` for inline text editing and `FileMetadataPanel` for exact path display.

Modify `frontend/src/App.tsx` and `frontend/src/components/layout/Sidebar.tsx` to add the `Files` route and sidebar item once this page exists.

- [ ] **Step 5: Add explicit error handling for managed files and non-text content**

Show user-friendly messages for:

- `managed in Personality`
- `unsupported binary edit`
- `file too large for inline editing`
- upload rejected for files over 50 MB
- failed delete / rename / upload

Use `content_type` from the API to decide preview behavior:

- `image/*` -> inline image preview + download
- other non-text -> metadata + download link

- [ ] **Step 6: Run the page tests, lint, and build**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui/frontend"
npm run test -- --run src/pages/Files.test.tsx
npm run lint
npm run build
```

Expected: all pass

- [ ] **Step 7: Create a checkpoint commit if the user explicitly asked for commits**

```bash
git -C "$HOME/.hermes/extensions/hermes-webui" add frontend/src/pages/Files.tsx frontend/src/components/files/FileBrowser.tsx frontend/src/components/files/FileMetadataPanel.tsx frontend/src/components/editor/TextFileEditor.tsx frontend/src/pages/Files.test.tsx frontend/src/App.tsx frontend/src/components/layout/Sidebar.tsx
git -C "$HOME/.hermes/extensions/hermes-webui" commit -m "feat: add allowlisted files page"
```

## Task 8: Seed runtime config, package the repo changes, regenerate the patch, and verify the VM flow

**Files:**
- Create: `~/Fr33dom_bot/config/fr33d0m-dashboard.yaml`
- Modify: `~/Fr33dom_bot/.gitignore`
- Modify: `~/Fr33dom_bot/install.sh`
- Modify: `~/Fr33dom_bot/README.md`
- Modify: `~/Fr33dom_bot/USER_MANUAL.md`
- Modify: `~/Fr33dom_bot/patches/hermes-webui.patch`

- [ ] **Step 1: Ignore brainstorm artifacts in the repo**

Modify `~/Fr33dom_bot/.gitignore`:

```gitignore
.superpowers/
```

- [ ] **Step 2: Add the seed runtime dashboard config**

Create `~/Fr33dom_bot/config/fr33d0m-dashboard.yaml`:

```yaml
personality_files:
  - id: soul
    label: SOUL.md
    path: ~/.hermes/SOUL.md
    kind: markdown
    description: Primary runtime persona file

file_roots:
  - id: runtime
    label: Runtime
    path: ~/.hermes
    editable: true
  - id: downloads
    label: Downloads
    path: ~/Downloads
    editable: true
```

- [ ] **Step 3: Copy the runtime dashboard config during install**

Update `~/Fr33dom_bot/install.sh` near the existing config copy block:

```bash
cp "$SCRIPT_DIR/config/fr33d0m-dashboard.yaml" "$HERMES_HOME/fr33d0m-dashboard.yaml"
ok "Runtime dashboard config installed"
```

- [ ] **Step 4: Regenerate the patch from the installed customized clone**

Run:

```bash
git -C "$HOME/.hermes/extensions/hermes-webui" diff --binary > "$HOME/Fr33dom_bot/patches/hermes-webui.patch"
```

Expected: `~/Fr33dom_bot/patches/hermes-webui.patch` now includes the new runtime-editor and refresh-action changes on top of the existing Fr33d0m customizations

- [ ] **Step 5: Update the repo docs**

Add the new routes and local-only behavior to:

- `~/Fr33dom_bot/README.md`
- `~/Fr33dom_bot/USER_MANUAL.md`

Explicitly document:

- `Personality` edits runtime files only
- `Files` is allowlist-based
- no dashboard git push/commit flow exists
- `fr33d0m-refresh-dashboard` is a local maintenance command

- [ ] **Step 6: Run the final verification commands**

Run:

```bash
cd "$HOME/.hermes/extensions/hermes-webui"
python -m pytest -q

cd "$HOME/.hermes/extensions/hermes-webui/frontend"
npm run test -- --run
npm run lint
npm run build

bash -n "$HOME/Fr33dom_bot/install.sh"
bash -n "$HOME/Fr33dom_bot/bin/fr33d0m-refresh-dashboard"
```

Expected:

- all backend tests pass
- all frontend tests pass
- lint passes
- frontend build succeeds
- shell syntax checks produce no output

- [ ] **Step 7: Verify the local refresh flow on the VM**

Run:

```bash
~/.local/bin/fr33d0m-refresh-dashboard
systemctl --user status fr33d0m-webui --no-pager
```

Expected:

- refresh logs show reset/apply/build/restart
- `fr33d0m-webui` is active after restart
- the new `/personality` and `/files` routes load in the browser

- [ ] **Step 8: Create a checkpoint commit if the user explicitly asked for commits**

```bash
git -C "$HOME/Fr33dom_bot" add .gitignore config/fr33d0m-dashboard.yaml install.sh README.md USER_MANUAL.md patches/hermes-webui.patch docs/superpowers/specs/2026-03-29-fr33dom-dashboard-runtime-editors-design.md docs/superpowers/plans/2026-03-29-fr33dom-dashboard-runtime-editors.md
git -C "$HOME/Fr33dom_bot" commit -m "feat: add local runtime editors to fr33dom dashboard"
```
