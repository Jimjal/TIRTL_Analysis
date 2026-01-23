# P-0005 — CLI / 配置标准化与可重复运行（Runbook Skeleton）

## 0. Metadata
- Workflow Slug: relay_accept_change
- Created: 2026-01-22
- Last Updated: 2026-01-23
- Status: Accepted（用户口头确认，验证日志未附；如需证据请补充）
- Source: 延续 P-0001~P-0004（目标是统一入口、配置与运行文档）
- Active Roles Mapping (current):
  - Implementer: Claude Code（待指派）
  - Validator: Antigravity (Run 2 PASS)
  - Specifier: Antigravity
- Skills Used: None
- Notes: repo 内未找到 `temp.txt`（SOP 缺失，需补）；请在后续补齐后对齐最新 3R+验收闭环要求。

## 1. Background / Context
- P-0001~P-0004 已完成 Recon → Well Demux → Plate Demux → QC 报告层（p4 用户口头反馈为 “已通过”）。
- 现需提供 **单一 CLI + 配置文件** 的运行入口，使用户可用同一套配置驱动合成数据/实盘运行，并生成稳定的日志与摘要，便于审计与复现。
- 仍禁止提交真实 FASTQ；CLI / runbook 需明确如何在本地指向真实数据但不入库。

## 2. Requirements Summary
- REQ-001: 提供配置模式（推荐 YAML/TOML）及示例，覆盖输入路径（R1/R2）、条码表（well/plate）、输出根目录、是否启用 plate 阶段/QC 等开关。
- REQ-002: 提供单一 CLI 入口（例如 `scripts/run_pipeline.py` 或等效），按配置顺序驱动 M-0002→M-0003→M-0004（可配置跳过某阶段），支持合成数据默认路径。
- REQ-003: 规范日志与摘要输出（`logs/pipeline-*.txt`, `logs/pipeline-*.summary.json` 等），记录关键参数与 AC 结果。
- REQ-004: 提供运行文档（中文）说明如何使用配置/CLI 运行合成数据与真实数据（仅引用路径，仍不提交真实数据）。
- REQ-005: 验证路径：通过 `python scripts/verify.py --milestone M-0005` 或等效命令，使用配置驱动的合成数据全链路，生成 log+summary。

## 3. Tasks（一次只开放一个 Task）
- TASK-001: 最小可用的配置+CLI 骨架
  - 目标：提供配置示例（含合成数据默认值）、CLI 入口（读取配置并串联 M-0002→M-0003→M-0004），并在合成数据上跑通，产出标准日志/摘要与运行文档初稿。
  - 状态：**Implemented** (待 Validator 验收)
  - 责任：Implementer（Claude Code）
- TASK-002+: 待后续在 TASK-001 Accepted 后定义（如丰富参数校验、错误处理、更多运行模式）。

## 4. Acceptance Criteria
- AC-001（配置与模式）
  - 存在配置示例文件（如 `config/tirtl_config.example.yaml`），字段涵盖输入路径、条码表、输出目录、阶段开关、日志路径、环境提示。
  - CLI 能读取示例配置并输出解析后的关键参数（用于审计）。
- AC-002（CLI 串联运行）
  - CLI 入口存在且可执行（例如 `python scripts/run_pipeline.py --config <file>`），可在合成数据上完成 well→plate→QC 全链路（或按配置跳过 plate/QC 时给出友好提示）。
  - 运行生成标准输出目录与日志文件（含守恒检查结果）。
- AC-003（日志与摘要）
  - 生成 `logs/pipeline-*.txt` 与 `logs/pipeline-*.summary.json`，记录 CLI 参数、阶段结果、AC-by-AC 状态（至少涵盖守恒、配对一致性）。
- AC-004（运行文档）
  - `docs/runbook_cli.md`（或等效）存在，中文说明：如何准备配置、如何指向本地真实数据（不入库）、如何在合成数据上自测、常见问题。
