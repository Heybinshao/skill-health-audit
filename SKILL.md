---
name: skill-health-audit
description: "【Skill 结构体检】开源/发布前验收你的 skill：孤儿 references、断裂引用、错位文件、残留章节、未闭合代码块、权威声称核实、兜底前向引用、文档脚本割裂、触发词漂移——十步清单 + 自动化脚本，629 本拆书 skill 实战验证。"
version: 1.0.0
author: 彬少
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skill, audit, maintenance, references]
    category: skill-maintenance
    triggers: [检查一下skill, 体检skill, 有没有开源必要, skill好不好用, 整理skill, 我的XX skill怎么样]
---

# Skill 结构体检

用户说「检查一下 XX skill / 有没有开源必要 / 会不会好用」时，**先做结构体检，再谈价值判断**。结构不健康的 skill 谈开源/交付是空中楼阁——孤儿文件、残留章节、断裂引用会让读者翻不到内容、读到坏渲染。

本 skill 管**单个 skill 内部**结构健康。跨 skill 库级清理（重叠/零使用诊断）是另一个维度的活，不在本清单内。

## 体检清单（按序执行）

### 1. 通读 SKILL.md + 全部 references

- `skill_view(name)` 拿 SKILL.md 全文 + linked_files 列表
- 逐个 `read_file` 每个 references 文件。**报 Binary 时用 python 读**：read_file 对部分正常 UTF-8 文件会误判 binary，不止 Unicode variation selectors（VS1-256）一种原因——纯中文 UTF-8 的 `.md`（无 VS、含【】等标点）也会触发（2026-08-09 实测 quote-classifier/dia-cdp-control/dia-bookmark-sync 三个 SKILL.md 被 read_file 误判 binary，但 `file` 显示纯 UTF-8、python 正常读出）。判别法：`file <path>` 若报 `UTF-8 text` 即正常，用 python 读出即可，不要被 binary 标记骗了：
  ```bash
  file <path>                                              # 看是否 UTF-8 text（而非真二进制）
  python3 -c "print(open('<path>','rb').read().decode('utf-8')[:1500])"
  ```

### 2. 引用完整性交叉检查（孤儿 reference 检测）——核心步骤

```bash
cd <skill_dir>
grep -oE "references/[a-z0-9-]+\.md" SKILL.md | sort -u   # 正文实际引用了哪些
ls references/                                             # 目录下实际有哪些
```

- **目录有、正文没引 → 孤儿**：内容写了但读者永远翻不到（skill_view 的 linked_files 是自动列目录，不代表正文引用）。处理：正文补链接，或删除，二选一，不留半吊子。
- **正文引了、目录没有 → 断裂引用**：补文件或删引用。
- 2026-08-08 实测：memory-file-maintenance 目录 9 个 references，正文只引 4 个，5 个孤儿（其中 4 个有货只是没挂链接、1 个是错位文件）。

### 3. 错位文件检测（属于别的 skill 的文件）

看到内容主题与本职不符的 reference（如记忆维护 skill 里出现 path-simulation 方法论）→ 去目标 skill 核实是否已有正主：

- 正主已有（目标 skill 的 SKILL.md 或 references 已含该内容）→ 冗余副本，删
- 正主没有 → 内容**迁回目标 skill** 再删副本（见第 6 步迁移检查）

### 4. 重复/残留章节检测

```bash
grep -n "^## " SKILL.md          # 列所有二级标题，肉眼找同名
grep -n "^## " SKILL.md | sort | uniq -d   # 或直接找重复
```

