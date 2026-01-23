# TIRTL-seq 真实数据运行手册

## 概述

本手册说明如何在 **不提交真实 FASTQ 数据到仓库** 的前提下，使用 P-0005 的 CLI/配置在本地或安全环境运行全链路分析，并输出合规的日志、审计记录与交付包。

**适用场景**:
- 本地工作站运行真实实验数据
- 安全计算环境（HPC、云实例）
- 协作交付与审计

---

## 1. 前置条件

### 1.1 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | macOS / Linux |
| Python | 3.8+ |
| Conda 环境 | `TIRTL_analyse` |
| 依赖工具 | `demultiplex`, `pyyaml` |
| 磁盘空间 | 至少 2× 输入数据大小 |
| 内存 | 建议 8GB+ |

### 1.2 环境激活

```bash
conda activate TIRTL_analyse

# 验证依赖
demultiplex --help
python -c "import yaml; print('PyYAML OK')"
```

### 1.3 仓库准备

```bash
# 克隆仓库（如未克隆）
git clone <repo_url>
cd 260105_DN_project_TIRTL_Analysis

# 确认条码文件存在
ls TIRTL_barcode_well.csv TIRTL_barcode_plate.csv
```

---

## 2. 数据布局与路径准备

### 2.1 真实数据存放原则

**核心规则**: 真实 FASTQ 数据 **绝对不能** 放在仓库目录内，也不能提交到 Git。

**推荐数据布局**:

```
/local/data/                          # 本地数据根目录（仓库外）
└── experiment_20260120/
    ├── raw/
    │   ├── Sample_R1.fastq.gz        # 原始 R1
    │   └── Sample_R2.fastq.gz        # 原始 R2
    └── results/                      # 输出目录（可选，也可放仓库内的 build/）
        ├── demux/
        ├── plate_demux/
        └── qc/

/path/to/repo/                        # 仓库目录
├── config/
│   └── local_exp20260120.yaml        # 本地配置（指向真实数据）
├── build/                            # 可选：输出到仓库内（注意 .gitignore）
└── logs/                             # 运行日志
```

### 2.2 配置文件准备

**步骤 1**: 复制示例配置

```bash
cp config/tirtl_config.example.yaml config/local_real_data.yaml
```

**步骤 2**: 编辑配置，指向真实数据

```yaml
# config/local_real_data.yaml

input:
  # 指向真实数据的绝对路径
  r1: "/local/data/experiment_20260120/raw/Sample_R1.fastq.gz"
  r2: "/local/data/experiment_20260120/raw/Sample_R2.fastq.gz"

barcodes:
  well: "TIRTL_barcode_well.csv"
  plate: "TIRTL_barcode_plate.csv"

output:
  # 输出到仓库外（推荐）
  root_dir: "/local/data/experiment_20260120/results"
  # 或输出到仓库内（确保 .gitignore 正确）
  # root_dir: "build"

stages:
  generate_synthetic: false  # 关闭合成数据生成
  well_demux: true
  plate_demux: true
  qc_report: true

logging:
  log_dir: "logs"  # 日志仍保存在仓库内供审计
```

### 2.3 .gitignore 检查

**确认以下内容在 `.gitignore` 中**:

```gitignore
# 真实数据相关
*.fastq
*.fastq.gz
*.fq
*.fq.gz

# 本地配置（含真实路径）
config/local_*.yaml

# 大型输出（如需提交请手动添加）
build/
```

**检查命令**:

```bash
# 查看 .gitignore 内容
cat .gitignore | grep -E "(fastq|local_)"

# 确认真实数据不在 git 跟踪中
git status --porcelain | grep -E "\.fastq|\.fq"  # 应无输出
```

---

## 3. 执行步骤

### 3.1 自检（Dry Run）

在运行真实数据前，先用合成数据验证环境:

```bash
# 使用示例配置运行合成数据
python scripts/run_pipeline.py --config config/tirtl_config.example.yaml --verbose

# 验证结果
python scripts/verify.py --milestone M-0005 --output-dir build_dryrun
```

