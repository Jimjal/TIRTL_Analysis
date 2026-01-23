# TIRTL-seq Demultiplex Pipeline 运行手册

## 概述

本文档说明如何使用统一 CLI 入口 (`scripts/run_pipeline.py`) 运行 TIRTL-seq 分板分孔流水线。

**流水线阶段**:
1. **合成数据生成** (可选) - 生成测试用合成 FASTQ
2. **Well Demux (M-0002)** - 按 well 条码 (i5+i7) 分孔
3. **Plate Demux (M-0003)** - 按 plate 条码 (R1 前缀) 分板
4. **QC Report (M-0004)** - 守恒检查、统计报告

---

## 1. 环境准备

### 1.1 激活 Conda 环境

```bash
conda activate TIRTL_analyse
```

### 1.2 确认 demultiplex 工具已安装

```bash
demultiplex --help
```

如未安装，执行:

```bash
pip install demultiplex
```

### 1.3 确认 PyYAML 已安装

```bash
python -c "import yaml; print('OK')"
```

如未安装，执行:

```bash
pip install pyyaml
```

---

## 2. 配置文件

### 2.1 配置文件位置

示例配置文件: `config/tirtl_config.example.yaml`

### 2.2 创建自定义配置

复制示例配置并修改:

```bash
cp config/tirtl_config.example.yaml config/my_config.yaml
```

### 2.3 配置文件结构

```yaml
# 输入文件
input:
  r1: "path/to/R1.fastq.gz"  # R1 FASTQ (必填)
  r2: "path/to/R2.fastq.gz"  # R2 FASTQ (可选)

# 条码表
barcodes:
  well: "TIRTL_barcode_well.csv"   # Well 条码表
  plate: "TIRTL_barcode_plate.csv" # Plate 条码表

# 输出目录
output:
  root_dir: "build"
  well_demux_dir: "demux"
  plate_demux_dir: "plate_demux"
  qc_dir: "qc"

# 日志配置
logging:
  log_dir: "logs"
  log_prefix: "pipeline"

# 阶段开关
stages:
  generate_synthetic: true  # 是否生成合成数据
  well_demux: true          # 是否执行 Well Demux
  plate_demux: true         # 是否执行 Plate Demux
  qc_report: true           # 是否执行 QC 报告
```

---

## 3. 运行方式

### 3.1 使用合成数据测试 (推荐首次运行)

```bash
python scripts/run_pipeline.py --config config/tirtl_config.example.yaml --verbose
```

此命令将:
1. 生成合成 FASTQ 数据
2. 执行 Well Demux
3. 执行 Plate Demux
4. 生成 QC 报告

### 3.2 查看配置 (Dry Run)

不执行流水线，仅显示解析后的配置:

```bash
python scripts/run_pipeline.py --config config/tirtl_config.example.yaml --dry-run
```

### 3.3 使用真实数据

**重要**: 真实数据路径不要提交到仓库！

创建本地配置文件:

```bash
cp config/tirtl_config.example.yaml config/local_config.yaml
```

编辑 `config/local_config.yaml`:

```yaml
input:
  r1: "/local/path/to/experiment_R1.fastq.gz"
  r2: "/local/path/to/experiment_R2.fastq.gz"

stages:
  generate_synthetic: false  # 关闭合成数据生成
```

运行:

```bash
python scripts/run_pipeline.py --config config/local_config.yaml --verbose
```

### 3.4 仅运行部分阶段

例如，仅运行 Well Demux:

```yaml
stages:
  generate_synthetic: false
  well_demux: true
  plate_demux: false
  qc_report: false
```

---

## 4. 输出文件

### 4.1 目录结构

```
build/
├── synthetic_R1.fq.gz      # 合成数据 R1 (如启用)
├── synthetic_R2.fq.gz      # 合成数据 R2 (如启用)
├── synthetic_manifest.csv  # 合成数据清单
├── demux/                  # Well Demux 输出
│   ├── well_A01.fastq.gz
│   ├── well_A02.fastq.gz
│   ├── unknown.fastq.gz
│   └── demux_stats.tsv
├── plate_demux/            # Plate Demux 输出
│   ├── plate_MP_V4_Ca_P5_UD01/
│   │   ├── well_A01.fastq.gz
│   │   └── well_A02.fastq.gz
│   ├── plate_UNKNOWN/
│   └── plate_demux_stats.tsv
└── qc/                     # QC 输出
    ├── plate_well_counts.tsv
    ├── plate_well_matrix.tsv
    ├── summary.json
    └── qc_report.md

logs/
├── pipeline-20260122-1430.txt          # 运行日志
└── pipeline-20260122-1430.summary.json # 运行摘要
```

### 4.2 日志文件说明

- `pipeline-*.txt`: 详细运行日志，包含每个阶段的命令和输出
- `pipeline-*.summary.json`: 机器可读摘要，包含:
  - 阶段结果 (stage_results)
  - AC 检查结果 (acceptance_criteria)
  - 输出路径 (paths)

---

## 5. 验证运行结果

### 5.1 使用 verify.py 验证

```bash
python scripts/verify.py --milestone M-0005
```

验证内容:
- AC-001: 配置文件存在且可解析
- AC-002: CLI 可运行全链路
- AC-003: 生成日志和摘要
- AC-004: 运行文档存在
- AC-005: verify.py 退出码 0

### 5.2 检查 QC 报告

查看生成的 QC 报告:

```bash
cat build/qc/qc_report.md
```

检查守恒状态和 AC 结果。

---

## 6. 常见问题

### Q1: demultiplex 找不到

**症状**: `ERROR: demultiplex not found`

**解决方案**:
```bash
conda activate TIRTL_analyse
pip install demultiplex
```

### Q2: PyYAML 未安装

**症状**: `ERROR: PyYAML not installed`

**解决方案**:
```bash
pip install pyyaml
```

### Q3: 配置文件路径错误

**症状**: `ERROR: Config file not found`

**解决方案**: 检查配置文件路径是否正确，使用相对路径时以项目根目录为基准。

### Q4: 条码文件找不到

**症状**: `ERROR: Barcode file not found`

**解决方案**: 确认 `TIRTL_barcode_well.csv` 和 `TIRTL_barcode_plate.csv` 存在于项目根目录。

### Q5: 真实数据路径不要提交

**重要**: 在 `.gitignore` 中已包含 `config/local_*.yaml`，请将包含真实数据路径的配置命名为 `local_*.yaml` 以避免意外提交。

---

## 7. 高级配置

### 7.1 调整错配容忍度

```yaml
advanced:
  mismatch: 2  # 允许 2 个错配 (默认 1)
```

### 7.2 保留临时文件 (调试)

```yaml
advanced:
  keep_temp: true
```

### 7.3 自定义合成数据参数

```yaml
stages:
  generate_synthetic: true
  synthetic_params:
    wells: 4        # 生成 4 个 well
    plates: 3       # 使用 3 个 plate
    num_reads: 100  # 每个 well×plate 100 条 reads
    noise_reads: 20 # 20 条噪声 reads
```

---

## 8. 相关文档

- [P-0005 Promptbook](.workflow/workflows/relay_accept_change/promptbook/P-0005_CLI_config.md)
- [QC 报告说明](build/qc/qc_report.md) (运行后生成)
- [verify.py 使用说明](scripts/verify.py)

---

*此文档为 P-0005 TASK-001 交付物之一*
