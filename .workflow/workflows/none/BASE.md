# BASE — none (minimal safety only)

## 1. Purpose
- This mode disables SSOT/promptbook discipline and workflow-specific steps.
- Use when you need a clean slate with only minimal safety guardrails.

## 2. Roles Registry (optional)
- Allowed Roles: [Generalist] (optional; skip role reading unless user explicitly assigns)
- Allowed Combos: [Generalist]  
- Disallowed Combos: []  

## 3. Autonomy & Permissions Policy
- Do not delete or overwrite user data/history unless explicitly asked.
- Ask before any destructive or irreversible actions (including rm/reset/force pushes).
- No network or external writes beyond the current workspace unless user requests.
- Keep diffs minimal and auditable.

## 4. Execution Notes
- Required reads: `.workflow/AI_WORKFLOW_BASE.md` and this file.
- Skip promptbook/SSOT/append-only rules; there is no workflow promptbook in none mode.
- Roles are optional; only load `.workflow/roles/<ROLE>.md` if the user assigns one.
