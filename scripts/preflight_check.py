#!/usr/bin/env python3
"""preflight_check.py — 验收/体检前的机械项一次跑完（skill-health-audit 执行层）

动机（2026-09-22）：验收慢的主因是「机械项分散成十几条命令」——每条都是一次往返 + 一份输出
回灌上下文。本脚本把可机械化的项合成一次调用，输出紧凑证据块。**只出证据不定性**：
孤儿/断裂里的占位名、2c 候选里的条内枚举，仍然要 agent 读原文定性。

覆盖项：
  [元信息] name/version/description（长度 + 前 57 字预览）、死 `triggers:` 字段、
           python len 字符数（权威口径）、references 字符总量（估读量）
  [引用]   正文已引用 vs references/ 实存（孤儿 / 断裂）；占位名不计
  [2b]     同名副本遮蔽（扫 skills 全库同名 SKILL.md，防 loading 遮蔽）
  [2c]     散文指路语候选（含编号索引型 ①②③、「对应条目：」），扫 SKILL.md + references/*.md
  [下一步] criteria_overlap.py（8g 形态 1/2/4/5 候选）+ 三形态 lure 正则（形态 3/6/7）

用法: python3 preflight_check.py <skill_dir> [--json] [--skills-root PATH] [--max-hits N]
退出码: 0 = 无机械问题; 1 = 有机械问题（孤儿/断裂/同名副本）; 2 = 用法错误
"""
import argparse
import glob
import json
import os
import re
import sys

PLACEHOLDER = {"xxx.md", "yyy.md", "zzz.md", "example.md", "foo.md", "bar.md",
               "test.md", "sample.md", "文件.md"}
CITED_RE = re.compile(r"references/([A-Za-z0-9_.\-]+\.md)")
# 2c 指路语：强信号 = 自然语言指路；弱信号 = 仅编号枚举（①②③，多为条内自带内容）
TOC_STRONG_RE = re.compile(
    r"见第|见 *Step|第 *[0-9]+ *(条|项|步|点)|上文|上节|前文|先见"
    r"|section above|见下方|见前|对应条目[：:]")
TOC_WEAK_RE = re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩]")
LURE = {
    "形态3 范围/义务": r"必须|唯一|一律|禁止|不得|所有|每条|凡",
    "形态6 外部权威": r"源码|第 *[0-9]+ *行|官方|\.py:[0-9]+|文件第",
    "形态7 能力/行为": r"支持|能查|可查|会自动|会报|退出码|可传|接受|实测",
}


