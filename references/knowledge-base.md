# 知识库与项目识别

## 1. 配置

固定入口，放在用户目录，任何平台共用同一份：

```
~/.sumof-experience/config.json
```

```json
{ "version": 1, "kb_path": "D:/Knowledge/sumof-experience" }
```

| 环境变量 | 作用 |
|---|---|
| `SUM_OF_EXPERIENCE_HOME` | 改写配置目录（默认 `~/.sumof-experience`） |
| `SUM_OF_EXPERIENCE_KB` | 临时覆盖知识库路径，并写回配置 |

默认知识库：Windows 为 `D:/Knowledge-base`，其它平台为 `~/Knowledge-base`。

首次使用流程：

1. 脚本返回 `needs_config`，并附 `default_kb_path`
2. 询问用户：用默认路径，还是指定其它路径
3. 执行 `--init`（用默认时省略路径参数），脚本创建知识库目录并写配置
4. 重跑解析，进入正常写入

配置缺失时不得跳过询问直接写入；用户确认过一次后，后续不再询问。

## 2. 项目识别

优先级从高到低：

| 顺序 | 依据 | identity | 跨平台 |
|---|---|---|---|
| 1 | `git remote.origin.url` 归一化 + 仓库内相对路径 | `git-remote` | 一致 |
| 2 | 无 remote 的 git 仓库：仓库目录名 + 绝对路径短哈希 + 相对路径 | `git-local` | 同机一致 |
| 3 | 非 git：目录名 + 绝对路径短哈希 | `filesystem` | 同机一致 |

归归一化规则：

1. 去掉协议头（`https://`、`ssh://`、`git+ssh://`）
2. 去掉 userinfo（`git@`、`user:pass@`）
3. `host:owner/repo` 转为 `host/owner/repo`
4. 去掉结尾 `/` 与 `.git`
5. 全小写

slug 生成：

```
取 remote 最后两段（owner、repo）
+ 仓库内相对路径的各段
+ 用 "__" 连接，各段转小写并把非 [a-z0-9] 替换为 "-"
```

实例：

| 场景 | remote | relpath | project_id |
|---|---|---|---|
| 本仓库（多 skill 单仓库） | github.com/wwh259/skills | sumof-experience | `wwh259__skills__sumof-experience` |
| 普通单仓库项目 | github.com/acme/api | 空 | `acme__api` |
| monorepo 子包 | github.com/acme/mono | packages/web | `acme__mono__packages__web` |
| 无 remote | 空 | 空 | `api--a1b2c3` |
| 非 git | 空 | 空 | `my-app__9f8e7d` |

## 3. 知识库目录

```
<KB>/
  index.md                         # 知识库 skill 维护：主题页目录
  log.md                           # 知识库 skill 维护：追加式操作日志
  .registry.json                   # 项目登记表：id / remote / relpath / aliases
  wwh259__skills__sumof-experience/
    .project.json                  # 本项目元信息
    raw/                           # 本 skill 独占写入，只追加
      20261104-<主题>.md
    wiki/                          # 知识库 skill 独占写入，本 skill 不创建、不改动
  acme__api/
    .project.json
    raw/
    wiki/
```

- 知识库不记录任何绝对路径，避免多机 git 同步冲突。
- 同一 remote + 同一相对路径 → 同一目录，与机器、平台、克隆位置无关。
- 项目目录不存在则新建；已存在则直接复用，不重建、不覆盖已有经验文件。
- `raw/` 与 `wiki/` 是相反写入语义：raw 只追加，wiki 可重写。混放会让不可变约束失效。
- 本 skill 只创建 `raw/`；`wiki/`、`index.md`、`log.md` 由知识库 skill 负责。

## 4. 跨平台一致

Trae / WorkBuddy / Codex 都通过本地 shell 与 git 工作，因此识别链路一致，不需要平台专属接口。

前提两条：

1. 各平台配置指向同一个知识库路径，或 `SUM_OF_EXPERIENCE_KB` 相同
2. 各平台工具各自安装一份 skill 时，`SKILL.md` 与 `scripts/` 内容必须一致；推荐把本仓库作为唯一源，用软链或 junction 挂到各平台技能目录

知识库本身建议是独立 git 仓库：写入前 `pull`，写入后由用户自行 `commit/push`。本 skill 不执行 git 操作。

## 5. 降级命令（Python 不可用）

在项目目录依次执行：

```bash
git rev-parse --show-toplevel
git config --get remote.origin.url
```

然后按第 2 节规则手工算 `project_id`，并在 `<KB>/<project_id>/` 下落盘。若 `git` 也不可用，用目录名 + 8 位路径哈希作为 `project_id`。

## 6. 边界情况

| 情况 | 行为 |
|---|---|
| worktree | remote 与相对路径相同，归入同一目录 |
| 仓库改名或转移 | slug 变化，按迁移处理：把新 slug 写入旧条目的 `aliases`，或手工合并目录 |
| fork | owner 不同，进入不同目录，符合预期 |
| 无 remote 的克隆 | `git-local` 标识，换机器会分叉，需手动设别名 |
| 单仓库多项目 | 相对路径区分，不会混桶 |
| 知识库路径在另一台机器不可达 | 脚本返回 `error`，停止写入 |

## 7. 禁止

- 自动 `git commit` / `push`
- 把经验写到项目仓库内（`experience/`、`.experience/` 一律不再使用）
- 配置缺失时使用默认路径兜底
- 把绝对路径写入知识库
