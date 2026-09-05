#!/usr/bin/env python3
"""Skill 结构健康自动体检：孤儿 references、重复标题、代码块配对。

用法:
    python3 audit_skill_health.py <skill_dir>

检查项:
    1. 孤儿 references: references/ 里有文件但 SKILL.md 正文没引用
    2. 断裂引用: SKILL.md 引了 references/xxx.md 但文件不存在
    3. 重复二级标题
    4. 代码块配对 (``` 应为偶数)
    5. frontmatter 完整性

退出码: 0 = 健康, 1 = 有问题
"""
import os
import re
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python3 audit_skill_health.py <skill_dir>")
        return 2

    skill_dir = os.path.abspath(sys.argv[1])
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md_path):
        print(f"❌ 找不到 SKILL.md: {skill_md_path}")
        return 2

    # 用二进制读避开 read_file 的 Unicode variation selector 误判
    with open(skill_md_path, "rb") as f:
        content = f.read().decode("utf-8")

    issues = []
    skill_name = os.path.basename(skill_dir)

    # 1+2. 引用完整性交叉检查
    cited = set(re.findall(r"references/([a-z0-9_-]+\.md)", content))
    refs_dir = os.path.join(skill_dir, "references")
    actual = set()
    if os.path.isdir(refs_dir):
        actual = {p for p in os.listdir(refs_dir) if p.endswith(".md")}

    orphans = sorted(actual - cited)
    missing = sorted(cited - actual)
    if orphans:
        issues.append(f"孤儿 references（有文件但正文没引用）: {orphans}")
    if missing:
        issues.append(f"断裂引用（正文引了但文件不存在）: {missing}")

    # 3. 重复二级标题
    headers = re.findall(r"^##\s+(.+)$", content, re.M)
    seen = {}
    for h in headers:
        seen[h] = seen.get(h, 0) + 1
    dups = {h: c for h, c in seen.items() if c > 1}
    if dups:
        issues.append(f"重复二级标题: {dups}")

    # 4. 代码块配对
    fences = len(re.findall(r"^```", content, re.M))
    if fences % 2 != 0:
        issues.append(f"代码块未配对: {fences} 个 ```（应为偶数）")

    # 5. frontmatter
    if not content.lstrip().startswith("---"):
        issues.append("frontmatter 缺失（不以 --- 开头）")

    if issues:
        print(f"🔴 {skill_name} 发现 {len(issues)} 个问题:")
        for i in issues:
            print(f"   - {i}")
        return 1
    else:
        print(f"✅ {skill_name} 结构健康: {len(cited)} 个引用全部存在, 无孤儿, 无重复标题, 代码块配对")
        return 0


if __name__ == "__main__":
    sys.exit(main())
