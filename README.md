# SumOfExperience

把对话或文件中的可复用经验，沉淀为结构化经验卡，并按项目自动归档到知识库。目前主要用于AI应用开发项目的开发总结。

这是一个独立运行的经验总结 skill：只负责**抽取**与**写入** `experience/` 层，不做索引、不做检索、不写数字分身记忆。
知识库（`knowledge_base`）与数字分身（`digital_twin`）是独立项目，三者通过文件契约解耦：KB 管存储，本 skill 管抽取，分身管归纳。

## 特性

- **原子经验卡**：每条经验固定 8 行字段，可被机器稳定解析
- **三轴坐标**：阶段 / 分层 / 模块，一张卡可横跨多个模块而不混乱
- **自动项目归档**：项目键以 KB 台账 `_index.json` 的 `project` 字段为准，跨平台、跨设备落到同一目录
- **可追溯修订**：正文与证据不可变，结论冲突通过 `supersedes` 取代
- **结构校验**：`validate_card.py` 强制 schema v1，落盘后必跑

## 工作方式

```
对话 / 文件
   │
   ├─ 抽取 5 类内容：决策 / 坑 / 模式 / 约束 / 有效路径
   ├─ 标注坐标：阶段 × 分层 × 模块
   ├─ 写经验卡（固定结构 + 证据 + 置信度）
   └─ 写入 <知识库>/experience/<项目>/
```

## 快速开始

### 1. 安装

把本仓库放到各平台读取 skill 的目录，或建立目录软链（Windows 可用 `mklink /J`）。仓库内容跨平台一致，无第三方依赖。

### 2. 首次配置知识库

```bash
python scripts/resolve_project.py --cwd <项目目录>
# 本机 python 可用；若指向应用商店存根（退出码 9009），改用 py 或 python3
```

首次运行返回 `needs_config`，按提示确认知识库路径后初始化：

```bash
python scripts/resolve_project.py --init                 # 使用默认路径
python scripts/resolve_project.py --init "<用户指定的知识库绝对路径>"   # 首次使用，路径由用户确认
```

默认路径：Windows 为 `D:/Knowledge-base`，其它平台为 `~/Knowledge-base`，**固定不变**；本机若不用默认路径，首次使用时由用户指定 `--init "<绝对路径>"`，之后不再询问。
配置写在 `~/.sumof-experience/config.json`（机器级，不随仓库同步），可用 `--show` 查看；目录结构的定义以知识库仓库的 README 与契约文档为准，不靠配置传递。

### 3. 使用

对话结束后说「总结经验」「沉淀经验」「复盘这个对话」，或对某份文件说「提取其中的可复用经验」。

输出位置：

```
<KB>/experience/<项目>/YYYYMMDD-<主题>.md
```

### 4. 校验

```bash
python scripts/validate_card.py <文件或目录>
```

## 项目识别

项目键以知识库台账 `_index.json` 的 `project` 字段为单一来源，与 `raw/<项目>/` 目录同名；台账里没有该名字时用当前目录名。不再另造 git slug，避免两套 ID 对不上。

知识库的两层结构（本 skill 只写第二层）：

```
<KB>/
├─ raw/<项目>/<平台>/<日期>_<主题>.md    # L0 原文，无判断，只进不改
├─ experience/<项目>/YYYYMMDD-<主题>.md  # L1 经验卡，本 skill 独占只追加
├─ _index.json                          # 台账，本 skill 只读
└─ _candidates/ · _index/               # 导航与视图，本 skill 不碰
```

## 经验卡格式

正文固定 6 节：结论 / 经验 / 失败与反例 / 复用清单 / 边界 / 关联。

```markdown
### E1 重排阈值必须按查询类型分组标定
- 坐标：S5 测试评估 / Application / Retrieval｜类型：pitfall
- 触发：检索召回不足，准备统一调阈值时
- 做法：按查询类型分组标定，不设全局单值
- 原因：不同查询类型的分数分布不同，单阈值会牺牲长尾
- 证据：复现 3 次；评估集分组对比
- 置信度：0.8
- 背景：用于 Retrieval 模块的阈值调优
```

坐标轴取值：

- 阶段：`S1 需求分析` · `S2 技术选型` · `S3 工程规范` · `S4 模块开发` · `S5 测试评估` · `S6 部署上线` · `S7 运维迭代` · `跨阶段`
- 分层：`Interface` · `Application` · `Domain` · `Infrastructure` · `部署资产` · `通用`
- 模块：`Conversation` · `Knowledge` · `Retrieval` · `Agent` · `Governance` · `Platform` · `通用`

完整规范见 [format-spec.md](references/format-spec.md)，模板见 [experience-template.md](assets/experience-template.md)，示例见 [examples/](examples/)。

## 修订规则

| 层 | 规则 |
|---|---|
| 正文（结论 / 经验 / 反例 / 证据） | 永久不可修改 |
| 元数据（坐标 / 标签 / 状态 / 关联） | 可校正 |

结论有误时新建一张卡，用 `supersedes` 指向旧卡；旧卡只改 `status` 与 `superseded_by`。这样既保留证据，又允许结论演进。

## 目录

| 路径 | 作用 |
|---|---|
| `SKILL.md` | skill 入口，触发条件与执行流程 |
| `references/knowledge-base.md` | 知识库两层结构、配置、项目键、降级命令 |
| `references/ai-app-taxonomy.md` | 三轴枚举与归类规则 |
| `references/format-spec.md` | 卡片字段、规模上限、拆分与修订 |
| `references/extraction-rules.md` | 采什么、丢什么、置信度分级 |
| `assets/experience-template.md` | schema v1 骨架 |
| `scripts/resolve_project.py` | 解析知识库与项目目录 |
| `scripts/validate_card.py` | schema v1 校验器 |
| `examples/` | 样张与回归样本 |

> **通用性约定**：本仓库不含任何本机真实路径；`schema_version` 与默认知识库路径是固定常量，后续更新不改。

## 版本

当前 `schema_version: 1`。模板变更遵循：

- 新增可选字段：minor，向后兼容
- 修改枚举或必填项：major，附迁移脚本
- 历史卡正文不动，元数据可校正

## 许可

暂未指定。
