# Aevum 薪火 OS - 项目规则

> **此文件在每次对话开始时自动加载，必须遵守。**

## 对话启动协议

每次新对话开始时，你必须按顺序执行：

1. **读取全景路线图**：读取 `.trae/documents/ROADMAP.md` 理解愿景全景、当前里程碑、下一子阶段
2. **读取项目状态**：读取 `.trae/documents/PROJECT_STATE.md` 确认具体进度
3. **文档同步检查**：运行 `git log --oneline -5`，对比 PROJECT_STATE.md 的 Git 历史 和 CHANGELOG.md。若发现任何 commit 的内容未反映在文档中，**必须先补齐文档，再继续任何开发工作**
4. **确认测试基线**：后端 346 个单元测试 + 前端 64 个组件测试必须全通过
5. **从 ROADMAP.md 中当前里程碑的下一子阶段开始执行**

## 闭环检查清单（每轮工作结束前必须执行）

**违反此清单即视为任务未完成。** 详见 `Autonomous_Project_Execution_Charter.md` 第 5.1 节。

- [ ] 代码已 git commit
- [ ] PROJECT_STATE.md 已同步（新模块/Bug修复/测试数变化/迁移变更/Git历史）
- [ ] CHANGELOG.md 已同步（Added/Fixed/Changed 条目）
- [ ] TEST_REPORT.md 已同步（测试数/测试文件清单）
- [ ] TASKS.md 已同步（任务状态更新）
- [ ] ROADMAP.md 已同步（里程碑进度标记）
- [ ] 后端 + 前端测试全通过，无回归
- [ ] 对比 `git log --oneline -5`，确认每个 commit 的内容都已反映在文档中

## 关键文件位置

| 文件 | 用途 |
|------|------|
| `Autonomous_Project_Execution_Charter.md` | 执行宪章（最高规则） |
| `.trae/documents/ROADMAP.md` | **全景路线图（M0-M5 完整规划）** |
| `.trae/documents/PROJECT_STATE.md` | 项目唯一可信状态来源 |
| `.trae/documents/CHANGELOG.md` | 变更日志 |
| `.trae/documents/TEST_REPORT.md` | 测试报告 |
| `.trae/documents/TASKS.md` | 任务看板 |

## 架构约束

- 六层架构：Human Expression -> Agent Execution -> Experience -> Retrieval -> Evaluation -> Governance
- 双世界分离：HumanExpression 和 Experience 独立表，无直接外键
- 四级优先级链：用户 -> 社区 -> 全球 -> 外部
- 人机分离四原则：人类数据不进图谱 / Agent不改写人类表达 / 人类输出仅供观察 / Agent输出必须结构化

## 验收标准执行规则

- 每个子阶段的验收标准必须**全部满足**才能进入下一子阶段
- 每个里程碑的整体验收标准必须**全部满足**才能进入下一里程碑
- 验收结果记录在 PROJECT_STATE.md 中
