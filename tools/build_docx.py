"""Minimal Markdown -> DOCX builder for project documents.

Usage:  python scripts/build_docx.py <input.md> [output.docx]

Supports: #/##/### headings, paragraphs with **bold** and `code`, bullet
lists, blockquotes, pipe tables, and rules.  Chinese-first typography
(宋体 + Times New Roman, 10.5 pt body, A4 with 2.4/2.6 cm margins).
"""

from __future__ import annotations

import pathlib
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BODY_PT = 10.5
TABLE_PT = 9.0
NOTE_PT = 9.5
TEXT_WIDTH_CM = 15.6

SRC_DIR = pathlib.Path(".")
IMAGE_RE = re.compile(r"^!\[(.*?)\]\((.+?)\)\s*$")

CJK = re.compile(r"[\u3400-\u9fff\uff00-\uffef]")


def disp_len(s: str) -> int:
    return sum(2 if CJK.match(ch) else 1 for ch in s)


def set_run_font(run, size: float | None = None, bold: bool | None = None,
                 italic: bool | None = None, color: RGBColor | None = None,
                 mono: bool = False) -> None:
    name = "Consolas" if mono else "Times New Roman"
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color


TOKEN = re.compile(r"(\*\*.+?\*\*|`[^`]+`)")


def add_inline(par, text: str, size: float = BODY_PT, color=None,
               base_bold: bool = False) -> None:
    for part in TOKEN.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            r = par.add_run(part[2:-2])
            set_run_font(r, size, True, color=color)
        elif part.startswith("`") and part.endswith("`"):
            r = par.add_run(part[1:-1])
            set_run_font(r, size - 0.5, base_bold, color=color, mono=True)
        else:
            r = par.add_run(part)
            set_run_font(r, size, base_bold, color=color)


def setup(doc: Document) -> None:
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.4)
    sec.left_margin = sec.right_margin = Cm(2.6)
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(BODY_PT)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    pf = st.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(4)
    pf.line_spacing = 1.35


def add_table(doc: Document, rows: list[list[str]]) -> None:
    header, body = rows[0], rows[1:]
    ncol = len(header)
    t = doc.add_table(rows=1 + len(body), cols=ncol)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False

    raw = []
    for j in range(ncol):
        longest = max(disp_len(r[j]) if j < len(r) else 0 for r in rows)
        raw.append(max(3, min(longest, 46)))
    total = sum(raw)
    cm = [TEXT_WIDTH_CM * w / total for w in raw]
    # enforce a usable minimum column width, then renormalise exactly
    floor = 1.15 if ncol > 2 else 2.4
    cm = [max(c, floor) for c in cm]
    scale = TEXT_WIDTH_CM / sum(cm)
    cm = [c * scale for c in cm]

    for j, cell_text in enumerate(header):
        cell = t.cell(0, j)
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(1)
        add_inline(p, cell_text, TABLE_PT, base_bold=True)
        for r in p.runs:
            r.font.bold = True
    for i, row in enumerate(body, start=1):
        for j in range(ncol):
            cell = t.cell(i, j)
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            add_inline(p, row[j] if j < len(row) else "", TABLE_PT)
    for row in t.rows:
        for j, cell in enumerate(row.cells):
            cell.width = Cm(cm[j])
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def parse_table_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def is_sep(line: str) -> bool:
    s = line.strip().strip("|")
    return bool(s) and set(s.replace("|", "").replace(" ", "")) <= set("-: ")


def build(src: pathlib.Path, dst: pathlib.Path) -> None:
    lines = src.read_text(encoding="utf-8").splitlines()
    doc = Document()
    setup(doc)

    i, first_heading = 0, True
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # ![caption](path)  -> centred image plus a caption paragraph
        m = IMAGE_RE.match(stripped)
        if m:
            caption, src = m.group(1), m.group(2)
            path = (SRC_DIR / src) if not pathlib.Path(src).is_absolute() else pathlib.Path(src)
            if path.exists():
                try:
                    from PIL import Image as _Image
                    with _Image.open(path) as im:
                        px = im.size[0]
                except Exception:
                    px = 1000
                width = Cm(15.0) if px > 1500 else Cm(9.2)
                doc.add_picture(str(path), width=width)
                last = doc.paragraphs[-1]
                last.alignment = WD_ALIGN_PARAGRAPH.CENTER
                last.paragraph_format.space_before = Pt(6)
                last.paragraph_format.space_after = Pt(2)
                last.paragraph_format.keep_with_next = True
                cap = doc.add_paragraph()
                cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
                cap.paragraph_format.space_after = Pt(8)
                add_inline(cap, caption, TABLE_PT - 0.5,
                           color=RGBColor(0x33, 0x33, 0x33))
            else:
                p = doc.add_paragraph()
                add_inline(p, f"[missing figure: {src}]", BODY_PT)
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and is_sep(lines[i + 1]):
            rows = [parse_table_row(line)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(parse_table_row(lines[i]))
                i += 1
            add_table(doc, rows)
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            p = doc.add_paragraph()
            pf = p.paragraph_format
            if first_heading:
                pf.space_before = Pt(0)
                first_heading = False
            elif level == 1:
                pf.space_before = Pt(14)
            else:
                pf.space_before = Pt(10)
            pf.space_after = Pt(4)
            pf.keep_with_next = True
            size = {1: 15.0, 2: 12.5, 3: 11.0}.get(level, 10.5)
            add_inline(p, text, size, base_bold=True)
            if level == 1:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1
            continue

        if stripped.startswith(">"):
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.left_indent = Cm(0.6)
            pf.space_before = Pt(3)
            pf.space_after = Pt(5)
            add_inline(p, stripped.lstrip("> ").strip(), NOTE_PT,
                       color=RGBColor(0x44, 0x44, 0x44))
            i += 1
            continue

        if stripped.startswith(("- ", "* ")):
            p = doc.add_paragraph(style="List Bullet")
            pf = p.paragraph_format
            pf.left_indent = Cm(0.75)
            pf.space_after = Pt(2)
            add_inline(p, stripped[2:].strip())
            i += 1
            continue

        if set(stripped) <= set("-—* ") and len(stripped) >= 3:
            i += 1
            continue

        # four-space indent = displayed equation: keep it monospaced and indented
        if raw.startswith("    "):
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.left_indent = Cm(1.0)
            pf.space_before = Pt(4)
            pf.space_after = Pt(4)
            pf.keep_together = True
            r = p.add_run(stripped)
            set_run_font(r, BODY_PT - 0.5, mono=True)
            i += 1
            continue

        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(5)
        add_inline(p, stripped)
        i += 1

    doc.save(str(dst))
    print(f"wrote {dst}")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: build_docx.py <input.md> [output.docx]")
    global SRC_DIR
    src = pathlib.Path(sys.argv[1])
    SRC_DIR = src.parent.resolve()
    dst = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".docx")
    build(src, dst)


if __name__ == "__main__":
    main()


