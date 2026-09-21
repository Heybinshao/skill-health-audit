# 官方 linter 用法与假阳性边界（Hermes 自带 tools/skill_linter.py）
> 2026-09-20 外迁自 SKILL.md v1.4.2（原文逐字保留，未改写）。

**官方 linter（Hermes 自带，补 frontmatter 与工具名口径）**：`~/.hermes/hermes-agent/tools/skill_linter.py` 的 `lint_skill()`，覆盖本 skill 清单之外的四类——description 长度(>60)/营销词、name 格式与目录名一致、version/author/license 存在性、platforms 取值、正文误提 shell 工具名。**它收的是 SKILL.md 文件路径，不是目录**（传目录直接抛 `IsADirectoryError`——2026-09-22 venv 实测纠偏，旧表述「静默不出结果」不实）：

```python
import sys, os; sys.path.insert(0, os.path.expanduser("~/.hermes/hermes-agent"))
from tools.skill_linter import lint_skill; from pathlib import Path
for f in lint_skill(Path("<skill_dir>") / "SKILL.md"): print(f.severity, f.rule, f.message)
```

**⚠️ 规则不能盲用——它面向「发布到官方仓库的自包含 skill」**，私人工作流 skill 有大量合法例外（自建区实测）：`dangling-reference` 假阳性 100%（跨 skill 引用、教学示例占位名、正文描述产物路径片段如 `assets/index-` 全被误报）；`shell-utility-reference` 假阳性约 80%（`ps aux | grep` 进程检查、`ls -i` inode 对比、`du` 体积统计、`grep|tail` 日志管道、`cat >` 重定向绕过都是 shell 专属能力，换原生工具反而做不到——只有「指令类 + 原生工具能做到」才该改：读文件→read_file、查文件→search_files）；`missing-section`（缺官方 When to Use 段）/`missing-metadata` 属发布规范，私人 skill 可选。**分工：description-length 是硬约束必改，其余逐条人工复核后再定。**两个工具互补——自建脚本查 references 目录一致性，官方 linter 查 frontmatter 规范与正文工具名，都跑。

**合并/搬迁类改动的验收必跑本脚本**——执行者在合并时最容易引入新断裂引用（搬走引用目标、改写指向行时漏改路径），这不是可选的收尾，是合并流程的一部分。**检查类请求也一样必跑**——「评估/体检 XX skill」先跑脚本再人工分析，脚本秒级抓出孤儿/断链（2026-09-12 验收 hermes-desktop-plugin-dev 时先跑了脚本，3 个重排孤儿在静态分析前就被抓出）。
