# session_mode — RAC Session Loop (template)

1) 读取：ACTIVE_WORKFLOW / CHAT_PROTOCOL / BASE / roles
2) 若角色手册 Required Skills ≠ NONE：确保 skills 可用（按角色手册 Install policy + BASE Skills Policy）
3) 先处理 chat（锁+Last read+UNREAD→READ）
4) 执行业务：
   - Specifier：更新 REQ/TASK/AC
   - Implementer：实现/修复 + Change Log 追加
   - Validator：按 AC 验收 + 验收总结追加
5) 需要沟通：写 chat（建议 TAG）
