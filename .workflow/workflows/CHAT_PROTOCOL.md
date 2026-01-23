# CHAT_PROTOCOL v1 (通用传输层)

本文件定义“跨 AI 文件聊天”的**通用传输协议**，与具体工作流无关。  
业务语义（TYPE 列表、归档落点、何时必须发消息等）由当前工作流 `BASE.md` 定义。

---

## 1. Chat 文件位置与命名
- 默认 chat 文件放在：`.workflow/workflows/<active_workflow>/`
- 匹配：`temp_chat_*.txt`
- 命名：`temp_chat_<id>.txt`（id 推荐 `yymmdd_hhmm` 或 `yymmdd_hhmm_<short>`）

---

## 2. Header（文件头）
```txt
# CHAT v3
# Chat ID: <id>
# Status: OPEN|CLOSED
# Participants:
# - <Role>@<Identity>
# - <Role>@<Identity>
# Last read:
# - <Role>@<Identity>: <line_number>
# - <Role>@<Identity>: <line_number>
# Purpose: <one-line>
```

---

## 3. 消息格式（append-only）
```txt
[M0001] FROM:<Role>@<Identity> | TYPE:<AnyString> | FLAG:UNREAD|READ | TAG:@<Role>|@All
<正文...>
```
- 发送时 `FLAG:UNREAD`，接收方处理后改为 `FLAG:READ`
- 目标判定：TAG 为 @All 或包含接收方 Role；TAG 缺失视为广播

---

## 4. 已读指针（不建额外文件）
1) 读取 header 中自己的 `Last read` 行号 N
2) 从 N+1 行开始读新增内容
3) 将相关消息 UNREAD→READ
4) 更新 header 中自己的 `Last read` 为当前总行数

---

## 5. 写冲突锁（重命名 `_editing`）
- 若存在 `temp_chat_<id>_editing.txt`：只读不写
- 写入/改 FLAG/改 Last read 时：
  1) `temp_chat_<id>.txt` → `temp_chat_<id>_editing.txt`
  2) 修改
  3) 改回原名

---

## 6. Close / Ack（底层结构）
- 一方发 `CLOSE_REQUEST`，另一方发 `CLOSE_ACK`
- 最终把 header `Status` 改为 `CLOSED`
- 是否归档 digest 由 BASE 决定

---

## 7. 禁止事项
- 禁止改旧消息正文（只能追加；允许改 header 的 Last read/Status 与消息 header 的 FLAG）
- 禁止插入或重排历史消息
