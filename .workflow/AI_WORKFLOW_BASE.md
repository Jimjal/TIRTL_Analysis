# AI_WORKFLOW_BASE.md ? Workflow base rules

> Read order: `.workflow/AI_LOADER.md` ? this file ? active workflow `BASE.md` ? role files.

---

## Kit Source (self-bootstrap)
- WORKFLOW_KIT_REPO = https://github.com/JimalH/ai-workflow-kit.git
- WORKFLOW_KIT_REF  = main (pin to a tag, e.g., v0.2.0)
- WORKFLOW_KIT_SUBDIR = .

## 0) Core terms
- Workflow: a collaboration flow (e.g., relay_accept_change).
- SSOT: single source of truth.
- BASE: per-workflow rules/specs (process, acceptance, records, skills, permissions).
- Roles: reusable role guides.
- Chat Protocol: cross-AI chat transport rules.
- Skills: optional capabilities (allowlisted, cached).

## 1) Fixed structure (must exist)
- `.workflow/workflows/`
- `.workflow/roles/`

Key files:
- `.workflow/workflows/ACTIVE_WORKFLOW.txt`  ? current `workflow_slug`
- `.workflow/workflows/CHAT_PROTOCOL.md`     ? transport protocol
- `.workflow/workflows/<workflow_slug>/BASE.md`
- `.workflow/roles/<Role>.md`
- `.workflow/workflows/<workflow_slug>/promptbook/` (if that workflow uses promptbook as SSOT)
- `.workflow/workflows/_skills_cache/` (skills cache)
- None mode: `.workflow/workflows/none/BASE.md` (minimal safety only; no SSOT/promptbook)

## 2) Your identity (Role / Identity) ? driven by workflow BASE
- **ROLE**: must be in current workflow `BASE.md` Roles Registry (combine only if allowed).
- **IDENTITY**: short label (AI instance/platform), e.g., `AI1/AI2/Claude/Codex/AG`.

### 2.1 Role confirmation rules (mandatory)
- If user assigned a role: use it, but verify it is Allowed and combo is permitted.
- If not assigned/unsure: ask once: ?Please pick a ROLE from Allowed Roles (combos must match Allowed Combos); what Identity tag should I use??

## 3) Every turn: Bootstrap Sequence (strict order)
> Do this before any implementation/validation/SSOT/chat output.

### Step 1 ? Read workflow config
1) Read `.workflow/workflows/ACTIVE_WORKFLOW.txt` to get `<workflow_slug>`
2) If `<workflow_slug> == none`:
   - Read `.workflow/workflows/none/BASE.md`
   - Skip promptbook/SSOT/append-only rules (none has no SSOT)
   - Roles are optional; load `.workflow/roles/<ROLE>.md` only if user assigns
   - You may skip `.workflow/workflows/CHAT_PROTOCOL.md` (none usually has no cross-AI chat)
   End Step 1.
   Else:
   - Read `.workflow/workflows/CHAT_PROTOCOL.md`
   - Read `.workflow/workflows/<workflow_slug>/BASE.md` (Roles Registry / SSOT / Skills / **Permissions Policy**)
   - Read `.workflow/roles/<ROLE>.md` (multiple if combined)

### Step 2 ? Permissions Bootstrap (mandatory)
- Even if the platform grants full rights, you **must** follow the current workflow?s `Autonomy & Permissions Policy`.
- If unsure whether an action is allowed: **ask the user** (BASE rules first).

### Step 3 ? Skills Bootstrap (if roles require)
- Read `Required Skills` in `.workflow/roles/<ROLE>.md`.
- Obey workflow Skills Policy:
  - Allowlist only
  - Cache to `.workflow/workflows/_skills_cache/` and pin to commit/tag
  - Default: load instructions only; no auto execution of scripts/binaries unless BASE/user allows
  - Record installs/usage in SSOT Change Log if BASE requires

### Step 4 ? Handle cross-AI chat (highest priority each turn)
In `.workflow/workflows/<workflow_slug>/` find `temp_chat_*.txt`:
- If multiple OPEN: pick newest mtime
- Lock via `_editing` per CHAT_PROTOCOL
- Update `Last read`
- Mark needed messages `FLAG:UNREAD ? READ`
- Reply if needed (TYPE per BASE; tags recommended)

---

## 4) SSOT write discipline (mandatory unless none mode)
- SSOT as defined by BASE (often promptbook)
- Canonical: first occurrence of a heading wins; no duplicate full templates
- Append-only: only sections BASE allows (often Change Log, Validation Report)
- Evidence required for PASS (per BASE)

## 5) Blocking
If blocked (missing files/perm/env/data):
- Record BLOCKED (SSOT or validation report)
- Provide unblocking steps
- Do not fabricate paths/versions/outputs

## 6) Minimum safety
- Do not delete user data/history
- Do not overwrite append-only records (append only)
- Do not edit prior chat bodies (only headers/flags)
- Stay within BASE-defined process; ask if unsure