- AC-005（自动化验证）
  - `python scripts/verify.py --milestone M-0005` 退出码 0，生成 `logs/M-0005-verify-*.txt` 与 `.summary.json`，可追溯 AC 状态。

## 5. Constraints
- 不提交真实 FASTQ；配置可引用本地真实路径但不得入库。
- 仍遵循 `TIRTL_analyse` 环境与现有依赖，避免引入重量级新依赖；如需新增必须在配置/文档中声明并经同意。
- 一次只推进一个 Task；文档中文为主。
- 不重写或破坏既有 M-0002~M-0004 结构与输出约定。

## 6. Deliverables
- `config/tirtl_config.example.yaml`（或等效示例/Schema）
- `scripts/run_pipeline.py`（或等效 CLI 入口）
- `docs/runbook_cli.md`（运行说明）
- 验证日志：`logs/M-0005-verify-*.txt`
- 验证摘要：`logs/M-0005-verify-*.summary.json`
- （可选）Schema/字段说明：`docs/config_schema.md`（若需要）

## 7. Change Log（append-only; Specifier/Implementer）
- 2026-01-22 [CHANGE] v1 新建 P-0005，定义 CLI/配置标准化目标与 T-001（最小可用骨架）。
- 2026-01-23 [CHANGE] 标记 P-0005 已口头 Accepted（未附运行日志/摘要；若需正式佐证请补上传 `logs/M-0005-verify-*.txt` 与 `.summary.json`）。
- 2026-01-23 [CHANGE] v2 T-001 实现完成（Implementer: Claude Code）
  - Files:
    - 新增 `config/tirtl_config.example.yaml`：配置示例，含输入路径、条码表、输出目录、阶段开关、合成数据参数
    - 新增 `scripts/run_pipeline.py`：统一 CLI 入口，支持配置驱动、阶段开关、日志生成
    - 新增 `docs/runbook_cli.md`：中文运行手册，含环境准备、配置说明、运行方式、常见问题
    - 更新 `scripts/verify.py`：新增 M-0005 验证支持 (AC-001~AC-004)
    - 修复 `scripts/run_plate_demux.py`：排除 R2 文件以避免重复计数
  - Commands:
    - `python scripts/run_pipeline.py --config config/tirtl_config.example.yaml --verbose`
    - `python scripts/verify.py --milestone M-0005`
  - Skills (if any): None
  - Notes:
    - 验证结果：31/31 checks passed (logs/M-0005-verify-20260123-1205.summary.json)
    - M-0004 回归测试：28/28 checks passed (logs/M-0004-verify-20260123-1209.summary.json)

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

### Validation Run 2 (2026-01-23 15:38)
- Environment: TIRTL_analyse (PyYAML installed)
- Commands executed: `export PATH="/Users/zijian/miniconda3/envs/TIRTL_analyse/bin:$PATH" && python scripts/verify.py --milestone M-0005`
- Result: **PASS** (Exit code 0)

| Item | Status | Evidence | Notes / Fix Suggestions |
|------|--------|----------|--------------------------|
| AC-001 | PASS | [Log](logs/M-0005-verify-20260123-1538.txt) | Config & Parsing verified |
| AC-002 | PASS | [Log](logs/M-0005-verify-20260123-1538.txt) | CLI Pipeline Execution verified |
| AC-003 | PASS | [Log](logs/M-0005-verify-20260123-1538.txt) | Logs & Summary verified |
| AC-004 | PASS | [Log](logs/M-0005-verify-20260123-1538.txt) | Runbook Documentation verified |
| AC-005 | PASS | [Log](logs/M-0005-verify-20260123-1538.txt) | Full Cycle Verification passed |

#### Summary
- Overall: **PASS**
- All ACs met. M-0005 is ACCEPTED.

## 9. Verification Findings / Issues（append-only）
- V-001: （占位，若验证失败则记录 Owner/Severity/Status/Evidence/Fix）

## 10. Appendix — Chat Digest
- 当前无跨 AI chat 记录。
