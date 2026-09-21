---
name: skill-health-audit
description: "【Skill 结构体检】体检skill、检查一下skill。孤儿/断链/开源前"
version: 1.5.3
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skill, audit, maintenance, references]
    category: skill-maintenance
---

# Skill 结构体检

用户说「检查一下 XX skill / 有没有开源必要 / 会不会好用」时，**先做结构体检，再谈价值判断**。结构不健康的 skill 谈开源/交付是空中楼阁——孤儿文件、残留章节、断裂引用会让读者翻不到内容、读到坏渲染。

本 skill 管**单个 skill 内部**结构健康。跨 skill 库级清理（重叠/零使用诊断）是 skill-library-audit 的职责，不在本清单内。

## 体检清单（按序执行）

### 1. 通读 SKILL.md + 全部 references + scripts

- **无效目标兜底**：指定的 skill 目录/frontmatter `name` 不存在或读不了 → 提示使用者重选有效 `skill_dir`（先 `search_files` 全库核 name），不开始体检——「缺 X」类断言前尤其必核，别把「没找到目标」报成「目标缺项」

- **评价/体检/验收类结论必须全目录通读后落笔**：只读 SKILL.md 正文的结论会被 deep 文件推翻——旧口径与跨文件矛盾（references 教用主流程明令禁的口径、脚本硬编码主流程声称「由 config 定」的值）只在全文件逐字对读时暴露；脚本要读主体逻辑，不能只列文件名和体量。确实只审部分范围时，结论里显式标注未读范围。
- `skill_view(name)` 拿 SKILL.md 全文 + linked_files 列表
- 逐个 `read_file` 每个 references 文件。**报 Binary 时用 python 读**：read_file 对部分正常 UTF-8 文件会误判 binary，不止 Unicode variation selectors（VS1-256）一种原因——纯中文 UTF-8 的 `.md`（无 VS、含【】等标点）也会触发（2026-08-09 实测 quote-classifier/dia-cdp-control/dia-bookmark-sync 三个 SKILL.md 被 read_file 误判 binary，但 `file` 显示纯 UTF-8、python 正常读出）。判别法：`file <path>` 若报 `UTF-8 text` 即正常，用 python 读出即可，不要被 binary 标记骗了：
  ```bash
  file <path>                                              # 看是否 UTF-8 text（而非真二进制）
  python3 -c "print(open('<path>','rb').read().decode('utf-8')[:1500])"
  ```

### 2. 引用完整性交叉检查（孤儿 reference 检测）——核心步骤

```bash
cd <skill_dir>
grep -oE "references/[a-z0-9_-]+\.md" SKILL.md | sort -u   # 正文实际引用了哪些（含下划线命名，与 audit 脚本口径一致）
ls references/                                             # 目录下实际有哪些
```

- **目录有、正文没引 → 孤儿**：内容写了但读者永远翻不到（skill_view 的 linked_files 是自动列目录，不代表正文引用）。处理：正文补链接，或删除，二选一，不留半吊子。
- **skill_view 的 linked_files 不算正文引用**——它是目录自动列举，只证明文件在，不证明正文挂了链接。孤儿判定以「grep SKILL.md 正文是否引用」为准（2026-09-12 实测：瘦身重排后 skill_view 显示 9 个 linked_files，脚本仍报 3 孤儿——文件都在，是重排丢了正文链接句）。
- **脚本的「N 个引用」≠附属文件总数，引用扫描口径仅覆盖 markdown 链接语法**：正文行内反引号式引用（`scripts/batch_vision.py` 这类）不计入，会同时少报引用数、漏检 scripts/ 目录孤儿。核对法：`find <skill_dir> -type f` 列全部附属文件，逐个 grep 正文提及次数，0 次才是真孤儿——引用数与文件数的差额本身就是待人工定性清单。
- **正文引了、目录没有 → 断裂引用**：补文件或删引用。
- **断裂报告先三分类定性再动手**（2026-09-06 全量验收 19 处断链实测：真断裂仅 3）：①示例代码块里的路径（教格式的举例）→ 不修；②举例性提及（教学句里写「坑表可写成独立 common-pitfalls.md 文件」这类，不带路径前缀也不算引用）→ 不修；③跨 skill 文件引用（正主在别的 skill 里且文件存在）→ 改为带「跨 skill 文件不属本目录」措辞消歧。只有「指向本目录 references/ 但文件不存在」才是真断裂。脚本正则无法区分，人工复核必做。
- **核对口径补充**（原 skill-library-audit「单 Skill 内部健康审计」第 7 步，2026-09-20 归位）：②类跨 skill 引用要**去归属 skill 的 `references/` 核对**——按本目录报断链是**扫描器口径错误**；③类（教学/历史语境、示例占位名）不核对，非活指针。
- 2026-08-08 实测：memory-file-maintenance 目录 9 个 references，正文只引 4 个，5 个孤儿（其中 4 个有货只是没挂链接、1 个是错位文件）。