### 3.2 运行真实数据

```bash
# 激活环境
conda activate TIRTL_analyse

# 运行流水线
python scripts/run_pipeline.py --config config/local_real_data.yaml --verbose
```

### 3.3 监控运行

**预估资源与时间**:

| 数据规模 | 预估时间 | 内存峰值 | 磁盘输出 |
|----------|----------|----------|----------|
| 1M reads | ~5 min | ~2 GB | ~500 MB |
| 10M reads | ~30 min | ~4 GB | ~5 GB |
| 100M reads | ~3 hr | ~8 GB | ~50 GB |

*注: 实际时间取决于 CPU、I/O 速度和 well/plate 数量。*

### 3.4 检查输出

```bash
# 检查输出目录结构
ls -la /local/data/experiment_20260120/results/

# 检查 QC 报告
cat /local/data/experiment_20260120/results/qc/qc_report.md

# 检查日志
cat logs/pipeline-*.txt | tail -50
```

---

## 4. 数据治理与合规

### 4.1 禁止事项

| 禁止操作 | 原因 |
|----------|------|
| 将真实 FASTQ 放入仓库目录 | 数据隐私与仓库大小 |
| 将真实 FASTQ 提交到 Git | 不可逆，违反数据政策 |
| 在配置中使用相对路径指向仓库外真实数据 | 路径混淆，安全风险 |
| 在日志中记录完整样本 ID / 敏感信息 | 隐私泄露风险 |

### 4.2 日志脱敏建议

流水线日志会记录文件路径。若路径包含敏感信息（如患者 ID），建议:

1. **使用代号**: 将真实样本 ID 替换为代号（如 `Sample_001`）
2. **存放映射表**: 在安全位置（非仓库）保存 ID 映射
3. **交付前审查**: 交付日志前检查是否包含敏感路径

### 4.3 缓存清理

运行完成后，清理临时文件:

```bash
# 清理 Python 缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 清理临时配置（如使用了临时文件）
rm -f /tmp/tmp*.yaml

# 检查是否有遗留的真实数据
find . -name "*.fastq*" -o -name "*.fq*"  # 应无输出
```

### 4.4 Git 提交前检查

```bash
# 检查暂存区是否包含大文件或敏感文件
git diff --cached --stat | grep -E "Bin|fastq|fq"

# 检查未跟踪文件
git status --porcelain | grep "??" | grep -E "fastq|fq|local_"

# 如发现问题，取消暂存
git reset HEAD <file>
```

---

## 5. 审计与交付物

### 5.1 运行后必须保留的文件

| 文件 | 位置 | 用途 |
|------|------|------|
| 运行日志 | `logs/pipeline-*.txt` | 执行步骤与状态记录 |
| 运行摘要 | `logs/pipeline-*.summary.json` | 机器可读 AC 状态 |
| QC 长表 | `qc/plate_well_counts.tsv` | 计数统计 |
| QC 矩阵 | `qc/plate_well_matrix.tsv` | 热图数据 |
| QC 摘要 | `qc/summary.json` | 守恒检查结果 |
| QC 报告 | `qc/qc_report.md` | 人类可读报告 |
| Well Demux 统计 | `demux/demux_stats.tsv` | 分孔统计 |
| Plate Demux 统计 | `plate_demux/plate_demux_stats.tsv` | 分板统计 |

### 5.2 交付包建议

**交付物（不含原始 FASTQ）**:

```
delivery_package/
├── README.md                 # 交付说明
├── logs/
│   ├── pipeline-*.txt
│   └── pipeline-*.summary.json
├── qc/
│   ├── plate_well_counts.tsv
│   ├── plate_well_matrix.tsv
│   ├── summary.json
│   └── qc_report.md
├── stats/
│   ├── demux_stats.tsv
│   └── plate_demux_stats.tsv
└── config/
    └── run_config.yaml       # 脱敏后的配置（路径替换为占位符）
```

**打包命令**:

