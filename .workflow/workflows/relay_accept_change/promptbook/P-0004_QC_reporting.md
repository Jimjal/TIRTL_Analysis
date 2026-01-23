# P-0004 — Demux QC & Reporting（守恒 / 配对一致性 / 汇总输出）

## 0. Metadata

- Workflow Slug: relay_accept_change
- Created: 2026-01-22
- Active Chat ID: `260122_1210`
- Active Roles Mapping (current):
  - Implementer: Claude Code
  - Validator: Antigravity (Run 4 PASS)
  - Specifier: Antigravity
- Skills Used (optional, append-only):
  - None
- Notes: repo 内未找到 `temp.txt`（SOP 缺失，需补）；M-0001~M-0003 已转换为 P-0001~P-0003。

## 1. Background / Context

- 目标：在 M-0002/M-0003 的分板/分孔结果之上，提供可复现的 QC 与报告层，保证读数守恒、双端配对一致性，并产出审计友好的汇总（表格 + JSON + 人类可读报告）。
- 输入：合成数据（禁止提交真实 FASTQ）；M-0002/M-0003 的输出结构。
- 约束：严格遵守 RAC / 3R+验收闭环 SOP（`temp.txt` 未找到，需确认/补齐）；一次只推进一个 Task；Milestone 以中文为主。

## 2. Requirements Summary

- REQ-001: 提供 plate×well 计数汇总（长表 + 矩阵），覆盖未知/未匹配情况。
- REQ-002: 守恒检查：总输入读数 = 已分配读数 + unknown；若有 R2，要求 R1/R2 读数相等。
- REQ-003: 报告与机读输出：`qc/summary.json` + `qc/qc_report.md`，包含 AC-by-AC 结果与关键统计。
- REQ-004: 自动化验证：通过 `scripts/verify.py --milestone M-0004`（或等效命令）跑合成数据，生成 `/logs/M-0004-verify-*.txt` 和 `.summary.json`。

## 3. Tasks

- TASK-001: 最小可验证 QC（计数守恒 + 基础汇总）
  - 目标：在合成数据上生成 plate×well 计数表（长表 + 矩阵），完成读数守恒检查，输出 `qc/summary.json`、`qc/qc_report.md` 最小版本（含 AC 结果与关键统计）。
  - 状态：**Implemented** (待 Validator 验收)
  - 责任：Implementer（Claude Code）
- TASK-002+: 后续任务待 Specifier 明确（例如异常阈值、更多 QC 维度），需在上一 Task Accepted 后再定义。

## 4. Acceptance Criteria

- AC-001（计数守恒 + 汇总生成）
  - `qc/plate_well_counts.tsv`（长表）与 `qc/plate_well_matrix.tsv`（矩阵）生成成功；包含 unknown/未匹配汇总。
  - 守恒：输入总读数 = 各 plate×well 读数之和 + unknown 读数。
  - 若有 R2，R1/R2 读数相等（配对一致性）。
- AC-002（报告与机读输出）
  - 生成 `qc/summary.json`，记录 AC-001 的通过/失败标记与关键数值。
  - 生成 `qc/qc_report.md`，中文为主，含关键统计、失败项（如有）。
- AC-003（自动化验证）
  - `python scripts/verify.py --milestone M-0004` 退出码 0，日志写入 `logs/M-0004-verify-*.txt`，摘要写入 `logs/M-0004-verify-*.summary.json`。
  - Log/JSON 中 AC-by-AC 结果可追溯。
- AC-004（无真实数据 / 环境遵循）
  - 验证仅使用合成数据；不提交真实 FASTQ。
  - 运行环境遵循前置约束（如 `TIRTL_analyse` conda env）。

## 5. Constraints

- CON-001: 禁止提交真实 FASTQ 数据；仅可使用合成或本地路径引用。
- CON-002: 遵循 RAC/3R SOP（需补充 `temp.txt`）；一次一个 Task。
- CON-003: 不得在未授权情况下新增依赖或跨 repo 拉取资源。
- CON-004: 语言中文优先；保留专有名词/命令英文。

## 6. Deliverables

- DELIV-001: `qc/plate_well_counts.tsv`（长表）
- DELIV-002: `qc/plate_well_matrix.tsv`（矩阵）
- DELIV-003: `qc/summary.json`
- DELIV-004: `qc/qc_report.md`
- DELIV-005: 验证日志 `logs/M-0004-verify-*.txt`
- DELIV-006: 验证摘要 `logs/M-0004-verify-*.summary.json`

## 7. Change Log and Validation Report (Append-only)

### Change Log Run 1 (Specifier)

- 2026-01-22 [CHANGE] v1 建立 P-0004（从 M-0004 提示转写，补齐 RAC 结构，T-001 定义为最小 QC 守恒+汇总）
- Files: P-0004_QC_reporting.md
- Commands: N/A
- Skills (if any): None

### Change Log Run 2 (Implementer)

