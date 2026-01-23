# AI_LOADER.md - Universal bootstrap (cross-platform)

> Purpose: ensure any AI/Agent runs the same bootstrap, permissions check, stub repair, and workflow selection (incl. none mode) before work.

---

## 0) Key terms
- Workflow: a collaboration flow (e.g., relay_accept_change).
- SSOT: single source of truth (requirements/tasks/acceptance/changes must be recorded).
- BASE: workflow rules & docs (process, acceptance, records, Skills/Permissions policy, etc.).
- Roles: reusable role handbooks.
- Chat Protocol: cross-AI file chat transport layer.
- Skills: optional capability extensions, allowlisted and cached.

---

## 1) Kit Source
- WORKFLOW_KIT_REPO = https://github.com/JimalH/ai-workflow-kit.git
- WORKFLOW_KIT_REF  = main   (pin to a tag, e.g., v0.2.0)
- WORKFLOW_KIT_SUBDIR = .
- INSTALL_STRATEGY = copy    (default; submodule optional)
- MARKER_BLOCK_ID = AI_WORKFLOW_LOADER_BLOCK

---

## 2) Installed check
Present if all exist:
- .workflow/workflows/CHAT_PROTOCOL.md
- .workflow/workflows/ACTIVE_WORKFLOW.txt
- .workflow/roles/
- .workflow/AI_WORKFLOW_BASE.md

Else run section 3 to install/repair.

---

## 3) Install / Repair

### 3.1 Fetch kit
Prefer git (repeatable):
`git clone --depth 1 --branch <WORKFLOW_KIT_REF> <WORKFLOW_KIT_REPO> <tmp_dir>`
If git unavailable, download zip to `<tmp_dir>`.

### 3.2 Copy into workspace (INSTALL_STRATEGY=copy)
Copy the entire `.workflow/` from `<tmp_dir>/<WORKFLOW_KIT_SUBDIR>/` to repo root.
Do not overwrite user content; ask on conflicts. Ensure `.workflow/workflows/_skills_cache/` exists (create if missing).

### 3.3 Choose workflow (must ask user)
List directories under `.workflow/workflows/` that contain `BASE.md` (skip `docs/`, `_skills_cache/`). The list **must include `none` (minimal safety only)**. Ask:
"Which workflow_slug to activate- (none = minimal safety, no SSOT/promptbook)"
Write choice to `.workflow/workflows/ACTIVE_WORKFLOW.txt` (one line).

### 3.4 Install/repair platform entry stubs (marker block)
Goal: ensure next session on any platform reads this loader first.
Stubs:
- Codex: AGENTS.md
- Claude Code: .claude/CLAUDE.md
- Antigravity/Gemini: .agent/rules/GEMINI.md

Steps:
1) Build a list of stubs that are missing or lack the marker block.
2) Ask the user which stubs to install from that list (default: all).
3) For chosen stubs: create file if missing, or replace/insert only the marker block, keeping other content.
   Marker (do not change):
   ```md
   <!-- BEGIN AI_WORKFLOW_LOADER_BLOCK -->
   You MUST read and follow ./.workflow/AI_LOADER.md before doing any work.
   <!-- END AI_WORKFLOW_LOADER_BLOCK -->
   ```

---

## 4) Enter workflow execution
Order:
1) Read `.workflow/AI_WORKFLOW_BASE.md`
2) If `<workflow_slug> == none`:
   - Read `.workflow/workflows/none/BASE.md`
   - Skip promptbook/SSOT/append-only rules (none has no SSOT)
   - Roles optional (read `.workflow/roles/<ROLE>.md` only if user assigns)
   - May skip `.workflow/workflows/CHAT_PROTOCOL.md`
   End step 2.
   Else:
   - Read `.workflow/workflows/CHAT_PROTOCOL.md`
   - Read `.workflow/workflows/<workflow_slug>/BASE.md` (roles registry, SSOT, skills, **permissions policy**)
   - Read `.workflow/roles/<ROLE>.md` (multiple if combined)
3) Handle `.workflow/workflows/<workflow_slug>/temp_chat_*.txt` (if any; none mode usually none)
4) Then implement/validate/write SSOT (SSOT may be skipped in none mode)

---

## 5) Required output
If section 3 ran, report:
- Files written/updated (with paths)
- Any conflicts needing user choice
- Workflow list shown + user selection (written to ACTIVE_WORKFLOW)