### 2b. 同名副本遮蔽检测（CLI 按 name 去重的盲区，2026-09-06 实测）

**机制**：Hermes 按 frontmatter `name` 去重加载 skill——同一个 name 存在两份时（如官方位 `note-taking/obsidian` + 自建位 `binshao/agent/hermes/obsidian`），CLI 列表只显示一份，**另一份永远不被加载**：它的 description 不进系统提示、内容从不生效，纯占磁盘。这解释了「为什么自建的增强版从未起作用」。

检测法（审计时对可疑 skill 跑一遍）：

```bash
# name 重复 = 有遮蔽（⚠️ 用 --include 递归：三层深的 binshao/agent/<主题>/<skill>/ 会被两层 glob 漏报）
# ⚠️ 会带进两类噪音：SKILL.md.bak-* 备份文件（glob 前缀匹配）、正文里 name: 开头的示例行（design-md 等有）——
#    命中后先人工核对是否真为两份同 name 的 skill 目录再定性，勿拿计数直接当结论
grep -rh "^name:" ~/.hermes/skills --include=SKILL.md 2>/dev/null | sort | uniq -d
```

**处置（留增强、去遮蔽）**：diff 两份定谁含增强内容 → 增强版迁入「被 CLI 实际加载的那份」的位置 → 删被遮蔽副本。若加载位是官方 bundled（修改自动进 `list-modified` 受保护，`hermes skills reset --restore` 可随时回官方版）；若增强版是 user-owned 原作，反方向迁回自建位。迁移完成后**合并官方 frontmatter 字段（version/license/原作者 author）与增强正文**：author 保留原作者署名只追加适配者，版本号 bump（如 1.0.0 → 1.1.0）标记非官方原版——丢弃官方字段会丢失版本管理线索。

**注意**：curator 使用统计的 key 也按 name 记账——被遮蔽副本的使用数据会记到生效那份头上，判断「谁在用」时勿被误导。

### 2c. 散文指路语失效检测（外迁/重组/合并后必做）

**症状**：内容外迁到 references 后，正文里**用自然语言指路**的句子断头——「见第 X 节」「见批量处理第 N 条」「C 线工作流第 N 项」「见 Step 5 去重判据」「section above」。这类句子不是 markdown 路径引用，第 2 步的 `references/xxx.md` grep 与孤儿/断链脚本**都扫不到**（脚本口径只覆盖链接语法与裸路径）。

```bash
grep -nE "见第|见 *Step|第 *[0-9]+ *(条|项|步|点)|上文|上节|前文|先见|section above|见下方|见前" <skill_dir>/SKILL.md
```

逐条核对指路目标还在不在本文件：
- 目标是**本文件内的节/步骤** → 查该节是否仍存在（外迁常常把它一起带走）
- 目标**已外迁** → 改成带文件链接的显式引用（`[名称](references/<file>.md)`）或删句
- **首次出现处**必须补显式链接，其后重复处可保留简短措辞

**为什么必查**：外迁时正文保留「流程骨架」，最自然的写法就是「详见第 N 条」——而那条恰恰被搬走了，执行者顺指路语翻不到内容，等于断头。实测（10 个 skill 批量瘦身）：路径引用层全绿、脚本零报错，系统性扫指路语才抓出 4 处悬空，且是用户追问「确定都没什么问题么」才动手查的——**外迁后主动扫，别等追问**。

### 3. 错位文件检测（属于别的 skill 的文件）

看到内容主题与本职不符的 reference（如记忆维护 skill 里出现 path-simulation 方法论）→ 去目标 skill 核实是否已有正主：

- 正主已有（目标 skill 的 SKILL.md 或 references 已含该内容）→ 冗余副本，删
- 正主没有 → 内容**迁回目标 skill** 再删副本（见第 6 步迁移检查）

- 2026-08-08 实测案例：`path-simulation-methodology.md` 混进 memory-file-maintenance 的 references（内容属别的 skill），核实正主后删副本
### 4. 重复/残留章节检测

