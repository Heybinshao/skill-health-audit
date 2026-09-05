# 体检补充坑（2026-08-24 路径模拟 book-distiller 后沉淀）

主清单在 SKILL.md；本文件存放第 8b 节（doc/script 割裂）的延伸坑，待下次前台会话并入正文。

## 8b 延伸：两类「半割裂」

1. **脚本用法的相对路径**
   - 表现：SKILL.md 正文写 `python3 scripts/x.py <文件>` 这类相对路径引用。脚本本身被引用了（不算孤儿），但 agent 工作目录通常不是 skill 目录，照抄命令必报 file not found。
   - 修法：脚本引用一律给绝对路径，如 `<你的skill安装目录>/scripts/x.py`。

2. **config.json 死配置**
   - 表现：配置文件定义了字段（如子目录名、开关），但 SKILL.md 正文流程全硬编码、从未说读取 → 配置是装饰，用户改了不生效。属 doc/config 割裂，与 doc/script 割裂同族。
   - 实测案例（book-distiller v2.0.0，2026-08-24）：config.json 有 `use_subdirs` / `original_subdir` / `distilled_subdir` 三字段，正文全部硬编码 `01｜书籍原文`、`02｜蒸馏拆解`，从未读 config。
   - 修法二选一：正文注明「X 读 config 对应字段」，或删掉冗余字段——不留装饰性配置。

## 检查法补充

```bash
grep -nE "python3? (scripts|\.)" SKILL.md        # 找脚本调用，核对是否绝对路径
grep -nE "config\.json|output_path" SKILL.md     # config 字段是否真的被流程引用
cat <skill_dir>/config.json 2>/dev/null          # 有配置就逐字段对正文
```

## 关联

- 时序错位类问题（检查步骤排在分发/写入之后）见 path-simulation 的「常见坑·时序错位」，体检阶段可用 grep 快筛：「必做」「必须在前」标注的条目是否位于对应写入步骤之后。