- 同名章节出现两次 → 常见于迭代中粘贴残留：一个完整版 + 一个半成品
- 残留段常带**未闭合代码块**，会破坏后续整节渲染 → 必删
- 2026-08-08 实测：memory-file-maintenance 的「反模式与陷阱」出现两次，第一次是残缺散列表 + 孤立 \`\`\`，把后面「增量补记去重」整节渲染成代码块

### 5. 代码块配对检查

```bash
grep -c '^```' SKILL.md    # 应为偶数
```

- 奇数 → 有未闭合代码块，后续整节被渲染成代码 → 定位修复

### 6. 删除前迁移检查（迁移后删，不是删了再说）

被删文件里的独有信息是否在别处？

1. 在你的知识库/参考库中全文搜索关键词（有本地搜索工具用工具，没有用 grep）
2. 查目标 skill 的 references 是否已含
3. **独有 → 先迁到正主**（参考库对应文件，或目标 skill 的 references），**再删副本**
4. 不迁直接删 = 信息永久丢失
- 2026-08-08 实测：binshao-vault-conventions.md 里「Z｜附件按文章名建子文件夹」规则参考库没有，先补进 vault-architecture 的 vault-structure-conventions.md，再删记忆维护里的副本。

### 7. 权威声称核实（references 引用的外部权威是否真实存在）

references 里出现「X 文件第 N 行规定 Y」「config 定了 Z」这类**指向外部权威的声称**时，逐条 grep/read 验证，不能信声称：

- 声称的权威文件是否存在、那一行是否真是那个内容
- 2026-08-08 实测：usability-self-test.md 声称「MEMORY.md 硬上限 10k（SOUL.md 第22行定的规矩）」——实测 SOUL.md 第22行是「删除文件前必须问」，根本没有 10k 规定；真权威是 `config.yaml` 的 `memory_char_limit: 10000`。SKILL.md 第293行同款错误说法也中招。
- **为什么实战暴露不了**：主干流程只走「通读→决策→执行」，永远不会去核对 references 声称的权威——只有专门走跨文件路径才抓得到。

### 8. 兜底前向引用检查（异常解法与触发点距离）

skill 内部已知某步可能出错、解法写在文件尾部异常表时，检查**入口处有没有前向提示**：

- 触发点（如第一步 read_file 读三文件）与兜底（如异常表「三文件 read_file 报 Binary」）距离过远 → agent 走到触发点不知道有兜底，可能卡住
- 修法：在触发点加一行「若报 X，见下方异常处理表第 N 行兜底」
- 2026-08-08 实测：memory-file-maintenance 第一步大概率触发 Binary 误判（MEMORY.md 22601 字节含 VS 序列），兜底解法只在 299 行异常表，第一步（68 行）无提示

### 8b. 文档与脚本一致性检查（doc/script 割裂）

skill 带 `scripts/` 时，SKILL.md 描述的工作流必须和脚本实际能力对得上——两者割裂是常见但体检清单上最容易漏的一项（2026-08-09 实测 dia-bookmark-sync：SKILL.md 通篇「直接操作浏览器本地 JSON 文件、改完重启生效」，但目录下 3 个脚本全是 HTML 解析器——正则匹配 `<DT><A HREF=`，usage 是 `bookmarks-合并-YYYY-MM-DD.html`，SKILL.md 自己兜底承认「当前版本基于 HTML 格式」）。读者照文档走 JSON 工作流，脚本却吃不了，等于断头。

检查法：
```bash
ls <skill_dir>/scripts/                       # 有哪些脚本
head -25 <skill_dir>/scripts/*.py             # 看真实输入输出格式（HTML? JSON?）
grep -nE "用法|usage|\.html|\.json|HREF=|Bookmarks" <skill_dir>/SKILL.md
```
- 文档说 JSON、脚本吃 HTML（或反之）→ 割裂。两种修法二选一：脚本改读文档格式，或文档改回脚本真能吃格式。不准留「注：当前版本基于 X 格式」的兜底 — 那是把缺陷写进文档。
- 同时看脚本的 agents/openai.yaml、references/ 是否也被 SKILL.md 引用（回到第 2 步交叉检查）。
- 延伸坑（脚本相对路径、config.json 死配置）见 `references/doc-script-split-pitfalls.md`——config.json 装饰性字段是 8b 的同族坑。

### 8c. 触发词一致性检查（frontmatter triggers vs 正文触发词）

frontmatter `metadata.hermes.triggers` 是系统级触发匹配，正文里的触发词是 agent 读到的——**两处必须同步**，漂移会导致系统匹配不到、或匹配到却走错模式。检查法：

```bash
grep -n "triggers:" <skill_dir>/SKILL.md          # frontmatter 里的触发词
grep -nE "「.*?」|用户说|触发" <skill_dir>/SKILL.md   # 正文里的触发词
```

- 正文写了、frontmatter 没有 → 系统级匹配漏（2026-08-10 实测：memory-file-maintenance v5.2 正文重度模式有「记忆大扫除」，frontmatter triggers 只有「大扫除」——用户说「记忆大扫除」时系统可能匹配不到）。
- 双模式/多入口 skill 尤其要查：每个模式的触发词是否都进了 frontmatter。
- 修法：frontmatter triggers 列表补全，与正文触发词一一对应。

### 8d. 架构改造后旧口径对账（版本升级/双模式改造后必做）

skill 做架构级改造（如 v5.x 引入双模式、改名、换方法论）后，**旧口径会残留在改造时漏掉的位置**——这是 8c 之外最常见的新坑，且路径模拟不一定抓得到（主干路径走通了，残留句只在旧表述里）。2026-08-10 实测 memory-file-maintenance v5.0→v5.2 双模式改造暴露三类：

```bash
grep -nE "旧模式名|旧关键词" <skill_dir>/SKILL.md <skill_dir>/references/*.md   # 列出改造前的旧词全量对账
```

1. **旧表述残留**：触发段落还写「必须走完整审计」（与新增的轻量模式矛盾）——把「完整审计」降级为仅重度模式用词，轻量触发句改「走审计流程（默认轻量）」
2. **标注漏改**：多个同类元素（如 3 处 CHECKPOINT）只改了前两处「重度保留，轻量并入方案」，第三处还是旧格式——**同类元素逐个 grep 标题确认全部标注一致**，不能「记得改了两处就收工」
3. **实现与说明脱节**：query 统一加了 `sort="newest"`，旁边说明文字还写「limit 是 FTS 相关性 topN」——实现改了、解释没同步，读者/执行者按旧说明理解

**对账方法**：改造完成后，列出「旧概念关键词」（旧模式名、被废弃的限定词如「全量/已降级/必须通读」、旧参数语义），全目录 grep 逐条确认已消除或已改写；再对「重复出现的同款元素」（CHECKPOINT、警告行、示例 query）逐个核对是否都带新标注。此步在路径模拟之前做，可减少路径模拟的噪音。

### 8e. SKILL.md 体量分层检查（臃肿 ≠ 结构病）

体量超阈值（SKILL.md > ~15KB 或行数同类最大）但结构健康（0 孤儿/0 重复/配对完好）时，病灶通常是**「每次触发全文加载」**而非乱堆——判断口径：臃肿的真实代价是每次烧 token，不是看着乱。

1. **先统计各节行数占比**：主流程 vs 附则群（纪律/陷阱/异常表）。附则占比 >40% = 典型可外迁形态
2. **附则外迁 recipe**（2026-08-28 实测 memory-file-maintenance：444 行/43KB → 365 行/14KB，-67%）：同主题附则合并成 1-2 个 references（如 writing-disciplines.md + pitfalls.md）；SKILL.md 原位置留「⚠️ 必读指向行」（写明触发场景：何时必须去读）；外迁后 8e 自身的坑——**指向行替换原文时会连带删掉附近对旧 references 的引用语句，产生新孤儿**，改完必须重跑第 2 步孤儿检测
3. **主流程不因瘦身砍内容**：七步/决策树等主干骨架原地保留；瘦的是「规则细则」不是「流程步骤」
4. **双表漂移检查**：SKILL.md 里维护的副本表（频率表/映射门表）要与权威源逐行核对——权威源加了行、副本没跟是高频漂移点（2026-08-28 实测：README 频率表加了 2 行，skill 副本漏 1 行；另 frontmatter 无 triggers 字段=系统级触发缺失，同轮补齐）

### 8f. 第三方仓库：体检对象是 canonical SKILL.md

目标是 GitHub 仓库而不是本地 `skill_dir` 时，**仓库文件数 / star 不是结构指标**。病毒 skill 常见形态：一份 <10KB 的 `skills/<name>/SKILL.md` + 十几个运行时适配器（`.claude-plugin/`、`INSTALL.md`、hooks）。适配层是分发工程，不进本 skill 的孤儿/臃肿口径。

1. 先定位 canonical 路径（仓库 AGENTS.md / README 会写 source of truth）
2. 只对那份 SKILL.md（及它声明的 references/）跑第 2–5 步
3. 仓库根的 marketplace 清单、多语言 README、always-on hook **不当作 skill 膨胀**

### 9. 修复后验证（必须，不验证不汇报）

- 重新 grep 引用 vs 文件：全部引用存在、无孤儿
- 代码块配对为偶数
- 重复标题只剩一个
- frontmatter 无损（read 前 12 行确认 name/description/version 完好）
- 通读目标段确认无中间状态残留

## 陷阱

| 陷阱 | 为什么是问题 | 正确做法 |
|------|------------|---------|
| patch 报 no_change 就以为删了 | fuzzy match 可能误判"目标已存在"，实际残留段还在 | 改后必须 python/read_file **重读目标段确认**，不信 no_change（2026-08-08 实测第一次 patch 就误报，重读发现残留段原封不动，换精确 old_string 才删掉） |
| 删错位文件前不查独有信息 | 文件里可能有别处没有的规则 | 删前在你的知识库/参考库全文搜索 + 查目标 skill，独有内容先归位再删 |
| 只修 SKILL.md 不修 references | 孤儿文件继续躺着，读者翻不到 | 补链接或删除二选一，别留半吊子 |
| 残留段带未闭合 \`\`\` 以为无害 | 后续整节渲染成代码块，阅读直接坏 | 代码块配对检查必做 |
| read_file 读含 VS 的文件报 Binary 就放弃 | Unicode variation selectors 误判，文件本身正常 | python3 读，grep 不受影响可辅助验证 |
| 信 references 里的「X 文件第 N 行规定 Y」 | 声称的权威可能不存在或行号不对（实测 SOUL.md 第22行是「删除文件前必须问」，却被声称是 10k 上限） | 逐条 grep 验证声称；真权威常是 config.yaml 而非 SOUL.md |
| 兜底写在文件尾部、入口无前向提示 | agent 走到触发点不知道有解法，可能卡住 | 触发点加「若报 X，见异常表第 N 行」；检查入口与兜底距离 |
| 文档说 JSON 工作流、脚本只吃 HTML（或反之） | doc/script 割裂，读者照文档走脚本报错 | 脚本改读文档格式，或文档改回脚本真能吃格式；不准留「注：当前版本基于 X 格式」兜底把缺陷写进文档（2026-08-09 实测 dia-bookmark-sync） |
| read_file 报 Binary 就当真二进制放弃 | 纯中文 UTF-8 也会误判，文件本身正常 | 先 `file <path>` 看是否 UTF-8 text，是则用 python3 读出，grep 不受影响可辅助 |
| 架构改造后只验主干路径，不查旧口径残留 | 旧表述/旧标注/旧说明文字残留在漏改位置（双模式改造实测 3 类：触发句还写「走完整审计」、3 处 CHECKPOINT 只标 2 处、query 加了 sort 但说明还写旧语义），路径模拟走主干抓不到 | 改造后先做 8d 旧口径对账：列旧关键词全目录 grep + 同款元素逐个核对标注，再跑路径模拟 |
| 评估"会不会好用"只看结构 | 结构健康 ≠ 体验好 | 对用户本人极好用 ≠ 对外人好用：还要查私有依赖（MCP/用户名/硬编码路径）、私有上下文（"本会话实测"时间戳）、单一用户假设 |
| 外迁附则时顺手删掉了附近旧引用语句 | 替换节为指向行的操作会波及周围文本，产生新孤儿（2026-08-28 实测：memory-file-maintenance 瘦身后 5 个 references 断链） | 外迁后必重跑第 2 步孤儿检测；新指向行的措辞要覆盖原引用的信息量（指向行丢失「见异常表第 N 行」这类细节=兜底前向引用退化） |
|指向行声称「见 X 文件的 Y 条目」但 X 里没有 Y | 外迁/重组时指向行凭记忆写，目标文件实际条目名对不上（2026-08-28 实测：④写「日期过时→date」，pitfalls.md 无此条，真身在 common-pitfalls.md） | 写指向行前先 grep 目标文件确认条目存在；跨文件指向优先指向条目真身而非就近文件 |
| 把仓库体量或 star 当 skill 复杂度 | 分发适配器会让仓库看起来很重，canonical 文件可能只有一百行 | 体检只打 canonical SKILL.md（见 8f）；star 是分发信号，不是结构分数 |

## 体检后：要不要跑路径模拟？（2026-08-08 定稿）

**结论：只要被测 skill 是「用户会走一串步骤」的流程类 skill，就值得跑一次 path-simulation——高频实战不是豁免理由。**

曾误判：「memory-file-maintenance 是你最高频实战的 skill，每次你说整理记忆就是真实走一遍，实战即模拟，不需要专门路径模拟。」用户坚持跑了一遍，**立刻抓到 2 条实战暴露不了的问题**（虚假权威引用、兜底无前向引用）——都是「跨文件路径 #7」才看得到的：

- 实战走主干：通读→决策→执行，永远不会去核对 references 声称的权威是否真实存在
- 路径模拟走跨文件路径：专门 grep 所有「X 文件第 N 行规定 Y」声称 → 发现 SOUL.md 引用是假的

**正确的判断框架**：
- 高频实战 skill：主干路径早已被真实执行验证过，**但跨文件一致性从未被验证** → 至少跑一次跨文件路径 #7（专核 references 之间、references 与外部权威之间的矛盾）
- 低频/未发布 skill：跑标准 + 风险路径全套
- 纯知识类（无步骤）：不跑，静态检查够

与 `path-simulation` skill 的衔接：体检第 7 步（权威声称核实）就是跨文件路径 #7 的具体化，跑路径模拟时直接复用本 skill 的清单。

## 验证脚本

`scripts/audit_skill_health.py` —— 自动执行第 2/4/5 步（孤儿引用、重复标题、代码块配对），传入 skill 目录即出报告。手动体检后跑一遍兜底。新增第 7/8 步（权威声称、兜底前向引用）需人工判断，脚本不覆盖。
