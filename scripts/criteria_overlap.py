#!/usr/bin/env python3
"""criteria_overlap.py — 8g 全量判据对账的候选提取器（skill-health-audit 执行层）

只出线索不定性：提取四类判据 token（命令/字段、数值阈值、计数点名、步骤/闸门引用），
列出出现在 2+ 文件的候选对。误报率不低（示例词/泛用词/代码块演示），定性永远是 agent 的活。
与 8g 七形态的映射：四类 token 覆盖形态 1/2/4/5；形态 3（范围/义务声明）、6（外部权威声称）与 7（能力/行为声称）
语义性强或须负例实测，本脚本不提取，人工按 8g 清单走。

用法：python3 criteria_overlap.py <skill_dir>
退出码：0 = 正常（可有/可无候选）；3 = 目录不存在等自身异常
"""
import os, re, sys
from collections import defaultdict

MAXLEN = 60
# 泛用噪音词：跨 skill 常见但不构成"同一判据"的证据
STOP = {"hermes", "config", "yaml", "json", "bash", "python", "python3", "read_file",
        "write_file", "search_files", "skill", "skills", "references", "https", "http",
        "com", "the", "and", "or", "true", "false", "none", "md", "py", "sh", "txt",
        "github", "owner", "repo", "name", "version", "description", "memory", "user"}

def tokens_of(text):
    out = set()
    # 1) 行内代码 token（含字母数字，3-40 字符，排除纯中文/纯路径展示）
    for raw in re.findall(r"`([^`\n]{3,40})`", text):
        t = raw.strip()
        if not re.search(r"[A-Za-z0-9]", t):
            continue
        # 取整串 + 命令类首词（`gh repo edit -q` → gh/ -q 噪音高，不收首词，收整串与含下划线/连字符的核心 token）
        cands = [t]
        m = re.fullmatch(r"([a-z0-9_./-]{4,}\.(?:py|md|sh|json|yaml|txt))", t)
        if m:
            cands.append(m.group(1))
        for c in cands:
            c = c.lower()
            if len(c) >= 4 and c not in STOP and " " not in c or c.startswith(("gh ", "git ", "python ")):
                out.add(c)
    # 2) 数值阈值：数字+单位/位（20,000 / 85% / 15KB / <150 字符 / v2.7.4 版本号除外）
    for m in re.finditer(r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?\s*(?:%|K\b|KB|字符|条|行|次|秒|天|轮|档|线))", text):
        out.add("NUM:" + re.sub(r"\s+", "", m.group(1)))
    # 3) 计数点名（X件套/X连搜/N项清单/X查/X步 等中文计数短语）
    for m in re.finditer(r"[一二两三四五六七八九十0-9]{1,3}[件套连条项步查轴档]", text):
        w = text[max(0, m.start()-2):m.end()+1]
        out.add("CNT:" + re.sub(r"\s", "", w)[-5:])
    # 4) 步骤/闸门/节号引用
    for m in re.finditer(r"(?:步骤|闸门|第\s*[0-9一二三四五六七八九十]+\s*步|Phase\s*\d|查\s*\d|层\s*\d)", text):
        out.add("REF:" + re.sub(r"\s", "", m.group(0)))
    return out

def main():
    if len(sys.argv) < 2 or not os.path.isdir(sys.argv[1]):
        print("用法: criteria_overlap.py <skill_dir>（目录不存在）", file=sys.stderr)
        sys.exit(3)
    d = sys.argv[1]
    files = {}
    for root, _, fs in os.walk(d):
        if os.sep + ".git" in root or "backup" in root.lower():
            continue
        for f in fs:
            if f.endswith(".md"):
                p = os.path.relpath(os.path.join(root, f), d)
                try:
                    files[p] = open(os.path.join(root, f), encoding="utf-8").read()
                except Exception:
                    pass
    if len(files) < 2:
        print("单文件对象，无跨文件对账面")
        sys.exit(0)
    loc = defaultdict(set)
    for p, t in files.items():
        for tok in tokens_of(t):
            loc[tok].add(p)
    pairs = {k: sorted(v) for k, v in loc.items() if len(v) >= 2}
    # 主文↔refs 优先展示
    def key(it):
        k, fs = it
        return (0 if any(x == "SKILL.md" for x in fs) else 1, k)
    if not pairs:
        print("✅ 无跨文件重复 token（脚本四类）——形态 3/6 仍需人工按 8g 清单走")
        return
    print(f"== 8g 候选 token（{len(pairs)} 个，出现在 2+ 文件；仅线索，误报正常，agent 逐对定性）==")
    for k, fs in sorted(pairs.items(), key=key)[:80]:
        mark = "★主文↔ref" if any(x == "SKILL.md" for x in fs) and any(x != "SKILL.md" for x in fs) else ""
        print(f"  {k}  [{', '.join(f[:MAXLEN] for f in fs)}] {mark}")
    if len(pairs) > 80:
        print(f"  …另有 {len(pairs)-80} 个未显示（提高输出上限或分文件跑）")

if __name__ == "__main__":
    main()
