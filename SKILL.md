---
name: summarize-experience
description: 从对话或文件中提取可复用的经验资产，按项目自动归档到指定知识库。当用户说「总结经验」「沉淀经验」「提取经验」「复盘这个对话」「这份文档有什么可复用的经验」时使用；也适用于任务、调试、评审结束后的结论归档。
---

# 经验总结

把一次对话或一个文件的价值压到最大化：只保留可复用、有证据、能指导下次决策的内容，并写入知识库中对应项目的目录。

## 边界

只做两件事：抽取经验、写入知识库的 `experience/` 层。

不写知识库台账、不建索引、不改 `raw/`、不写数字分身的记忆条目、不执行 git 操作。
采集 / 台账 / 视图归 `knowledge_base`；把经验卡归纳成 L2 记忆归 `digital_twin`。三方平时独立维护，只在抽取与归纳时通过文件连接。

## 第一步：解析知识库与项目（必须先执行）

```bash
python <本 skill 目录>/scripts/resolve_project.py --cwd <项目目录>
# 本机 python 可用；若指向应用商店存根（退出码 9009），改用 py 或 python3
```

脚本返回单行 JSON，按 `status` 分支处理：

| status | 动作 |
|---|---|
| `ok` | 使用返回的 `experience_dir` 作为唯一输出目录 |
| `needs_config` | 询问用户：用默认路径还是指定其它路径；确认后执行 `--init`（用默认时省略路径参数），再重跑解析 |
| `error` | 停止并向用户报告原因 |

规则：

- `needs_config` 时不得写入任何文件，也不得直接采用默认路径；须经用户确认一次。
- 未取得 `project` 与 `experience_dir` 前不得动笔。
- `experience/<项目>/` 是只追加层：写入后不得修改、不得覆盖。
- **写卡前查重**：看返回的 `existing_sources`，同一源文件已抽过就不再产出新卡；卡片不可变，重复抽取无法覆盖修正。
- 项目键以 KB 台账 `_index.json` 的 `project` 为准，与 `raw/<项目>/` 同名；台账里没有时用当前目录名。
- 同一项目在 Trae / WorkBuddy / Codex 中调用，会得到同一个项目键和同一个目录。
- Python 不可用时，按 [references/knowledge-base.md](references/knowledge-base.md) 的降级命令手工执行同样逻辑。

## 第二步：抽取

1. **读全量输入**。对话取关键节点（目标、冲突、失败、修正、最终结论）；文件取全文。
2. **列候选**。只按 5 类收集：决策、坑、模式、约束、有效路径。
3. **定坐标**。按 [references/ai-app-taxonomy.md](references/ai-app-taxonomy.md) 给每条经验标「阶段 / 层 / 模块」；主坐标进 frontmatter，每条经验与反例自带完整坐标。
4. **合并与丢弃**。同一根因的多个现象合并为一条；不可迁移的内容丢弃。
5. **补证据**。每条标注证据来源与置信度；无证据的降级为待验证。
6. **按模板写作**。用 [assets/experience-template.md](assets/experience-template.md)。
7. **过自检**。全部通过才落盘。
8. **写入并校验**。写入 `<experience_dir>/YYYYMMDD-<主题>.md`，运行 `scripts/validate_card.py <文件>`；FAIL 则按报错修正，PASS 后才回报路径、条数、最低置信度条目、是否触发拆分。

## 输出

- 路径：`<KB>/experience/<项目>/YYYYMMDD-<英文短横线主题>.md`（以脚本返回的 `experience_dir` 为准）
- 一次抽取产出 1 个文件；满足拆分条件时产出多个，见 [format-spec.md](references/format-spec.md)
- 文件内 `background` 与每条经验的 `背景` 必填，供知识库模块与数字分身分类

## 硬约束

- 每条经验固定 8 行：标题、坐标、触发、做法、原因、证据、置信度、背景。
- 每条经验与反例必须带完整坐标：阶段 / 层 / 模块。
- 单字段单行，任一行不得换行展开。
- 全文不超过 150 行，经验条目不超过 10 条。
- 禁止过程叙述：不写「我们讨论了」「然后」「最终发现」「经过分析」。
- 禁止复述输入。写结论，不写经过。
- 既有结论有误时不改正文：新建一张卡，用 `supersedes` 指向旧卡；旧卡只改 frontmatter 的 `status` 与 `superseded_by`。
- 坐标或标签归错时只校正 frontmatter 的 `stage` / `module` / `layer` / `tags`，正文与证据不动。
- 有文件路径、报错原文、版本号、参数值时保留原文，不做概括。

## 自检

- [ ] 每条都能回答「下次遇到什么场景、该怎么做」
- [ ] 每条都有完整坐标（阶段 / 层 / 模块）与证据
- [ ] 删掉任意一句，信息量都会下降
- [ ] 无背景铺垫，无过程还原
- [ ] 边界明确：写清什么时候不适用
- [ ] ≤ 150 行，无重复主题

## 参考

- [references/knowledge-base.md](references/knowledge-base.md)：知识库配置、两层结构、项目键、降级命令
- [references/ai-app-taxonomy.md](references/ai-app-taxonomy.md)：阶段 / 模块 / 分层三轴与归类规则
- [references/format-spec.md](references/format-spec.md)：文件结构、字段、规模上限、拆分与修订规则
- [references/extraction-rules.md](references/extraction-rules.md)：采什么、丢什么、怎么判价值与置信度
- [assets/experience-template.md](assets/experience-template.md)：可直接复制的骨架
- [scripts/validate_card.py](scripts/validate_card.py)：schema v1 校验器，落盘后必跑