```bash
# 创建交付目录
mkdir -p delivery_package/{logs,qc,stats,config}

# 复制审计文件
cp logs/pipeline-*.txt logs/pipeline-*.summary.json delivery_package/logs/
cp qc/*.tsv qc/*.json qc/*.md delivery_package/qc/
cp demux/demux_stats.tsv plate_demux/plate_demux_stats.tsv delivery_package/stats/

# 创建脱敏配置（手动编辑替换真实路径）
cp config/local_real_data.yaml delivery_package/config/run_config.yaml
# 编辑 run_config.yaml，将真实路径替换为 <DATA_PATH>

# 打包
tar -czvf delivery_$(date +%Y%m%d).tar.gz delivery_package/
```

### 5.3 交付检查清单

在交付前确认:

- [ ] 交付包不包含任何 `.fastq` / `.fq` 文件
- [ ] 配置文件中的真实路径已脱敏
- [ ] 日志中无敏感样本 ID / 患者信息
- [ ] QC 报告显示守恒检查 PASS
- [ ] 包含运行时间戳与环境信息

---

## 6. 常见故障排查

### 6.1 demultiplex 找不到

**症状**: `ERROR: demultiplex not found`

**解决**:
```bash
conda activate TIRTL_analyse
pip install demultiplex
```

### 6.2 内存不足

**症状**: 进程被杀死 (Killed) 或 MemoryError

**解决**:
- 减少并行度（如有）
- 使用更大内存的机器
- 分批处理（拆分输入文件）

### 6.3 磁盘空间不足

**症状**: `No space left on device`

**解决**:
- 清理临时文件
- 将输出目录指向更大的磁盘
- 删除中间文件后重新运行

### 6.4 权限问题

**症状**: `Permission denied`

**解决**:
```bash
# 检查文件权限
ls -la /path/to/data/

# 如需要，修改权限（谨慎操作）
chmod +r /path/to/data/*.fastq.gz
```

### 6.5 守恒检查失败

**症状**: QC 报告显示 `Conservation check: FAIL`

**可能原因**:
- 输入文件损坏或不完整
- 条码文件与实际条码不匹配
- 中间步骤被意外中断

**解决**:
1. 检查输入文件完整性: `gzip -t input.fastq.gz`
2. 核对条码表与实验设计
3. 清理输出目录后重新运行

---

## 7. 自检与验证

### 7.1 合成数据自检

```bash
# 完整自检流程
python scripts/verify.py --milestone M-0006 --output-dir build_m0006 --verbose
```

### 7.2 真实数据结果验证

运行后执行以下检查:

```bash
# 1. 检查运行状态
grep "Overall Status" logs/pipeline-*.txt

# 2. 检查守恒
cat qc/summary.json | python -c "import sys,json; d=json.load(sys.stdin); print('Conservation:', d['conservation_check']['conserved'])"

# 3. 检查 AC 状态
cat logs/pipeline-*.summary.json | python -c "import sys,json; d=json.load(sys.stdin); print('Status:', d['overall_status'])"
```

### 7.3 结果留痕模板

运行完成后，建议创建运行记录:

```markdown
# 运行记录 - [实验名称]

- 运行日期: YYYY-MM-DD HH:MM
- 操作员: [姓名]
- 环境: [机器名称/IP], TIRTL_analyse conda env
- 输入数据:
  - R1: [文件名, 大小, MD5]
  - R2: [文件名, 大小, MD5]
- 配置文件: config/local_[name].yaml
- 输出目录: [路径]
- 运行状态: PASS / FAIL
- 日志文件: logs/pipeline-[timestamp].txt
- 备注: [任何异常或注意事项]
```

---

## 附录

### A. 相关文档

- [CLI 运行手册](runbook_cli.md) - 配置与 CLI 使用说明
- [QC 报告说明](../build/qc/qc_report.md) - QC 输出格式
- [P-0006 Promptbook](../.workflow/workflows/relay_accept_change/promptbook/P-0006_Real_data_runbook.md)

### B. 联系与支持

如遇问题，请联系项目负责人或在仓库 Issues 中报告。

---

*此文档为 P-0006 TASK-001 交付物*
*最后更新: 2026-01-23*
