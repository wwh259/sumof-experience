# 知识库与项目识别

> 知识库是独立项目 `knowledge_base`，本 skill 只是它的一个外部写入者。
> 三方职责与完整契约见 `<KB>/docs/契约-经验链路.md`。

## 1. 配置（每台机器一次）

固定入口，放在用户目录，任何平台共用同一份：

```
~/.sumof-experience/config.json
```

```json
{ "version": 1, "kb_path": "<用户首次使用时指定的绝对路径>" }
```

| 环境变量 | 作用 |
|---|---|
| `SUM_OF_EXPERIENCE_HOME` | 改写配置目录（默认 `~/.sumof-experience`） |
| `SUM_OF_EXPERIENCE_KB` | 临时覆盖知识库路径，并写回配置 |

默认路径：Windows 为 `D:/Knowledge-base`，其它平台为 `~/Knowledge-base`。**默认路径是固定常量，不随任何更新改动**；本机若不用默认路径，首次使用时由用户指定，执行 `--init "<用户指定的绝对路径>"`，之后不再询问。`--show` 可随时查看当前配置。
>
> **通用 skill 约束**：仓库内不写任何本机真实路径（示例一律用占位符）；配置文件在用户目录、不进 git。首次运行返回 `needs_config` 时必须先问用户，不得替他选路径、也不得直接采用默认路径。

> 配置只解决「路径在哪」，**不定义「里面长什么样」**。结构由知识库仓库的 README 与契约文档定义、随仓库同步；换机器时靠它对齐，不靠人记。

首次流程：

1. `python scripts/resolve_project.py --show` → `needs_config` 时询问用户：用默认路径，还是指定真实知识库路径
2. `python scripts/resolve_project.py --init "<确认的路径>"`
3. 脚本直接返回 `ok`，含 `experience_dir` / `project` / `existing_sources`，无需重跑

| status | 动作 |
|---|---|
| `ok` | 用返回的 `experience_dir` 作为唯一输出目录 |
| `needs_config` | 询问用户确认路径后执行 `--init`；在此之前不得写入任何文件 |
| `error` | 停止并向用户报告原因 |

## 2. 知识库的两层结构

```
<KB>/
├─ raw/<项目>/<平台>/<日期>_<主题>.md      # L0 原文，无判断，只进不改
├─ experience/<项目>/YYYYMMDD-<主题>.md    # L1 经验卡，本 skill 独占只追加
├─ _index.json                             # 会话台账，本 skill 只读
├─ _candidates/ · _index/ · _inbox/        # 导航 / 视图 / 暂存，本 skill 不碰
└─ scripts/ · docs/                        # KB 自己的工具与文档
```

- **两层物理隔离**：KB 的「L0 不写结论」红线只约束 `raw/`；`experience/` 本来就是结论层，不受该约束。
- KB 的 `check.py` 只扫 `raw/`，不会把经验卡误判成 L0 违规。
- 本 skill 只创建 `experience/<项目>/`：不写台账、不建索引、不改 `raw/`、不碰分身记忆。

## 3. 项目键

**唯一来源**：KB 台账 `_index.json` 里各条目的 `project` 字段（即 `raw/<项目>/` 的真实目录名）。

匹配顺序：

1. 取当前目录的各路径段（从深到浅），与台账项目名做大小写不敏感匹配；命中即用台账里的规范写法（`project_source: kb-index`）
2. 都没命中 → 用当前目录名，剥掉 Windows 非法字符（`project_source: cwd-name`）
3. 不再用 git remote 生成 slug；`remote` 只作为返回字段备查，不落盘、不做目录名

这样 `experience/<项目>/` 与 `raw/<项目>/` 天然同名，分身归纳时也不会对不上号。台账里没有的新项目照常写入 `experience/`，但**不代 KB 往台账里登记**——是否归档该项目由 KB 的采集流程决定。

## 4. 跨平台一致

Trae / WorkBuddy / Codex 都通过本地文件读写，不需要平台专属接口。前提两条：

1. 各平台配置指向同一个知识库路径（或 `SUM_OF_EXPERIENCE_KB` 相同）
2. 各平台安装的 `SKILL.md` 与 `scripts/` 内容一致；推荐把本仓库作为唯一源，用软链 / junction 挂到各平台技能目录

`resolve_project.py` 只读 KB 台账、只建 `experience/<项目>/`，不写任何共享状态，因此多平台并发写卡不会互相覆盖（文件名仍按 `YYYYMMDD-<主题>.md`，同一天同主题需人工避开）。知识库建议是独立 git 仓库；本 skill 不执行 git 操作，提交由用户决定。

## 5. 降级命令（Python 不可用）

1. 读 `<KB>/_index.json` 取所有 `project` 值，或直接 `ls <KB>/raw/`
2. 用当前目录名（或任一路径段）匹配，得项目键
3. `grep -h '^source:' <KB>/experience/<项目>/*.md` 查重——**同一源文件已抽过就不要再写**
4. 在 `<KB>/experience/<项目>/` 下写卡，再手工跑 `scripts/validate_card.py <文件>`

## 6. 边界情况

| 情况 | 行为 |
|---|---|
| KB 路径在另一台机器不可达 | `error`，停止写入 |
| 指向的目录不像 KB（缺 `raw/` 与 `_index.json`） | 仍可写，返回 `warning`，项目名按目录名 |
| 台账里没有该项目 | 用 cwd 目录名新建 `experience/<项目>/`，不动台账 |
| 同一源文件抽第二次 | `existing_sources` 命中即跳过；卡片不可变，不能靠覆盖修正 |
| 仓库改名 / 转移 | 项目键以 KB 台账为准；重命名需人工同步 `raw/` 与 `experience/` 两边 |
| worktree / 多平台同项目 | 目录名一致 → 落到同一个 `experience/<项目>/` |

## 7. 禁止

- 写 `<KB>/raw/` 下的任何文件，或改动 `_index.json` / `_candidates/` / `_index/`
- 写数字分身的 `knowledge/02-记忆/`（那是归纳，不是抽取）
- 在项目子目录里放 `README.md` 等非卡片 md（`validate_card.py` 会把它当卡扫描并 FAIL；说明文件放 `experience/` 根）
- 把绝对路径写进知识库文件
- 配置缺失时用默认路径兜底
- 自动 `git commit` / `push`
