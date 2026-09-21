#!/usr/bin/env python3
"""Skill 结构健康自动体检：孤儿 references、重复标题、代码块配对。

用法:
    python3 audit_skill_health.py <skill_dir>

检查项:
    1. 孤儿 references: references/ 里有文件但 SKILL.md 正文没引用
    2. 断裂引用: SKILL.md 引了 references/<文件名>.md 但本库任何 skill 都没有此文件（占位符用尖括号写法，免被本正则自命中；跨 skill 引用识别为 ℹ️ 非问题）
    3. 重复二级标题
    4. 代码块配对 (``` 应为偶数)
    5. frontmatter 存在性（仅查是否以 --- 开头；字段齐全性不查，人工核）

退出码: 0 = 健康, 1 = 发现问题, 2 = 用法错误（缺参数/找不到 SKILL.md）
"""
import glob
import os
import re
import sys


def skills_root_for(skill_dir: str) -> str:
    """从被测目录往上找名为 skills 的根（找不到则回退 ~/.hermes/skills）。

    用途：跨 skill 引用判定——正文引的 references 文件在本 skill 里没有，
    但在本库别的 skill 下存在，那就不是断裂，只是正主在别处。
    """
    p = os.path.abspath(skill_dir)
    while p != "/":
        if os.path.basename(p) == "skills":
            return p
        p = os.path.dirname(p)
    return os.path.expanduser("~/.hermes/skills")


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
    cited = set(re.findall(r"references/([A-Za-z0-9_.\-]+\.md)", content))
    refs_dir = os.path.join(skill_dir, "references")
    actual = set()
    if os.path.isdir(refs_dir):
        actual = {p for p in os.listdir(refs_dir) if p.endswith(".md")}

    orphans = sorted(actual - cited)
    missing = sorted(cited - actual)
    # 跨 skill 引用（正主在别的 skill 的 references/ 下）≠ 断裂——结构性假红的一大来源
    # （2026-09-22 立：此前靠人工给每处加「跨 skill 文件」措辞消红，第 4 次遇到后改为工具侧识别）
    root = skills_root_for(skill_dir)
    cross, missing_real = [], []
    for name in missing:
        hits = glob.glob(os.path.join(root, "**", "references", name),
                         recursive=True)
        if hits:
            cross.append(f"{name} → 正主 {os.path.relpath(hits[0], root)}")
        else:
            missing_real.append(name)
    if orphans:
        issues.append(f"孤儿 references（有文件但正文没引用）: {orphans}")
    if missing_real:
        issues.append(f"断裂引用（正文引了但本库任何 skill 都没有此文件）: {missing_real}")

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
        for c in cross:
            print(f"   ℹ️ 跨 skill 引用（非问题）: {c}")
        return 1
    else:
        print(f"✅ {skill_name} 结构健康: {len(cited)} 个引用全部存在, 无孤儿, 无重复标题, 代码块配对")
        for c in cross:
            print(f"   ℹ️ 跨 skill 引用（非问题）: {c}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
