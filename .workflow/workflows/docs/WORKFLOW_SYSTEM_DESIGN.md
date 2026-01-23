# 多工作流协作系统设计（BASE + Roles + Chat Protocol + Skills + Permissions）

本设计用于在同一仓库内维护多个“AI 协作工作流”，并允许跨平台复用同一套规则。  
核心目标：**目录结构固定 + 分层清晰 + 写入纪律严格 + 授权边界明确**，以降低多 AI 写文件与自动执行时的风险。

---

## 1. 分层与优先级
- **Chat Protocol（传输层）**：文件对话机制（锁、已读指针、格式、关闭）。
- **BASE（工作流层）**：当前 workflow 的业务规则（流程、SSOT、文档结构、验收标准、Skills Policy、Permissions Policy）。
- **Roles（角色层）**：可跨 workflow 复用的职责边界（仅定义“做什么/不做什么”）。
- **Skills（能力依赖层）**：角色可声明需要/可选技能；缺失时按 allowlist 获取并缓存/安装。
- **Permissions（授权边界层）**：允许 agent 在何种范围内“不问直接 edit/执行”，以及哪些动作必须询问用户。

优先级：  
`BASE.md（当前工作流） > CHAT_PROTOCOL.md > .workflow/roles/<Role>.md > Skills`

---

## 2. 固定目录结构（写死）
```text
/.workflow/
  AI_LOADER.md
  AI_WORKFLOW_BASE.md
  workflows/
    CHAT_PROTOCOL.md
    ACTIVE_WORKFLOW.txt
    _skills_cache/
    docs/
      WORKFLOW_SYSTEM_DESIGN.md
      WORKFLOW_SYSTEM_DESIGN_GUIDE.md
    none/
      BASE.md
    <workflow_slug>/
      BASE.md
      .commands/
        <command>.md
      promptbook/
        P-0001.md
        ...
  roles/
    <Role>.md

none workflow_slug: `.workflow/workflows/none/BASE.md` — minimal safety only (no promptbook/SSOT; roles optional unless explicitly assigned).
```

---

## 3. ACTIVE_WORKFLOW.txt
- `.workflow/workflows/ACTIVE_WORKFLOW.txt` 只有一行：当前 `workflow_slug`
- 所有 AI 以此确定“当前启用工作流”

---

## 4. Roles 动态定义（关键）
角色集合不是固定的，由每个 workflow 的 `BASE.md` 定义。  
为保证可解析性，BASE 必须提供：

```md
## Roles Registry (machine-readable)
- Allowed Roles: [RoleA, RoleB, RoleC]
- Allowed Combos: [RoleA+RoleB]
- Disallowed Combos: [RoleB+RoleC]
```

---

## 5. Permissions Policy（关键）
平台层可能允许 agent “不问直接 edit/运行命令/联网/装依赖”。  
为了跨平台一致与可审计，**必须在 BASE 中定义权限边界**：

```md
## Autonomy & Permissions Policy
- Allowed without asking (in-scope): <...>
- Always require user confirmation: <...>
- Audit requirements: <...>
- Safety defaults: <...>
```

原则：
- **范围白名单**：仅允许在 BASE 指定的 scope 内自动改动。
- **高风险动作必问**：删除/大规模重命名/装依赖/执行脚本/改安全配置/触及 secrets 等。
- **强制审计**：自动改动后必须给出文件清单 + 变更摘要，并写回 SSOT 的 Change Log（如适用）。

---

## 6. Chat Protocol（通用）
- `.workflow/workflows/CHAT_PROTOCOL.md` 只定义传输机制，不定义业务语义
- TYPE 语义、归档策略等放在 workflow 的 `BASE.md`

---

## 7. Skills（allowlist + cache + pin）
allowlist only：
- https://github.com/openai/skills
- https://github.com/anthropics/skills
- https://github.com/rominirani/antigravity-skills
- https://github.com/sickn33/antigravity-awesome-skills

统一缓存目录：`.workflow/workflows/_skills_cache/`  
规则：
- 固定 commit/tag
- 默认只加载指令文件；禁止自动执行脚本/二进制（除非 BASE/用户明确允许）
- 使用/安装必须写入 SSOT Change Log（repo+commit/tag+路径+安装目标/手动步骤）

---

## 8. 防呆规则（强制）
- canonical：同名标题以首次出现为准；禁止文末重复整套模板
- append-only：仅 BASE 指定章节允许追加（常见：Change Log、Validation Report）
- 禁止预写空结构/占位符
- PASS 必须证据（由 BASE 定义）


---

## Entry Points（平台入口文件）
为减少“每个 repo 复制整套文件”的成本，本系统采用“两层入口”：

- **短入口（自举）**：`AI_LOADER.md`
  - 负责：缺文件时从 GitHub 拉取/安装 `.workflow/workflows/` 与 `.workflow/roles/`，并修复平台入口文件（stub）
- **长期版规则（规范）**：`AI_WORKFLOW_BASE.md`
  - 负责：Bootstrap Sequence、SSOT 写入纪律、Skills/Permissions 总规则

各平台入口文件只需保持很短，并包含指向 `AI_LOADER.md` 的标记块：
- Codex：`AGENTS.md`
- Claude Code：`.claude/CLAUDE.md`
- Antigravity：`.agent/rules/GEMINI.md`

原则：入口越短越稳定；复杂逻辑放在 `AI_LOADER.md` / `AI_WORKFLOW_BASE.md`。
