#!/usr/bin/env python3
"""健康体检脚本自测：一条命令验证 audit_skill_health.py + preflight_check.py 的行为。

**为什么要有这个文件**（2026-09-22 立）：这两个脚本是验收链与发布链的承重件，
但此前每次验证都靠临时手搓夹具（`neg-skill` 那种），验完即弃、不可复现，
下一次改动又得重造一遍。本文件把夹具与断言固化：clone 后跑
`python3 scripts/selftest.py` 即可自证，不依赖任何本机既有 skill。

覆盖的回归点（每条都对应一次真实踩坑）：
  A 良构 skill          → audit / preflight 双绿，且预检输出含 [并发写入] 段
  B 病构 skill          → 双红，且孤儿 / 断裂 / 重复二级标题 / 代码块未配对都被点名
  B5 退出码语义         → 超限/死 triggers 属注意级（exit 0），孤儿/断裂/同名副本才阻断（exit 1）
  C 含点文件名          → `v0.20.5-audit-2026-08.md` 不被正则截成 `08.md`（假孤儿+假断裂）
  D 跨 skill 引用       → 本 skill 没有、兄弟 skill 有 ⇒ ℹ️ 非问题、不判红（结构性假红）
  E `--scan-all`        → 全库门面扫描抓到超限 description
  F LURE 零断言守护     → 三形态 lure 正则在预置语料上必须命中（删任一项本组转红）

退出码：0 = 全部通过；1 = 有断言失败。
用法：`python3 scripts/selftest.py`（无需参数，夹具建在临时目录、跑完即删）
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.join(HERE, "audit_skill_health.py")
PREFLIGHT = os.path.join(HERE, "preflight_check.py")
PY = sys.executable or "python3"

FM = "---\nname: {n}\ndescription: \"{d}\"\nversion: 1.0.0\n---\n\n"
LONG_DESC = ("这是一条故意写得很长的门面描述用来验证全库扫描与单对象预检都能抓到长度越界"
             "并给出红灯提示的填充文字不可精简这部分继续加长以确保越过六十字符的判定线")


def build_fixture(root):
    """建一棵 skills/ 夹具树（根目录名必须叫 skills，脚本靠它认全库范围）。"""
    def wr(rel, text):
        p = os.path.join(root, "skills", rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)

    wr("good-skill/SKILL.md", FM.format(n="good-skill", d="良构示例") +
       "# 标题\n\n见 [references/ok.md](references/ok.md)。\n\n```sh\necho hi\n```\n")
    wr("good-skill/references/ok.md", "# ok\n")

    # 仅 description 超限、其余全良构 → 用来验证「注意级不阻断」（退出码须为 0）
    wr("over-skill/SKILL.md", FM.format(n="over-skill", d=LONG_DESC) +
       "# 标题\n\n见 [references/ok2.md](references/ok2.md)。\n")
    wr("over-skill/references/ok2.md", "# ok2\n")

    # 病构：孤儿 + 断裂 + 重复二级标题 + 代码块未配对 + description 超限
    wr("bad-skill/SKILL.md", FM.format(n="bad-skill", d=LONG_DESC) +
       "# 标题\n\n## 重复\n\n## 重复\n\n见 references/missing.md 与 references/orphan.md\n\n```sh\nunclosed\n")
    wr("bad-skill/references/orphan.md", "# orphan\n")
    # 正文没引它 → 真孤儿（注意：被引用的文件不算孤儿，夹具别再踩这个坑）
    wr("bad-skill/references/never-cited.md", "# never cited\n")

    # 含点文件名回归
    wr("dot-skill/SKILL.md", FM.format(n="dot-skill", d="含点文件名回归") +
       "# 标题\n\n见 references/v0.20.5-audit-2026-08.md。\n")
    wr("dot-skill/references/v0.20.5-audit-2026-08.md", "# dot\n")

    # 跨 skill 引用回归：cross-a 引的 shared.md 只有 cross-b 有
    wr("cross-a/SKILL.md", FM.format(n="cross-a", d="跨 skill 引用示例") +
       "# 标题\n\n见 references/shared.md。\n")
    wr("cross-b/SKILL.md", FM.format(n="cross-b", d="正主 skill") + "# 标题\n")
    wr("cross-b/references/shared.md", "# shared\n")


def run(script, *args):
    p = subprocess.run([PY, script, *args], capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


FAILS = []


def case(name, cond, detail=""):
    print(("✅ " if cond else "❌ ") + name + ("" if cond else f"   ← {detail.strip()[:600]}"))
    if not cond:
        FAILS.append(name)


def main():
    root = tempfile.mkdtemp(prefix="skill-scripts-selftest-")
    try:
        build_fixture(root)
        S = os.path.join(root, "skills")
        good, bad = os.path.join(S, "good-skill"), os.path.join(S, "bad-skill")
        over = os.path.join(S, "over-skill")
        dot, cross_a = os.path.join(S, "dot-skill"), os.path.join(S, "cross-a")

        print("【A】良构 skill —— 应双绿")
        rc, out = run(AUDIT, good)
        case("A1 audit 退出 0", rc == 0, f"rc={rc}\n{out}")
        case("A2 audit 报结构健康", "结构健康" in out, out)
        rc, out = run(PREFLIGHT, good, "--skills-root", S)
        case("A3 preflight 退出 0", rc == 0, f"rc={rc}\n{out}")
        case("A4 预检含 [并发写入] 段", "[并发写入]" in out, out)
        case("A5 预检报孤儿 0", "孤儿 0" in out, out)
        case("A6 良构 skill 不得被误报灯", "超限" not in out, out)

        print("【B】病构 skill —— 应双红且点名四类病")
        rc, out = run(AUDIT, bad)
        case("B1 audit 退出 1", rc == 1, f"rc={rc}\n{out}")
        for marker in ("孤儿", "断裂", "重复二级标题", "代码块未配对"):
            case(f"B2 audit 点出「{marker}」", marker in out, out)
        rc, out = run(PREFLIGHT, bad, "--skills-root", S)
        case("B3 preflight 退出 1", rc == 1, f"rc={rc}\n{out}")
        case("B4 预检点出 description 越界（注意级符号）", "⚠️ 超限" in out, out)
        case("B4b 越界不得用 🔴 阻断符（符号跟后果走）", "🔴 超限" not in out, out)

        print("【B5】退出码语义 —— 超限不阻断、孤儿必阻断")
        rc, out = run(PREFLIGHT, over, "--skills-root", S)
        case("B5a 仅超限的 skill 退出 0（注意级）", rc == 0, f"rc={rc}\n{out}")
        case("B5b 仅超限时仍点出超限事实", "超限" in out, out)
        rc, out = run(PREFLIGHT, bad, "--skills-root", S)
        case("B5c 含孤儿的 skill 退出 1（阻断级）", rc == 1, f"rc={rc}\n{out}")
        rc, out = run(PREFLIGHT, good, "--skills-root", S)
        case("B5d 干净 skill 退出 0", rc == 0, f"rc={rc}\n{out}")

        print("【F】LURE 零断言守护 —— 删任一 lure 项必须转红")
        sys.path.insert(0, os.path.dirname(PREFLIGHT))
        for m in ("preflight_check",):
            sys.modules.pop(m, None)
        import preflight_check as P
        # 每个 lure 词一条独立语料：一句里塞多个词，删任一项仍会命中 → 断言恒绿等于装饰
        # （实测第一版三形态各给一句综合语料，变异删「文件第/一律/实测」selftest 仍全绿，
        #   逼不出真红；改成逐词单点语料后同样变异转红）
        WORDS = {
            "形态3 范围/义务": ["必须", "唯一", "一律", "禁止", "不得", "所有", "每条", "凡"],
            "形态6 外部权威": ["源码", "第 42 行", "官方", "core.py:120", "文件第"],
            "形态7 能力/行为": ["支持", "能查", "可查", "会自动", "会报", "退出码", "可传", "接受", "实测"],
        }
        for key, words in WORDS.items():
            case(f"F-{key} 键存在", key in P.LURE, str(list(P.LURE)))
            rx = re.compile(P.LURE.get(key, r"$^"))
            for w in words:
                case(f"F-{key}·{w}", bool(rx.search(w)),
                    f"lure 正则匹配不到单点语料 {w!r}（正则={rx.pattern!r}）")
        case("F-LURE 恰为三形态", len(P.LURE) == 3, str(list(P.LURE)))
        # 负向：不属本形态的词不该被本形态命中（防 lure 过宽）
        for key, neg in (("形态3 范围/义务", "随便提一句"),
                         ("形态6 外部权威", "见下一节"),
                         ("形态7 能力/行为", "本节讲一件事")):
            case(f"F-{key}·负向「{neg}」", not re.search(P.LURE[key], neg),
                f"lure 过宽，命中了无关语料 {neg!r}")

        print("【C】含点文件名 —— 不得被截断成 08.md")
        rc, out = run(AUDIT, dot)
        case("C1 audit 退出 0", rc == 0, f"rc={rc}\n{out}")
        case("C2 输出无 08.md 残留", "08.md" not in out, out)

        print("【D】跨 skill 引用 —— 应 ℹ️ 非问题、不判红")
        rc, out = run(AUDIT, cross_a)
        case("D1 audit 退出 0", rc == 0, f"rc={rc}\n{out}")
        case("D2 audit 标 ℹ️ 跨 skill", "跨 skill" in out, out)
        rc, out = run(PREFLIGHT, cross_a, "--skills-root", S)
        case("D3 preflight 退出 0", rc == 0, f"rc={rc}\n{out}")
        case("D4 preflight 标跨 skill 非问题", "跨 skill" in out, out)

        print("【E】--scan-all 全库门面扫描")
        rc, out = run(PREFLIGHT, "--scan-all", "--skills-root", S)
        case("E1 抓到超限 description 的 skill 名", "bad-skill" in out, out)
        case("E2 报 skill 计数", "skill 数" in out, out)

        print()
        if FAILS:
            print(f"❌ 自测失败：{len(FAILS)} 条 —— " + "；".join(FAILS))
            return 1
        print("✅ 自测全过：audit + preflight 行为与回归点一致")
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
