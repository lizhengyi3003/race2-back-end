"""读取 .docx 文本内容（无需 python-docx，直接解析 OOXML）。

用法：
    python scripts/read_docx.py <docx路径>                        # 输出全部段落（带行号）
    python scripts/read_docx.py <docx路径> --headings             # 只输出疑似标题行
    python scripts/read_docx.py <docx路径> --grep "第三章"         # 关键词定位（含上下文）
    python scripts/read_docx.py <docx路径> --range 100 200        # 指定行范围
"""

import argparse
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def read_paragraphs(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    root = ET.fromstring(xml)
    out: list[str] = []
    for p in root.iter(f"{W}p"):
        texts = [t.text or "" for t in p.iter(f"{W}t")]
        line = "".join(texts).strip()
        if line:
            out.append(line)
    return out


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--headings", action="store_true")
    ap.add_argument("--grep")
    ap.add_argument("--range", nargs=2, type=int, metavar=("START", "END"))
    ap.add_argument("--context", type=int, default=15, help="grep 上下文行数")
    args = ap.parse_args()

    path = Path(args.docx)
    if not path.exists():
        print(f"[err] 文件不存在: {path}")
        sys.exit(1)

    paras = read_paragraphs(path)
    print(f"# 文档: {path.name}  段落数: {len(paras)}\n")

    if args.grep:
        pat = args.grep
        for i, line in enumerate(paras):
            if pat in line:
                lo, hi = max(0, i - args.context), min(len(paras), i + args.context + 1)
                print(f"--- 命中 @行{i} (显示 {lo}-{hi - 1}) ---")
                for j in range(lo, hi):
                    mark = ">>" if j == i else "  "
                    print(f"{mark}{j:4d} | {paras[j]}")
                print()
        return

    if args.headings:
        # 标题特征：以数字/第X章开头、或长度较短且无标点结尾
        pat = re.compile(
            r"^(第[一二三四五六七八九十]+[章节部分]|[0-9]+(\.[0-9]+)*\s*[、.．]|[（(][一二三四五六七八九十0-9]+[)）])"
        )
        for i, line in enumerate(paras):
            if pat.match(line) or (len(line) <= 40 and not line.endswith(("。", "，", "；"))):
                print(f"{i:4d} | {line}")
        return

    if args.range:
        start, end = args.range
        for i in range(max(0, start), min(len(paras), end)):
            print(f"{i:4d} | {paras[i]}")
        return

    for i, line in enumerate(paras):
        print(f"{i:4d} | {line}")


if __name__ == "__main__":
    main()
