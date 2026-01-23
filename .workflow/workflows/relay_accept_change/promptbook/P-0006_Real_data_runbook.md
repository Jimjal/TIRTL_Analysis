# P-0006 — 真实数据运行手册与发布准备（Runbook & Governance）

## 0. Metadata
- Workflow Slug: relay_accept_change
- Created: 2026-01-23
- Last Updated: 2026-01-23
- Status: Draft
- Source: 延续 P-0005（CLI/配置已完成，需落地真实数据操作规范）
- Active Roles Mapping (current):
  - Implementer: Claude Code（待指派）
  - Validator: Antigravity (Run 1 PASS)
  - Specifier: Antigravity
- Skills Used: None
- Notes: repo 仍缺 `temp.txt`（SOP）；请补齐后对齐最新 3R+验收闭环要求。

## 1. Background / Context
- P-0001~P-0005 已完成：Recon → Well Demux → Plate Demux → QC → CLI/配置骨架（用户口头确认 P-0005 通过）。
- 下一步需提供 **真实数据运行手册（Runbook）与发布前治理要求**：说明如何在不提交真实 FASTQ 的前提下，使用 P-0005 的 CLI/配置在本地/安全环境运行全链路，并输出合规的日志、审计记录与交付包。
- 语言：中文为主；强调数据治理与合规约束。

## 2. Requirements Summary
- REQ-001: 运行手册（docs/runbook_real_data.md）— 中文，涵盖前置条件、数据路径准备、配置示例、执行步骤、常见故障、资源/时间预估。
- REQ-002: 数据治理与合规章节：禁止提交真实数据、如何使用本地/挂载路径、如何检查 `.gitignore` / 清理缓存、敏感信息处理。
- REQ-003: 审计与交付物定义：运行后需保留哪些日志/摘要/统计（沿用 P-0005/P-0004 约定），如何打包交付给审核方。
- REQ-004: 自检流程：使用合成数据的 “dry-run” 示例命令；若需真实数据验证，给出离线运行指引与“结果留痕”模板（不提交数据）。
- REQ-005: 验证路径：`python scripts/verify.py --milestone M-0006`（或等效）输出 `logs/M-0006-verify-*.txt` 与 `.summary.json`，验证运行手册的可操作性（可在合成数据模式下）。

## 3. Tasks（一次只开放一个 Task）
- TASK-001: 真实数据运行手册 v1（文档与治理清单）
  - 目标：撰写 `docs/runbook_real_data.md`，覆盖 REQ-001~004 的最小可用版本；提供示例配置引用（不含真实数据）、运行步骤、数据治理/安全清单、自检命令。
  - 状态：**Implemented** (待 Validator 验收)
  - 责任：Implementer（Claude Code）
- TASK-002+: 待 TASK-001 通过后定义（如发布包模板、审核表单、自动化合规检查）。

## 4. Acceptance Criteria
- AC-001（运行手册完备性）
  - `docs/runbook_real_data.md` 存在；包含前置条件、数据布局、配置示例引用（使用 P-0005 示例）、执行步骤、资源/时间提示、常见故障排查。
- AC-002（数据治理与合规）
  - 文档明确：禁止提交真实数据、如何放置/引用真实数据、`.gitignore` 提示、日志脱敏建议、缓存清理步骤。
- AC-003（审计与交付物）
  - 定义运行后必须保留的日志与摘要（如 `logs/pipeline-*.txt/.summary.json`、QC 输出），以及交付打包建议（不含原始 FASTQ）。
- AC-004（自检与验证）
  - 提供基于合成数据的 “dry-run” 命令示例；若需真实数据验证，说明离线执行与结果留痕方式。
  - `python scripts/verify.py --milestone M-0006` 退出码 0，生成 `logs/M-0006-verify-*.txt` 和 `.summary.json`，记录 AC-by-AC 状态（可使用合成数据模式）。
- AC-005（语言与范围）
  - 文档中文为主，未引入未经批准的新依赖或真实数据。

## 5. Constraints
- 不提交或上传任何真实 FASTQ；仅文档与示例配置引用路径。
- 遵循现有环境与依赖；如需新增依赖必须在文档中声明并经批准。
- 一次只推进一个 Task；遵守 RAC/3R 规则。

## 6. Deliverables
- `docs/runbook_real_data.md`
- （可选）`docs/runbook_checklist.md` 或附录中的运行检查清单
- 验证日志：`logs/M-0006-verify-*.txt`
- 验证摘要：`logs/M-0006-verify-*.summary.json`

## 7. Change Log（append-only; Specifier/Implementer）
- 2026-01-23 [CHANGE] v1 新建 P-0006，定义真实数据运行手册与治理要求，开放 TASK-001。
- 2026-01-23 [CHANGE] v2 T-001 实现完成（Implementer: Claude Code）
  - Files:
    - 新增 `docs/runbook_real_data.md`：真实数据运行手册（中文），覆盖：
      - 前置条件与环境要求
      - 数据布局与路径准备（禁止仓库内存放真实数据）
      - 配置文件准备与 .gitignore 检查
      - 执行步骤与资源/时间预估
      - 数据治理与合规（脱敏、缓存清理、Git 提交前检查）
      - 审计与交付物定义（日志、QC 输出、打包建议）
      - 自检与验证流程
      - 常见故障排查
    - 更新 `scripts/verify.py`：新增 M-0006 验证支持 (AC-001~AC-005)
  - Commands:
    - `python scripts/verify.py --milestone M-0006`
  - Skills (if any): None
  - Notes:
    - 验证结果：23/23 checks passed (logs/M-0006-verify-20260123-1545.summary.json)

## 8. Validation Report / 验收总结（append-only; Validator）
### Validation Run 1
- Environment: （待验证）
- Commands executed: -
- Skills (if any): -

| Item | Status | Evidence | Notes / Fix Suggestions |
|------|--------|----------|--------------------------|
| AC-001 | BLOCKED |  | 待实现/验证 |
| AC-002 | BLOCKED |  | 待实现/验证 |
| AC-003 | BLOCKED |  | 待实现/验证 |
| AC-004 | BLOCKED |  | 待实现/验证 |
| AC-005 | BLOCKED |  | 待实现/验证 |

### Validation Run 1 (2026-01-23 15:47)
- Environment: TIRTL_analyse (PyYAML verified)
- Commands executed: `export PATH="/Users/zijian/miniconda3/envs/TIRTL_analyse/bin:$PATH" && python scripts/verify.py --milestone M-0006`
- Result: **PASS** (Exit code 0)

| Item | Status | Evidence | Notes / Fix Suggestions |
|------|--------|----------|--------------------------|
| AC-001 | PASS | [Log](logs/M-0006-verify-20260123-1547.txt) | Runbook Completeness verified |
| AC-002 | PASS | [Log](logs/M-0006-verify-20260123-1547.txt) | Data Governance & Compliance verified |
| AC-003 | PASS | [Log](logs/M-0006-verify-20260123-1547.txt) | Audit & Deliverables verified |
| AC-004 | PASS | [Log](logs/M-0006-verify-20260123-1547.txt) | Self-Check & Validation verified |
| AC-005 | PASS | [Log](logs/M-0006-verify-20260123-1547.txt) | Language & Scope verified |

#### Summary
- Overall: **PASS**
- All ACs met. M-0006 is ACCEPTED.

## 9. Verification Findings / Issues（append-only）
- V-001: （占位；若验证失败则记录 Owner/Severity/Status/Evidence/Fix）

## 10. Appendix — Chat Digest
- 当前无跨 AI chat 记录。
