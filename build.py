#!/usr/bin/env python3
"""
build.py — 题库 → 单文件 HTML 试卷

零第三方依赖。输入一份题库 YAML/JSON，输出一个自包含的 HTML 文件：
双击即开、离线可用、无后端、无 CDN。

用法:
    python3 build.py bank.yaml                  # 输出 <bank名>.html
    python3 build.py bank.yaml -o 试卷.html     # 指定输出
    python3 build.py bank.json                  # JSON 也支持
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# 题库解析：不依赖 PyYAML，自己解析够用的 YAML 子集
# ─────────────────────────────────────────────────────────────

def _strip_comment(line: str) -> str:
    """去掉行内 # 注释，但保留引号内的 #。"""
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ('"', "'"):
            quote = ch
            out.append(ch)
        elif ch == '#':
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _parse_scalar(val: str):
    val = val.strip()
    if not val:
        return None
    if val in ("true", "True"):
        return True
    if val in ("false", "False"):
        return False
    if val in ("null", "~", "None"):
        return None
    # 行内数组：[A, B, C] / ["a", "b"]
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        parts, buf, quote = [], [], None
        for ch in inner:
            if quote:
                if ch == quote:
                    quote = None
                else:
                    buf.append(ch)
            elif ch in ('"', "'"):
                quote = ch
            elif ch == ",":
                parts.append("".join(buf).strip())
                buf = []
            else:
                buf.append(ch)
        parts.append("".join(buf).strip())
        return [_parse_scalar(p) for p in parts if p != ""]
    if (val.startswith('"') and val.endswith('"')) or \
       (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def parse_simple_yaml(text: str):
    """
    解析题库用的 YAML 子集：
      - 顶层 key: value
      - 顶层 key: 后面跟缩进列表（- 开头）
      - 列表项可以是标量，也可以是 key: value 组成的映射
      - 再次缩进的 "- " 表示映射里的列表字段（options / answers / accept）
    不支持锚点、多行块标量、流式集合——题库用不到。
    """
    lines = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        lines.append((indent, line.strip()))

    root = {}
    i = 0
    n = len(lines)

    def parse_block(start, base_indent):
        """返回 (value, next_index)。value 是 list 或 dict。"""
        items = []
        mapping = {}
        idx = start
        mode = None
        while idx < n:
            ind, content = lines[idx]
            if ind < base_indent:
                break
            if ind > base_indent:
                # 不该发生：上一轮已处理，跳过防御
                idx += 1
                continue
            if content.startswith("- "):
                if mode is None:
                    mode = "list"
                if mode != "list":
                    break
                item_body = content[2:].strip()
                # 列表项内嵌映射
                if re.match(r'^[^:]+:\s*', item_body) and not item_body.startswith('"'):
                    key, _, rest = item_body.partition(":")
                    item = {key.strip(): _parse_scalar(rest)}
                    # 继续吃缩进更深的属性和同级子列表
                    idx += 1
                    sub_indent = None
                    while idx < n:
                        sind, scontent = lines[idx]
                        if sind <= base_indent:
                            break
                        if sub_indent is None:
                            sub_indent = sind
                        if sind != sub_indent:
                            idx += 1
                            continue
                        if scontent.startswith("- "):
                            # 嵌套列表（如 options: 后的 - "A. xxx"）
                            sub = []
                            while idx < n and lines[idx][0] == sub_indent and lines[idx][1].startswith("- "):
                                sub.append(_parse_scalar(lines[idx][1][2:].strip()))
                                idx += 1
                            item[key.strip()] = sub
                            # 关键：嵌套列表结束后，回到解析同级属性
                            continue
                        k2, _, v2 = scontent.partition(":")
                        k2, v2 = k2.strip(), v2.strip()
                        if v2 == "":
                            # 后面可能紧跟嵌套列表
                            look = idx + 1
                            if look < n and lines[look][0] > sub_indent and lines[look][1].startswith("- "):
                                sub = []
                                item_indent = lines[look][0]
                                while look < n and lines[look][0] == item_indent and lines[look][1].startswith("- "):
                                    sub.append(_parse_scalar(lines[look][1][2:].strip()))
                                    look += 1
                                item[k2] = sub
                                idx = look
                                continue
                            item[k2] = None
                        else:
                            item[k2] = _parse_scalar(v2)
                        idx += 1
                    items.append(item)
                    continue
                else:
                    items.append(_parse_scalar(item_body))
                    idx += 1
                    continue
            else:
                if mode is None:
                    mode = "dict"
                if mode != "dict":
                    break
                key, _, rest = content.partition(":")
                key, rest = key.strip(), rest.strip()
                if rest == "":
                    # 值在下一层缩进
                    look = idx + 1
                    if look < n and lines[look][0] > base_indent:
                        sub, nxt = parse_block(look, lines[look][0])
                        mapping[key] = sub
                        idx = nxt
                        continue
                    mapping[key] = None
                    idx += 1
                    continue
                mapping[key] = _parse_scalar(rest)
                idx += 1
        return (items if mode == "list" else mapping), idx

    value, _ = parse_block(0, 0)
    return value if isinstance(value, dict) else {"questions": value}


def load_bank(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return parse_simple_yaml(text)


# ─────────────────────────────────────────────────────────────
# 题库规范化 + 校验
# ─────────────────────────────────────────────────────────────

VALID_TYPES = {"single", "multiple", "judge", "fill", "short"}

TYPE_ALIASES = {
    "单选": "single", "single": "single", "radio": "single", "choice": "single",
    "多选": "multiple", "multiple": "multiple", "multi": "multiple", "checkbox": "multiple",
    "判断": "judge", "judge": "judge", "bool": "judge", "truefalse": "judge",
    "填空": "fill", "fill": "fill", "blank": "fill",
    "简答": "short", "short": "short", "essay": "short", "subjective": "short",
}


def normalize(bank: dict) -> tuple[dict, list[str]]:
    """规范化题库结构，返回 (题库, 警告列表)。"""
    warns: list[str] = []
    meta = bank.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    raw_qs = bank.get("questions") or bank.get("items") or []
    if not isinstance(raw_qs, list):
        raise ValueError("questions 必须是列表")

    questions = []
    for idx, q in enumerate(raw_qs, 1):
        if not isinstance(q, dict):
            warns.append(f"第 {idx} 题不是映射，已跳过")
            continue

        qtype = str(q.get("type", "single")).strip().lower()
        qtype = TYPE_ALIASES.get(qtype, qtype)
        if qtype not in VALID_TYPES:
            warns.append(f"第 {idx} 题 type={q.get('type')!r} 无法识别，按 single 处理")
            qtype = "single"

        stem = str(q.get("q") or q.get("question") or q.get("stem") or "").strip()
        if not stem:
            warns.append(f"第 {idx} 题缺题干，已跳过")
            continue

        item = {
            "type": qtype,
            "q": stem,
            "explain": str(q.get("explain") or q.get("analysis") or "").strip(),
            "source": str(q.get("source") or "").strip(),
            "score": q.get("score", 1),
        }

        if qtype in ("single", "multiple"):
            opts = q.get("options") or []
            if not isinstance(opts, list) or len(opts) < 2:
                warns.append(f"第 {idx} 题选项少于 2 个，已跳过")
                continue
            item["options"] = [str(o).strip() for o in opts]
            ans = q.get("answer") or q.get("answers") or []
            if not isinstance(ans, list):
                ans = [ans]
            # 支持写字母 A / a / 1 / 0，统一成索引
            norm_ans = []
            for a in ans:
                a = str(a).strip()
                if not a:
                    continue
                if a.upper() in "ABCDEFGH" and len(a) == 1:
                    norm_ans.append("ABCDEFGH".index(a.upper()))
                else:
                    try:
                        v = int(a)
                        norm_ans.append(v - 1 if v >= 1 else v)
                    except ValueError:
                        warns.append(f"第 {idx} 题答案 {a!r} 无法解析，已忽略")
            norm_ans = sorted(set(x for x in norm_ans if 0 <= x < len(item["options"])))
            if not norm_ans:
                warns.append(f"第 {idx} 题没有有效答案，已跳过")
                continue
            if qtype == "single" and len(norm_ans) > 1:
                warns.append(f"第 {idx} 题是单选却给了 {len(norm_ans)} 个答案，已改为多选")
                item["type"] = "multiple"
            item["answer"] = norm_ans

        elif qtype == "judge":
            ans = q.get("answer")
            if isinstance(ans, bool):
                item["answer"] = 0 if ans else 1   # 0=正确 1=错误
            else:
                s = str(ans).strip().lower()
                if s in ("true", "t", "对", "正确", "是", "1", "√", "y", "yes"):
                    item["answer"] = 0
                elif s in ("false", "f", "错", "错误", "否", "0", "×", "x", "n", "no"):
                    item["answer"] = 1
                else:
                    warns.append(f"第 {idx} 题判断题答案 {ans!r} 无法识别，已跳过")
                    continue
            item["options"] = ["正确", "错误"]

        elif qtype == "fill":
            accept = q.get("accept") or q.get("answers") or q.get("answer") or []
            if not isinstance(accept, list):
                accept = [accept]
            item["accept"] = [str(a).strip() for a in accept if str(a).strip()]
            if not item["accept"]:
                warns.append(f"第 {idx} 题填空题没有 accept 答案，已跳过")
                continue
            item["case_sensitive"] = bool(q.get("case_sensitive", False))

        elif qtype == "short":
            item["reference"] = str(
                q.get("reference") or q.get("answer") or q.get("explain") or ""
            ).strip()
            item["keywords"] = [str(k).strip() for k in (q.get("keywords") or []) if str(k).strip()]

        questions.append(item)

    meta.setdefault("title", "在线自测")
    meta.setdefault("pass_score", 60)
    return {"meta": meta, "questions": questions}, warns


# ─────────────────────────────────────────────────────────────
# HTML 渲染
# ─────────────────────────────────────────────────────────────

TEMPLATE_PATH = Path(__file__).with_name("template.html")


def render(bank: dict) -> str:
    tpl = TEMPLATE_PATH.read_text(encoding="utf-8")
    # 塞进 <script type="application/json"> 是安全的：只需转义 </ 防止提前闭合
    payload = json.dumps(bank, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(str(bank["meta"].get("title", "在线自测")))
    return (tpl
            .replace("/*__TITLE__*/", title)
            .replace("/*__DATA__*/", payload))


def main():
    ap = argparse.ArgumentParser(description="题库 → 单文件 HTML 试卷")
    ap.add_argument("bank", help="题库文件（.yaml / .yml / .json）")
    ap.add_argument("-o", "--out", help="输出 HTML 路径")
    ap.add_argument("--check", action="store_true", help="只校验题库，不生成 HTML")
    args = ap.parse_args()

    src = Path(args.bank)
    if not src.exists():
        sys.exit(f"找不到题库文件：{src}")

    bank = load_bank(src)
    bank, warns = normalize(bank)

    for w in warns:
        print(f"⚠️  {w}", file=sys.stderr)

    if not bank["questions"]:
        sys.exit("题库为空，无法生成")

    counts = {}
    for q in bank["questions"]:
        counts[q["type"]] = counts.get(q["type"], 0) + 1
    print(f"✅ 载入 {len(bank['questions'])} 题：" +
          " / ".join(f"{k}×{v}" for k, v in counts.items()))
    if warns:
        print(f"⚠️  {len(warns)} 条警告", file=sys.stderr)

    if args.check:
        return

    out = Path(args.out) if args.out else src.with_suffix(".html")
    out.write_text(render(bank), encoding="utf-8")
    print(f"📄 已生成：{out}  ({out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