```bash
grep -n "^## " SKILL.md          # 列所有二级标题，肉眼找同名
grep "^## " SKILL.md | sort | uniq -d   # 或直接找重复（⚠️ 不能带 -n：行号前缀使每行唯一，uniq -d 恒零输出）
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
- **反向同样成立：自己下判据前先核源，别凭印象定标尺**。设阈值/上限类判据（字符上限、体积线、超时数）或做「某类全都缺 X」的断言前，先 grep 源码/权威文件拿实值，再按权威口径分区统计。实测两连翻车：① 按印象把 description 上限当 120 字符（源码 `SKILL_PROMPT_DESC_LIMIT = 60`，宽了一倍，超长项漏修一半，超限的触发词继续被截断）；② 凭错误分区断言「41 个 skill 缺 version」（按归属分区后自建区 100% 有，真缺失量为零，差一步去改官方区）。**印象值和错分区都会让整批操作打偏，而它们在报告里看起来同样言之凿凿——先拿命令输出再开口。**

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
- 延伸坑见 `references/doc-script-split-pitfalls.md`——含 8b 延伸（脚本相对路径、config.json 死配置）与 **8d 延伸：方案/plan 类文档的权威声称检查手法**（体检对象是 plan 时必读，该文件为延伸节的权威存放处）。

### 8c. 触发词覆盖检查（description 是唯一的系统级触发面）

**机制（源码口径，勿再凭直觉改回）**：系统提示的 skill 索引只注入 frontmatter 的 `description`（`agent/prompt_builder.py` → `extract_skill_description`）；加载器读取的条件字段只有 toolset/platform 门控（`_CONDITION_KEYS`），**任何位置的 `triggers` 字段（顶层 `triggers:` 和 `metadata.hermes.triggers`）都不被读取，是死配置**。description 不含的触发词 = 该场景永远匹配不到。

**⚠️ description 还有长度截断（8c 的关键限定，勿漏）**：`SKILL_PROMPT_DESC_LIMIT = 60`（`agent/skill_utils.py`），索引只渲染 `description[:57] + "..."`——**超 60 字符的部分每轮对话都读不到**，触发词写在后半段 = 等于没写。所以触发词必须落在**前 57 字符内**（写法规范：职责一句话 + 最高频 3-4 词，见 skill-creation-rules 第三步）。**压缩到 ≤60 时，用户真实会说的入口词必须留在前 57 字**——用「流程与清单」顶掉「上传」这类原话 = 覆盖失败；`description-length` linter 绿 ≠ 触发覆盖过。低频问句不必硬塞 60 字，主路径词丢了就是病。截完用用户原话走一遍触发覆盖，不能拿上轮「结构 0 问题」当基线。

检查法：

```bash
python3 -c "import yaml,sys;s=open(sys.argv[1],encoding='utf-8').read();d=yaml.safe_load(s[3:s.find(chr(10)+'---',3)]);print(len(d['description']),d['description'])" <skill_dir>/SKILL.md
# >60 = 后半段触发词不进系统提示，按上表重写
```


```bash
grep -n "triggers:" <skill_dir>/SKILL.md           # 发现死 triggers 字段（不要往里补词）
grep -nE "「.*?」|用户说|触发" <skill_dir>/SKILL.md   # 正文里的触发场景词
```

- 正文写了触发场景、description 没覆盖 → 把词补进 **description**（模型只看得到它）。
- 发现 `triggers:` 字段 → 把里面的词并入 description 后**删掉字段**——留着会误导后续维护者以为它在生效。
- 双模式/多入口 skill 尤其要查：每个模式的入口词都要在 description 里。
- **合并来源 skill 时，源的专属触发词要并入 target 的 description**（如「发布到GitHub/公开仓库」「大规模蒸馏」这类词）——漏并 = 合并后源场景触发不到任何 skill。

### 8d. 架构改造后旧口径对账（版本升级/双模式改造后必做）

skill 做架构级改造（如 v5.x 引入双模式、改名、换方法论）后，**旧口径会残留在改造时漏掉的位置**——这是 8c 之外最常见的新坑，且路径模拟不一定抓得到（主干路径走通了，残留句只在旧表述里）。2026-08-10 实测 memory-file-maintenance v5.0→v5.2 双模式改造暴露三类：

```bash
grep -nE "旧模式名|旧关键词" <skill_dir>/SKILL.md <skill_dir>/references/*.md   # 列出改造前的旧词全量对账
# 对账范围含库内消费方：被编排/被引用的清单，改动后 grep 全库找引用它的 skill 一并核（见坑表「姊妹 skill 动词/硬数字越界」）
grep -rln "<本 skill name>" ~/.hermes/skills --include=SKILL.md
```

1. **旧表述残留**：触发段落还写「必须走完整审计」（与新增的轻量模式矛盾）——把「完整审计」降级为仅重度模式用词，轻量触发句改「走审计流程（默认轻量）」
2. **标注漏改**：多个同类元素（如 3 处 CHECKPOINT）只改了前两处「重度保留，轻量并入方案」，第三处还是旧格式——**同类元素逐个 grep 标题确认全部标注一致**，不能「记得改了两处就收工」
3. **实现与说明脱节**：query 统一加了 `sort="newest"`，旁边说明文字还写「limit 是 FTS 相关性 topN」——实现改了、解释没同步，读者/执行者按旧说明理解

**对账方法**：改造完成后，列出「旧概念关键词」（旧模式名、被废弃的限定词如「全量/已降级/必须通读」、旧参数语义），全目录 grep 逐条确认已消除或已改写；再对「重复出现的同款元素」（CHECKPOINT、警告行、示例 query）逐个核对是否都带新标注。此步在路径模拟之前做，可减少路径模拟的噪音。

### 8e. SKILL.md 体量分层检查（臃肿 ≠ 结构病）

体量超阈值（SKILL.md > ~15KB 或行数同类最大）但结构健康（0 孤儿/0 重复/配对完好）时，病灶通常是**「每次触发全文加载」**而非乱堆——判断口径：臃肿的真实代价是每次烧 token，不是看着乱。

1. **先统计各节行数占比**：主流程 vs 附则群（纪律/陷阱/异常表）。附则占比 >40% = 典型可外迁形态
2. **附则外迁 recipe**（2026-08-28 实测 memory-file-maintenance：444 行/43KB → 365 行/14KB，-67%）：同主题附则合并成 1-2 个 references（如 writing-disciplines.md + pitfalls.md）；SKILL.md 原位置留「⚠️ 必读指向行」（写明触发场景：何时必须去读）；外迁后 8e 自身的坑——**指向行替换原文时会连带删掉附近对旧 references 的引用语句，产生新孤儿**，改完必须重跑第 2 步孤儿检测
3. **主流程不因瘦身砍内容**：七步/决策树等主干骨架原地保留；瘦的是「规则细则」不是「流程步骤」。**外迁后禁止把主文件改成「动手前先读 references 全文」**——那把按需加载变成每次强制二次加载，弱模型会把细则当闸门；指向行只写触发场景（何时读哪一段），不写先读完再动手
4. **双表漂移检查**：SKILL.md 里维护的副本表（频率表/映射门表）要与权威源逐行核对——权威源加了行、副本没跟是高频漂移点（实测：README 频率表加 2 行，skill 副本漏 1 行）

### 8f. 第三方仓库：体检对象是 canonical SKILL.md

目标是 GitHub 仓库而不是本地 `skill_dir` 时，**仓库文件数 / star 不是结构指标**。病毒 skill 常见形态：一份 <10KB 的 `skills/<name>/SKILL.md` + 十几个运行时适配器（`.claude-plugin/`、`INSTALL.md`、hooks）。适配层是分发工程，不进本 skill 的孤儿/臃肿口径。

1. 先定位 canonical 路径（仓库 AGENTS.md / README 会写 source of truth）
2. 只对那份 SKILL.md（及它声明的 references/）跑第 2–5 步
3. 仓库根的 marketplace 清单、多语言 README、always-on hook **不当作 skill 膨胀**

### 8g. 全量判据对账（不依赖本轮变更范围，抓跨文件语义打架）

**与 8d 的分工**：8d 的旧口径对账 grep 的是**本轮变更关键词**——历史轮次改造留下的旧口径不在本轮变更集里，关键词 grep 天然扫不到。8g 补的正是这个盲区：全目录、全量、按判据配对。2026-09-16 实证（memory-file-maintenance）：四轮验收（增量轮）全绿，同日全量深读抓出 3 处「SKILL.md 禁用 X 口径、某 references 教用 X 口径」打架（file_size/wc -c 计算口径、USER.md Binary 误判范围、P0/P2 旧分级）——全是历次修复漏改的存量，躺在 deep 文件里。

**方法（半机械：脚本出候选，人做定性）：**

先跑 `python3 <本skill目录>/scripts/criteria_overlap.py <skill_dir>`——自动提取**跨文件重复 token**（行内代码 token、数值阈值、计数点名、步骤/闸门号引用四类）并列出出现在 2+ 文件的候选对；脚本只出线索，误报率不低（示例词、泛用词），定性永远是人。对照实测（2026-09-16）：对人工判定无打架的 path-simulation 出 6 候选全假阳性（`NUM:3条`、`REF:步骤` 类同源泛词），对 mfm 出 41 候选含真打架线索——**候选信噪比低是设计内**：FP 是看一眼即判一致的无害候选，本步真正要防的是漏报，勿因 FP 弃用或收紧规则。无脚本环境（第三方安装缺 scripts/）按下列六形态手工枚举——**六形态各来自 2026-09-16 四轮验收实战，每形态至少抓到一处真打架**：

1. **命令/CLI 参数与字段名**（如 `file_size`、`wc -c`、`--write-baseline`）——A 文件禁用、B 文件教学
2. **数值与阈值**（容量线、百分比、字符上限、超时数）——两处数值不等或口径（字节/字符）不同
3. **范围/义务声明**（必做/禁用/正常/可跳过/豁免/默认）——同一动作一边必走一边可跳
4. **计数点名与枚举**（「X 项/X 件套/X 连搜」+ 点名清单）——宣称数 ≠ 实列数、同名不同列
5. **跨文件节点/步骤号引用**（「步骤 X」「闸门 N」「第 N 条」）——被引侧重排/改名后失配
6. **外部权威声称**（「X 文件第 N 行」「源码 :1434」「config 定了 Z」）——行号漂移、行为改版（与第 7 步权威声称核实共用手法，7 步查单点真伪、本查查多处一致）

只在单文件出现一次的判据不进对账（无打架对象）。同名判据逐对**双向**比对方向与数值：A 处说允许、B 处说禁止 = 必有一错或缺边界裁决；同时核对数值/范围是否一致。**必含 SKILL.md 主流程 ↔ references 双向**——执行者先读正文再跳参考文件，两边打架最致命（参考文件的旧口径会被当成正文细则的例外执行）。

**定性**：冲突项出「谁对谁错」结论（以实测记录/最新版本为准，参照 8d 的新旧判型），合法历史残留（版本演进注记、案例叙述）标注豁免理由。

**触发档位**：全量验收（scope=全量）、大版本/架构改造后、或修复引入「新口径替代旧口径」时必做（双版本并存迹象 = 触发信号）；**含多参考文件时增量轮亦必走**（对象可缩为「本轮新口径 vs 全目录存量判据」配对，成本可控）；确要跳过（仅限单参考文件以下的对象），须在报告「覆盖」行显式标注「8g 未跑」。**本节为 scope 判据唯一权威；skill-acceptance Phase 0 条 3 在其上加编排侧从严信号，不另立判据**。

**收工判据**：每条判据对有结论（一致 / 冲突已修 / 合法残留已标注）。

> 与 path-simulation 的分工：其跨文件路径 #7 是本步的走查版（执行定义已回指本方法）；只装本 skill 时 8g 独立可跑，无前置依赖。

### 9. 修复后验证（必须，不验证不汇报）

- 重新 grep 引用 vs 文件：全部引用存在、无孤儿
- 代码块配对为偶数
- 重复标题只剩一个
- frontmatter 无损（read 前 12 行确认 name/description/version 完好）
- 通读目标段确认无中间状态残留

## 陷阱

> 实测坑表（patch 报 no_change / 删错位文件 / 未闭合代码块 / 假权威声称 / doc-script 割裂 / 8d 关键词盲区 / 外迁后旧引用残留等，勿在本句写死条数——8g 形态 4「宣称数≠实列数」自踩案 2026-09-22 实证）+ **体检后要不要跑路径模拟的判断框架** → [references/common-pitfalls.md](references/common-pitfalls.md)

## 验证脚本

`<你的 skill 安装目录>/scripts/audit_skill_health.py` —— 自动执行第 2 步（孤儿+断裂引用）、第 4 步（重复标题）、第 5 步（代码块配对）三项机械检查，另含 frontmatter 完整性检测（对应第 9 步验证首项），传入 skill 目录即出报告。手动体检后跑一遍兜底。第 7/8 步（权威声称、兜底前向引用）需纯人工判断，脚本不覆盖；第 8g 步有候选提取器 `scripts/criteria_overlap.py`（四类 token 自动配对待账清单，见 8g 节），候选仍须人工定性。

> **官方 linter**（`tools/skill_linter.py` 的 `lint_skill()`，补 frontmatter 与工具名口径）用法 + **规则假阳性边界**（`dangling-reference` 假阳性 100%、`shell-utility-reference` ~80%，私人 skill 有大量合法例外）→ [references/official-linter.md](references/official-linter.md)