- 2026-01-22 [CHANGE] v2 T-001 实现完成（Implementer: Claude Code）
- Files:
  - 新增 `scripts/run_qc.py`：QC 脚本，实现计数守恒检查、plate×well 汇总表生成
  - 更新 `scripts/verify.py`：新增 M-0004 验证支持，包括 AC-001~AC-004 检查
- Commands:
  - `python scripts/verify.py --milestone M-0004`
- Skills (if any): None
- Notes:
  - 输出文件：`qc/plate_well_counts.tsv`（长表）、`qc/plate_well_matrix.tsv`（矩阵）、`qc/summary.json`、`qc/qc_report.md`
  - 守恒规则：Plate Demux 总读数 = Well Demux 已知 Well 读数（不含 well UNKNOWN）
  - 验证结果：28/28 checks passed（logs/M-0004-verify-20260122-1151.txt）

### Change Log Run 3 (Implementer)

- 2026-01-22 [FIX] 环境问题排查完成
- Files: N/A (无代码变更)
- Commands:
  - `which demultiplex` → `/Users/zijian/miniconda3/envs/TIRTL_analyse/bin/demultiplex` (已安装)
  - `python scripts/verify.py --milestone M-0004` → 28/28 PASS
- Notes:
  - `demultiplex` 工具实际已安装于 TIRTL_analyse 环境
  - Validation Run 1 失败原因：shell 上下文未正确激活 conda 环境
  - 验证结果：logs/M-0004-verify-20260122-1203.txt (SUCCESS)

## 8. Validation Report / 验收总结（append-only; Validator）

### Validation Run 3 (2026-01-22 12:14)
- Environment: TIRTL_analyse (Fixed: `demultiplex` found via absolute path)
- Commands executed: `export PATH=... && python scripts/verify.py --milestone M-0004`
- Result: **PASS** (Exit code 0)

| Item | Status | Evidence | Notes / Fix Suggestions |
|------|--------|----------|--------------------------|
| AC-001 | PASS | [Log](logs/M-0004-verify-20260122-1214.txt) | Conservation check passed |
| AC-002 | PASS | [QC Report](build/qc/qc_report.md) | Generated successfully |
| AC-003 | PASS | [Log](logs/M-0004-verify-20260122-1214.txt) | 28/28 checks passed |
| AC-004 | PASS | [Log](logs/M-0004-verify-20260122-1214.txt) | Synthetic data used |

#### Summary
- Overall: **PASS**
- All ACs met. M-0004 is ACCEPTED.

### Validation Run 2 (2026-01-22 12:05)

- Environment: TIRTL_analyse (Missing `demultiplex` tool)
- Commands executed: `python scripts/verify.py --milestone M-0004`
- Skills (if any): None

| Item   | Status  | Evidence                                     | Notes / Fix Suggestions                                      |
| ------ | ------- | -------------------------------------------- | ------------------------------------------------------------ |
| AC-001 | BLOCKED | [Log](logs/M-0004-verify-20260122-1155.txt)  | Prerequisite M-0002 failed (missing `demultiplex`)           |
| AC-002 | BLOCKED | -                                            | Cannot generate report without upstream output               |
| AC-003 | BLOCKED | [Log](logs/M-0004-verify-20260122-1155.txt)  | Verification script failed at Step 2                         |
| AC-004 | BLOCKED | -                                            | Synthetic data generation passed, but processing failed      |

#### Summary

- Overall: **BLOCKED / FAIL**
- Critical Issue: The `demultiplex` tool is not installed in the environment, preventing M-0002 and M-0003 from running, which M-0004 depends on.
- Recommendation: Implementer must run `pip install demultiplex` in the `TIRTL_analyse` environment.

### Validation Run 4 (2026-01-23 15:21)
- Environment: TIRTL_analyse (PATH explicitly set)
- Commands executed: `export PATH="/Users/zijian/miniconda3/envs/TIRTL_analyse/bin:$PATH" && python scripts/verify.py --milestone M-0004`
- Result: **PASS** (Exit code 0)

| Item | Status | Evidence | Notes / Fix Suggestions |
|------|--------|----------|--------------------------|
| AC-001 | PASS | [Log](logs/M-0004-verify-20260123-1521.txt) | Conservation check passed |
| AC-002 | PASS | [QC Report](build/qc/qc_report.md) | Generated successfully |
| AC-003 | PASS | [Log](logs/M-0004-verify-20260123-1521.txt) | 28/28 checks passed |
| AC-004 | PASS | [Log](logs/M-0004-verify-20260123-1521.txt) | Synthetic data used |

#### Summary
- Overall: **PASS**
- All ACs met. M-0004 is ACCEPTED.

## 9. Appendix — Chat Digest

- Chat ID: `260122_1210` - 环境问题讨论 (OPEN)
  - [M0001] Implementer@Claude_Code → @Validator: QUESTION - demultiplex 环境问题排查