def read(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def fm(text):
    """极简 frontmatter 取值（不引 yaml 依赖）。"""
    out = {}
    if not text.startswith("---"):
        return out
    body = text[3: text.find("\n---", 3)]
    for key in ("name", "version", "description", "triggers"):
        m = re.search(rf"^{key}:\s*(.+)$", body, re.M)
        if m:
            out[key] = m.group(1).strip().strip('"').strip("'")
    return out


def check(skill_dir, skills_root, max_hits):
    text = read(os.path.join(skill_dir, "SKILL.md"))
    if not text:
        return None
    meta = fm(text)
    refs_dir = os.path.join(skill_dir, "references")
    actual = ([f for f in os.listdir(refs_dir) if f.endswith(".md")]
              if os.path.isdir(refs_dir) else [])
    cited = [c for c in set(CITED_RE.findall(text)) if c not in PLACEHOLDER]
    orphans = sorted(set(actual) - set(cited))
    missing = sorted(set(cited) - set(actual))
    # 跨 skill 引用（正主在本库别的 skill 的 references/ 下）≠ 断裂——结构性假红一大来源
    cross, missing_real = [], []
    for _n in missing:
        hits = glob.glob(os.path.join(skills_root, "**", "references", _n),
                         recursive=True)
        if hits:
            cross.append({"file": _n, "owner": os.path.relpath(hits[0], skills_root)})
        else:
            missing_real.append(_n)
    missing = missing_real
    ref_chars = sum(len(read(os.path.join(refs_dir, f))) for f in actual)

    # 2b 同名副本
    name = meta.get("name") or os.path.basename(skill_dir.rstrip("/"))
    dupes = []
    for root, _dirs, files in os.walk(skills_root):
        if "SKILL.md" not in files:
            continue
        p = os.path.join(root, "SKILL.md")
        if os.path.abspath(root) == os.path.abspath(skill_dir):
            continue
        if fm(read(p)).get("name") == name:
            dupes.append(p)

    # 2c 指路语（强信号全列，弱信号仅编号枚举→抽样）
    strong, weak = [], []
    files = [os.path.join(skill_dir, "SKILL.md")] + \
            [os.path.join(refs_dir, f) for f in sorted(actual)]
    for p in files:
        for i, line in enumerate(read(p).splitlines(), 1):
            rel = os.path.relpath(p, skill_dir)
            if TOC_STRONG_RE.search(line):
                strong.append({"file": rel, "line": i, "text": line.strip()[:80]})
            elif TOC_WEAK_RE.search(line):
                weak.append({"file": rel, "line": i, "text": line.strip()[:60]})

    desc = meta.get("description", "")
    d = {
        "skill_dir": skill_dir,
        "name": name,
        "version": meta.get("version"),
        "chars": len(text),
        "references": {"count": len(actual), "chars": ref_chars,
                       "est_total_chars": len(text) + ref_chars},
        "description": {"chars": len(desc), "limit": 60,
                        "over_limit": len(desc) > 60, "first57": desc[:57]},
        "triggers_field": bool(meta.get("triggers")),
        "cited": sorted(cited), "orphans": orphans, "missing": missing,
        "cross_skill": cross,
        "duplicate_name": dupes,
        "toc_strong": strong[:max_hits], "toc_strong_total": len(strong),
        "toc_weak": weak[:max_hits], "toc_weak_total": len(weak),
        "next": {
            "criteria_overlap": "python3 <health-audit>/scripts/criteria_overlap.py " + skill_dir,
            "lures": LURE,
        },
    }
    return d


def render(d):
    L = []
    a = L.append
    a(f"== skill: {d['name']} (v{d['version']}) ==")
    desc = d["description"]
    a(f"[元信息] SKILL.md {d['chars']} 字符 | references {d['references']['count']} 个 "
      f"/ {d['references']['chars']} 字符 | 估读量 {d['references']['est_total_chars']} 字符")
    a(f"        description {desc['chars']} 字符（限 60）{'🔴 超限' if desc['over_limit'] else '✅'}"
      f" | 前57: {desc['first57']}")
    a(f"        死 triggers 字段: {'⚠️ 存在（加载器不读，应并入 description 后删）' if d['triggers_field'] else '无 ✅'}")
    a(f"[引用]  已引用 {len(d['cited'])} / 实存 {d['references']['count']}"
      f" → 孤儿 {len(d['orphans'])} {d['orphans'] or ''}"
      f" | 断裂 {len(d['missing'])} {d['missing'] or ''}")
    if d.get("cross_skill"):
        for c in d["cross_skill"]:
            a(f"        ℹ️ 跨 skill 引用（非问题）: {c['file']} → 正主 {c['owner']}")
    a(f"[2b]    同名副本遮蔽: {'🔴 ' + str(d['duplicate_name']) if d['duplicate_name'] else '无 ✅'}")
    a(f"[2c]    强信号（真指路语）{d['toc_strong_total']} 条——**逐条读原文定性**：指向本文件已迁走的节 = 断头；指向被指文件则核实体存在")
    for h in d["toc_strong"]:
        a(f"        {h['file']}:{h['line']}  {h['text']}")
    if d["toc_strong_total"] > len(d["toc_strong"]):
        a(f"        …另有 {d['toc_strong_total'] - len(d['toc_strong'])} 条（--max-hits 放大）")
    a(f"        弱信号（仅编号枚举 ①②③）{d['toc_weak_total']} 条——抽样看：多是条内自带内容（合法），"
      f"只在「编号对被指文件无实体」时算问题")
    for h in d["toc_weak"][:5]:
        a(f"        {h['file']}:{h['line']}  {h['text']}")
    a("[下一步] 8g 判据对账：先跑 criteria_overlap 出形态 1/2/4/5 候选 → **只读命中涉及的文件**；")
    a("         形态 3/6/7 用 lure 正则定向抓（不做全对象逐字通读）:")
    for k, v in d["next"]["lures"].items():
        a(f"           {k}: grep -nE \"{v}\" <skill_dir>/SKILL.md <skill_dir>/references/*.md")
    return "\n".join(L)


def scan_all(skills_root, limit=60):
    """全库扫描：description 超限 + 死 triggers 字段（--scan-all）。

    单 skill 预检只能查出本对象的门面问题；description 超限是**全库高频坑**
    （2026-09-22 实测 139 个 skill 里 14 个超限，自家维护的也有），一次扫完比
    逐个跑便宜得多。超限后果：只有前 57 字符进系统提示，尾巴等于白写。
    """
    rows = []
    for f in sorted(glob.glob(os.path.join(skills_root, "**", "SKILL.md"),
                              recursive=True)):
        if "/.archive/" in f:
            continue
        text = read(f)
        if not text:
            continue
        meta = fm(text)
        name = meta.get("name") or os.path.basename(os.path.dirname(f))
        desc = meta.get("description", "")
        rows.append({
            "skill": name, "dir": os.path.dirname(f), "chars": len(desc),
            "over": len(desc) > limit, "trailing": desc[limit:],
            "dead_triggers": bool(meta.get("triggers")),
        })
    return rows


def render_scan(root, rows, limit=60):
    over = [r for r in rows if r["over"]]
    dead = [r for r in rows if r["dead_triggers"]]
    out = [f"== 全库门面扫描: {root} ==",
           f"skill 数 {len(rows)}｜description >{limit} 字符: {len(over)}｜死 triggers 字段: {len(dead)}"]
    if over:
        out.append(f"\n[description 超限] 尾巴（第 {limit} 字符之后的全部内容）不进系统提示 = 白写：")
        for r in sorted(over, key=lambda x: -x["chars"]):
            out.append(f"    {r['chars']:5} 字符  {r['skill']}")
    else:
        out.append("\n[description 超限] 无 ✅")
    if dead:
        out.append("\n[死 triggers 字段] 加载器不读，删或改写成触发词进 description 前 57 字：")
        for r in dead:
            out.append(f"    {r['skill']}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("skill_dir", nargs="?",
                    help="被测 skill 目录；用 --scan-all 时可省")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--scan-all", action="store_true",
                    help="全库门面扫描（description 超限 + 死 triggers），忽略 skill_dir")
    ap.add_argument("--skills-root",
                    default=os.path.expanduser("~/.hermes/skills"))
    ap.add_argument("--max-hits", type=int, default=25)
    args = ap.parse_args()
    if args.scan_all:
        rows = scan_all(args.skills_root)
        print(json.dumps(rows, ensure_ascii=False, indent=1) if args.json
              else render_scan(args.skills_root, rows))
        return 0
    if not args.skill_dir:
        print("用法错误: 需要 <skill_dir>，或用 --scan-all", file=sys.stderr)
        return 2
    if not os.path.isdir(args.skill_dir):
        print(f"用法错误: 目录不存在 {args.skill_dir}", file=sys.stderr)
        return 2
    d = check(os.path.abspath(args.skill_dir), args.skills_root, args.max_hits)
    if d is None:
        print(f"用法错误: {args.skill_dir} 下无 SKILL.md", file=sys.stderr)
        return 2
    print(json.dumps(d, ensure_ascii=False, indent=1) if args.json else render(d))
    bad = bool(d["orphans"] or d["missing"] or d["duplicate_name"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
