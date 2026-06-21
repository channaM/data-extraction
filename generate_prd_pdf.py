"""
Generates a colorful, professional PDF version of PRD.md.

Usage:
    python generate_prd_pdf.py

Output:
    PRD.pdf  (in the same directory as this script)

Requirements:
    pip install reportlab
"""

import subprocess
import sys


def _ensure_reportlab():
    try:
        import reportlab  # noqa: F401
    except ImportError:
        print("Installing reportlab...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])


_ensure_reportlab()

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable


# ──────────────────────────────────────────────────────────────────────────────
# Colour Palette
# ──────────────────────────────────────────────────────────────────────────────

NAVY        = colors.HexColor("#1a1a2e")
DARK_PANEL  = colors.HexColor("#16213e")
ACCENT      = colors.HexColor("#0f3460")
HIGHLIGHT   = colors.HexColor("#e94560")
GREEN       = colors.HexColor("#00b894")
GOLD        = colors.HexColor("#f0a500")
LIGHT_BLUE  = colors.HexColor("#4fc3f7")
WHITE       = colors.white
LIGHT_GRAY  = colors.HexColor("#a0aec0")
ROW_ALT     = colors.HexColor("#eaf2ff")
ROW_MAIN    = colors.HexColor("#f7fbff")
HEADER_BG   = colors.HexColor("#0f3460")
COVER_TEXT  = colors.HexColor("#e0e0e0")


# ──────────────────────────────────────────────────────────────────────────────
# Custom Flowables
# ──────────────────────────────────────────────────────────────────────────────

class CoverPage(Flowable):
    def __init__(self, width, height):
        super().__init__()
        self.width  = width
        self.height = height

    def draw(self):
        c = self.canv
        w, h = self.width, self.height

        # Dark background
        c.setFillColor(NAVY)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        # Accent stripe at top
        c.setFillColor(ACCENT)
        c.rect(0, h - 18*mm, w, 18*mm, fill=1, stroke=0)

        # Highlight bar
        c.setFillColor(HIGHLIGHT)
        c.rect(0, h - 22*mm, w, 4*mm, fill=1, stroke=0)

        # Gold side bar
        c.setFillColor(GOLD)
        c.rect(0, 0, 8*mm, h, fill=1, stroke=0)

        # Bank icon area
        c.setFillColor(ACCENT)
        c.roundRect(w/2 - 30*mm, h - 90*mm, 60*mm, 50*mm, 8, fill=1, stroke=0)

        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(w/2, h - 60*mm, "🏦")
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(w/2, h - 72*mm, "BANK ETL ENGINE")

        # Title
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(w/2, h - 110*mm, "Bank Statement")

        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(w/2, h - 125*mm, "ETL Engine")

        # Subtitle
        c.setFillColor(COVER_TEXT)
        c.setFont("Helvetica", 13)
        c.drawCentredString(w/2, h - 143*mm, "Product Requirements Document")

        # Divider
        c.setStrokeColor(HIGHLIGHT)
        c.setLineWidth(2)
        c.line(w/2 - 40*mm, h - 152*mm, w/2 + 40*mm, h - 152*mm)

        # Meta info
        meta = [
            ("Document ID", "BSE-PRD-001"),
            ("Version",     "1.0"),
            ("Date",        "2026-06-21"),
            ("Status",      "Active — Living Document"),
            ("Owner",       "channa.meng"),
        ]
        y = h - 168*mm
        for label, value in meta:
            c.setFillColor(LIGHT_BLUE)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(w/2 - 45*mm, y, label + ":")
            c.setFillColor(WHITE)
            c.setFont("Helvetica", 9)
            c.drawString(w/2 - 10*mm, y, value)
            y -= 8*mm

        # Bottom tagline
        c.setFillColor(LIGHT_GRAY)
        c.setFont("Helvetica-Oblique", 9)
        c.drawCentredString(w/2, 22*mm, "One click. Any bank. Any format. Clean Excel. Every time.")

        # Bottom stripe
        c.setFillColor(HIGHLIGHT)
        c.rect(0, 0, w, 8*mm, fill=1, stroke=0)


class SectionHeader(Flowable):
    """A bold, colored section heading band."""

    def __init__(self, text, width, color=ACCENT, text_color=WHITE, font_size=13):
        super().__init__()
        self.text       = text
        self.width      = width
        self.color      = color
        self.text_color = text_color
        self.font_size  = font_size
        self.height     = font_size * 2.2

    def draw(self):
        c = self.canv
        c.setFillColor(self.color)
        c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)

        c.setFillColor(GOLD)
        c.rect(0, 0, 4, self.height, fill=1, stroke=0)

        c.setFillColor(self.text_color)
        c.setFont("Helvetica-Bold", self.font_size)
        c.drawString(10, self.height * 0.28, self.text)

    def wrap(self, *args):
        return self.width, self.height


class SubHeader(Flowable):
    """A lighter sub-section header."""

    def __init__(self, text, width, color=DARK_PANEL):
        super().__init__()
        self.text   = text
        self.width  = width
        self.color  = color
        self.height = 18

    def draw(self):
        c = self.canv
        c.setFillColor(self.color)
        c.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=0)

        c.setFillColor(HIGHLIGHT)
        c.rect(0, 0, 3, self.height, fill=1, stroke=0)

        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(8, 5, self.text)

    def wrap(self, *args):
        return self.width, self.height


# ──────────────────────────────────────────────────────────────────────────────
# Styles
# ──────────────────────────────────────────────────────────────────────────────

def build_styles():
    base = getSampleStyleSheet()

    body = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=9,
        leading=14,
        textColor=colors.HexColor("#222222"),
        spaceAfter=4,
    )

    code = ParagraphStyle(
        "code",
        fontName="Courier",
        fontSize=8,
        leading=12,
        textColor=colors.HexColor("#1a1a2e"),
        backColor=colors.HexColor("#f0f4f8"),
        borderPadding=(4, 6, 4, 6),
        spaceAfter=4,
    )

    bullet = ParagraphStyle(
        "bullet",
        parent=body,
        leftIndent=12,
        bulletIndent=0,
        spaceAfter=2,
    )

    caption = ParagraphStyle(
        "caption",
        fontName="Helvetica-Oblique",
        fontSize=8,
        textColor=LIGHT_GRAY,
        alignment=TA_CENTER,
        spaceAfter=6,
    )

    highlight_box = ParagraphStyle(
        "highlight_box",
        fontName="Helvetica",
        fontSize=9,
        leading=14,
        textColor=WHITE,
        backColor=ACCENT,
        borderPadding=(6, 8, 6, 8),
        spaceAfter=6,
    )

    return {"body": body, "code": code, "bullet": bullet,
            "caption": caption, "highlight": highlight_box}


# ──────────────────────────────────────────────────────────────────────────────
# Table helpers
# ──────────────────────────────────────────────────────────────────────────────

def info_table(rows, col_widths, styles_extra=None):
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [ROW_MAIN, ROW_ALT]),
        ("FONTNAME",   (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",   (0, 1), (-1, -1), 8),
        ("TEXTCOLOR",  (0, 1), (-1, -1), NAVY),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#c0cfe0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]
    if styles_extra:
        ts.extend(styles_extra)
    return Table(rows, colWidths=col_widths, style=TableStyle(ts), hAlign="LEFT")


def arch_box(text, style, width, bg=DARK_PANEL, fg=WHITE):
    """A styled code/architecture box."""
    lines = text.strip().split("\n")
    data  = [[Paragraph(
        f'<font name="Courier" size="7.5" color="{fg.hexval() if hasattr(fg,"hexval") else "#ffffff"}">'
        + line.replace(" ", "&nbsp;").replace("<", "&lt;").replace(">", "&gt;")
        + "</font>",
        style["body"],
    )] for line in lines]
    ts = TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ])
    return Table(data, colWidths=[width], style=ts, hAlign="LEFT")


# ──────────────────────────────────────────────────────────────────────────────
# Page template
# ──────────────────────────────────────────────────────────────────────────────

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm


def header_footer(canvas, doc):
    canvas.saveState()
    w = PAGE_W

    if doc.page > 1:
        # Header bar
        canvas.setFillColor(ACCENT)
        canvas.rect(0, PAGE_H - 12*mm, w, 12*mm, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, PAGE_H - 13*mm, w, 1*mm, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(MARGIN, PAGE_H - 8*mm, "Bank Statement ETL Engine — PRD")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - MARGIN, PAGE_H - 8*mm, "BSE-PRD-001 v1.0")

        # Footer
        canvas.setFillColor(ACCENT)
        canvas.rect(0, 0, w, 10*mm, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, 10*mm, w, 0.8*mm, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(MARGIN, 3.5*mm, "Confidential — Internal Use Only")
        canvas.drawRightString(w - MARGIN, 3.5*mm, f"Page {doc.page}")

    canvas.restoreState()


# ──────────────────────────────────────────────────────────────────────────────
# Content builders
# ──────────────────────────────────────────────────────────────────────────────

TEXT_W = PAGE_W - 2 * MARGIN


def p(text, style):
    return Paragraph(text, style)


def sp(h=4):
    return Spacer(1, h)


def hr(color=ACCENT, thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=4)


def build_story(styles):
    S = styles
    W = TEXT_W

    story = []

    # ── Cover ──────────────────────────────────────────────────────────────
    story.append(NextPageTemplate("content"))
    story.append(CoverPage(PAGE_W, PAGE_H))
    story.append(PageBreak())

    # ── 1. Executive Summary ───────────────────────────────────────────────
    story.append(SectionHeader("1.  Executive Summary", W))
    story.append(sp(6))
    story.append(p(
        "This document defines the complete product requirements for the "
        "<b>Bank Statement ETL Engine</b> — a professional, standalone "
        "Python-based desktop system that reads bank statement files in any "
        "format (CSV, XLS, XLSX, PDF), normalises them into a clean standard "
        "structure, and produces organised Excel output files grouped by "
        "<b>bank / year / month / currency</b>.",
        S["body"],
    ))
    story.append(sp(4))

    highlights = [
        ("Single Click", "One <b>launcher.bat</b> opens the entire application — no terminal, no configuration."),
        ("Any Format",   "Source files can be <b>CSV, XLS, XLSX, or PDF</b>. Output is always clean <b>XLSX</b>."),
        ("Standalone",   "Each bank engine runs in its <b>own Python venv</b> — completely independent."),
        ("Auto-Detect",  "Year, month, and currency are <b>read from the data</b> — never typed manually."),
        ("Scalable",     "Designed for <b>ABA Bank first</b>, expandable to <b>200+ banks</b> with no refactoring."),
        ("GUI",          "Professional <b>PyQt6</b> desktop interface — colourful, friendly for all skill levels."),
        ("Database",     "<b>SQLite</b> now. <b>PostgreSQL</b> via Docker when volume justifies it."),
    ]
    rows = [["Feature", "Description"]] + [[k, Paragraph(v, S["body"])] for k, v in highlights]
    story.append(info_table(rows, [3.5*cm, W - 3.5*cm]))
    story.append(sp(10))

    # ── 2. Vision & Goals ─────────────────────────────────────────────────
    story.append(SectionHeader("2.  Project Vision & Goals", W))
    story.append(sp(6))
    story.append(p(
        "<b>Vision:</b> One professional desktop application that any user — "
        "from an absolute beginner to a power user — can open, select a bank, "
        "drop a statement file, and receive a clean, organised Excel output in "
        "seconds. No command line. No configuration. No manual column mapping "
        "at runtime.",
        S["body"],
    ))
    story.append(sp(6))

    goals = [
        ["#", "Goal", "Priority"],
        ["G1", "Process any format (CSV/XLS/XLSX/PDF) → clean XLSX",         "Must Have"],
        ["G2", "Single launcher.bat — one click opens everything",            "Must Have"],
        ["G3", "Each bank engine isolated in its own venv",                   "Must Have"],
        ["G4", "Auto-detect year, month, currency from transaction data",     "Must Have"],
        ["G5", "Output folder auto-created: output/aba/2025/202501/USD/",    "Must Have"],
        ["G6", "Professional PyQt6 GUI — colourful, beginner-friendly",      "Must Have"],
        ["G7", "SQLite database to persist all processed transactions",       "Must Have"],
        ["G8", "Proof of concept with ABA Bank only first",                  "Must Have"],
        ["G9", "Architecture supports 200 banks without refactoring",        "Must Have"],
        ["G10","Future migration to PostgreSQL via Docker",                   "Should Have"],
    ]
    extra = [("TEXTCOLOR", (2, 1), (2, -1), GREEN)]
    story.append(info_table(goals, [1.2*cm, W - 3.8*cm, 2.6*cm], extra))
    story.append(sp(10))

    # ── 3. Core Design Principles ─────────────────────────────────────────
    story.append(SectionHeader("3.  Core Design Principles", W))
    story.append(sp(6))

    principles = [
        ("P1 — One Bank, One Engine, One Venv",
         "Every bank has its own isolated Python virtual environment. Bank A's "
         "dependencies never affect Bank B."),
        ("P2 — Single Entry Point for the User",
         "The user only ever sees and clicks ONE file: launcher.bat. "
         "The GUI handles everything else."),
        ("P3 — Auto-Detect, Never Ask",
         "The engine figures out year, month, and currency by reading the "
         "transactions. The user is never asked."),
        ("P4 — Source Format is the Bank's Problem, Not the User's",
         "Whether ABA sends a PDF or a CSV this month, the engine handles it "
         "silently. The user just drops the file."),
        ("P5 — Output is Always Clean XLSX",
         "No matter what format comes in, what comes out is always a clean, "
         "formatted .xlsx Excel file."),
        ("P6 — Logic Stays Separate from Interface",
         "ETL pipeline code must never know about the GUI. "
         "The GUI calls the pipeline via subprocess."),
        ("P7 — Each Bank is a Blueprint Copy",
         "Adding Bank #50 means: copy the aba/ folder, rename it, fill in the "
         "column mapping. Nothing else changes."),
    ]
    for title, desc in principles:
        story.append(SubHeader(title, W))
        story.append(sp(3))
        story.append(p(desc, S["body"]))
        story.append(sp(5))

    story.append(PageBreak())

    # ── 4. Architecture Overview ──────────────────────────────────────────
    story.append(SectionHeader("4.  System Architecture Overview", W))
    story.append(sp(6))

    arch_text = """\
USER  double-clicks  launcher.bat
        │
        ▼
launcher.bat  →  detects Python  →  launches  gui/main.py
        │
        ▼
PyQt6 GUI
  ├─ Bank Selector      (auto-discovers banks/ folder)
  ├─ File Drop Zone     (drag & drop or Browse button)
  ├─ Process Button     (triggers the selected bank's engine)
  ├─ Progress Display   (Extracting… Transforming… Exporting…)
  └─ Results Table      (shows all processed transactions)
        │
        │  calls via subprocess
        ▼
Per-Bank Standalone Engine
  banks/aba/run.py  ← called with source file path as argument
        ├─ detect.py    → identify CSV / XLS / XLSX / PDF
        ├─ extract.py   → read into DataFrame
        ├─ transform.py → map columns to standard schema
        └─ export.py    → write clean .xlsx output
        │
        ▼
output/aba/2025/202501/USD/aba_202501_USD.xlsx
        │
        ▼
database/bank_statements.db   (SQLite Phase 1)
PostgreSQL via Docker          (Phase 2 — future)"""

    story.append(arch_box(arch_text, S, W, bg=NAVY, fg=WHITE))
    story.append(sp(10))

    # ── 5. Folder Structure ───────────────────────────────────────────────
    story.append(SectionHeader("5.  Folder Structure", W))
    story.append(sp(6))

    folder_text = """\
project-root/
│
├── launcher.bat                  ← THE ONLY FILE THE USER CLICKS
│
├── gui/                          ← Shared PyQt6 GUI application
│   ├── venv/                     ← GUI's own virtual environment
│   ├── requirements.txt          ← PyQt6 + GUI dependencies only
│   ├── main.py                   ← Entry point
│   ├── windows/                  ← Window classes
│   ├── widgets/                  ← Reusable UI components
│   └── assets/styles/theme.qss   ← Color theme stylesheet
│
├── banks/
│   ├── aba/                      ← ABA Bank — fully standalone
│   │   ├── venv/                 ← ABA's own venv (.gitignored)
│   │   ├── requirements.txt      ← ABA's own dependencies
│   │   ├── setup.bat             ← Creates venv and installs deps
│   │   ├── run.py                ← Entry point called by GUI
│   │   ├── config.py             ← ABA column mappings
│   │   ├── pipeline/
│   │   │   ├── detect.py
│   │   │   ├── extract.py
│   │   │   ├── transform.py
│   │   │   └── export.py
│   │   └── db/
│   │       └── sqlite_loader.py
│   │
│   └── [future banks follow same structure]
│
├── downloads/
│   └── aba/                      ← Drop ABA source files here
│
├── output/
│   └── aba/
│       └── 2025/
│           └── 202501/
│               ├── USD/
│               │   └── aba_202501_USD.xlsx
│               └── KHR/
│                   └── aba_202501_KHR.xlsx
│
├── database/
│   └── bank_statements.db        ← SQLite database
│
└── PRD.md                        ← This document"""

    story.append(arch_box(folder_text, S, W, bg=DARK_PANEL, fg=WHITE))
    story.append(sp(10))
    story.append(PageBreak())

    # ── 6. Single Launcher ────────────────────────────────────────────────
    story.append(SectionHeader("6.  Single Launcher — launcher.bat", W))
    story.append(sp(6))
    story.append(p(
        "The user only ever sees <b>one file: launcher.bat</b>. "
        "This is a fundamental UX requirement. One double-click launches the "
        "entire system. There must never be one .bat file per bank — that "
        "would force users to know which bank to click, and scale to "
        "200 .bat files.",
        S["body"],
    ))
    story.append(sp(5))

    launcher_text = """\
launcher.bat  (simplified logic)

1. Check Python 3.10+ is installed
2. If gui/venv does not exist → run gui/setup.bat to create it
3. For each bank in banks/ → if venv missing → run banks/{name}/setup.bat
4. Launch:  gui/venv/Scripts/python.exe  gui/main.py
5. GUI takes full control — no terminal visible to user"""

    story.append(arch_box(launcher_text, S, W))
    story.append(sp(6))
    story.append(p(
        "The GUI calls each bank engine programmatically via "
        "<b>subprocess</b> — passing the source file path as an argument "
        "and reading a JSON result from stdout. The user selects the bank "
        "in the GUI dropdown; the launcher never needs to know which bank.",
        S["body"],
    ))
    story.append(sp(10))

    # ── 7. ETL Pipeline ───────────────────────────────────────────────────
    story.append(SectionHeader("7.  ETL Pipeline — Extract Transform Load", W))
    story.append(sp(6))

    etl_rows = [
        ["Stage", "Input", "Output", "Key Logic"],
        ["DETECT",    "File path",           "file_type, valid flag",    "Read extension + magic bytes"],
        ["EXTRACT",   "File path + type",    "Raw DataFrame",            "pandas / xlrd / pdfplumber"],
        ["TRANSFORM", "Raw DataFrame",       "List of standard records", "Apply COLUMN_MAP, cast types"],
        ["EXPORT",    "Standard records",    "Clean .xlsx file",         "Auto-create folder, format table"],
        ["LOAD",      "Standard records",    "SQLite rows",              "INSERT OR IGNORE (no duplicates)"],
    ]
    story.append(info_table(etl_rows, [2*cm, 3*cm, 3.5*cm, W - 8.5*cm]))
    story.append(sp(8))

    story.append(SubHeader("COLUMN_MAP — How Each Bank Teaches the Engine", W))
    story.append(sp(4))
    story.append(p(
        "Each bank's <b>config.py</b> contains a <b>COLUMN_MAP</b> dictionary. "
        "The keys are the bank's actual column header names exactly as they "
        "appear in the source file. The values are the standard field names "
        "that every bank's output must conform to.",
        S["body"],
    ))
    story.append(sp(4))
    col_map_text = """\
# banks/aba/config.py  (example — to be confirmed with real ABA statement)

BANK_NAME  = "aba"

COLUMN_MAP = {
    "Tran Date"  :  "transaction_date",
    "Narration"  :  "description",
    "Debit"      :  "debit_amount",
    "Credit"     :  "credit_amount",
    "Balance"    :  "balance",
    "Ref No"     :  "reference_id",
    "CCY"        :  "currency",
    "Account No" :  "account_number",
}"""
    story.append(arch_box(col_map_text, S, W))
    story.append(sp(10))
    story.append(PageBreak())

    # ── 8. Standard Output Schema ─────────────────────────────────────────
    story.append(SectionHeader("8.  Standard Output Schema", W))
    story.append(sp(6))
    story.append(p(
        "Every bank, regardless of source format, produces records "
        "conforming to this schema. This is the contract that the ETL "
        "pipeline, the Excel exporter, and the database all rely on.",
        S["body"],
    ))
    story.append(sp(6))

    schema_rows = [
        ["Field",            "Type",      "Required", "Description"],
        ["transaction_date", "date",      "Yes",      "Date the transaction occurred"],
        ["account_number",   "str",       "No",       "Bank account number"],
        ["account_name",     "str",       "No",       "Account holder name"],
        ["reference_id",     "str",       "No",       "Bank's transaction reference"],
        ["description",      "str",       "No",       "Narration / transaction description"],
        ["debit_amount",     "Decimal",   "No",       "Money going out (always positive)"],
        ["credit_amount",    "Decimal",   "No",       "Money coming in (always positive)"],
        ["balance",          "Decimal",   "No",       "Running balance after transaction"],
        ["currency",         "str",       "Yes",      "3-letter code: USD, KHR, etc."],
        ["bank_name",        "str",       "Yes",      "Bank identifier e.g. 'aba'"],
        ["source_file",      "str",       "Yes",      "Original filename processed"],
    ]
    req_style = [
        ("TEXTCOLOR", (2, 1), (2, -1), NAVY),
    ]
    for i, row in enumerate(schema_rows[1:], start=1):
        if row[2] == "Yes":
            req_style.append(("TEXTCOLOR", (2, i), (2, i), GREEN))
            req_style.append(("FONTNAME",  (2, i), (2, i), "Helvetica-Bold"))

    story.append(info_table(schema_rows, [3.2*cm, 1.8*cm, 1.8*cm, W - 6.8*cm], req_style))
    story.append(sp(4))
    story.append(p(
        "<b>Amount convention:</b> Debit and Credit are always stored as "
        "<b>positive numbers</b> in separate columns. If the bank uses a "
        "single amount column with +/- signs, the transform stage splits them.",
        S["body"],
    ))
    story.append(sp(10))

    # ── 9. Output Folder Convention ───────────────────────────────────────
    story.append(SectionHeader("9.  Output File & Folder Convention", W))
    story.append(sp(6))

    path_text = """\
output/
  {bank_name}/
    {year}/
      {year}{month_2digits}/
        {CURRENCY}/
          {bank_name}_{year}{month_2digits}_{CURRENCY}.xlsx

Examples:
  output/aba/2025/202501/USD/aba_202501_USD.xlsx
  output/aba/2025/202501/KHR/aba_202501_KHR.xlsx
  output/aba/2025/202502/USD/aba_202502_USD.xlsx
  output/aba/2024/202412/USD/aba_202412_USD.xlsx"""

    story.append(arch_box(path_text, S, W))
    story.append(sp(6))

    auto_rows = [
        ["What to determine", "How it is determined"],
        ["Year + Month",      "Most frequent (year, month) pair from transaction_date values"],
        ["Currency",          "Most frequent currency value across all records"],
        ["Multi-currency",    "If USD and KHR both appear → produce two separate output files"],
    ]
    story.append(info_table(auto_rows, [4.5*cm, W - 4.5*cm]))
    story.append(sp(10))
    story.append(PageBreak())

    # ── 10. GUI Specification ─────────────────────────────────────────────
    story.append(SectionHeader("10.  GUI Specification — PyQt6", W))
    story.append(sp(6))
    story.append(p(
        "The GUI is built with <b>PyQt6</b>. It must work for an absolute "
        "beginner. Every action must have a clear visual result. The terminal "
        "must never be visible to the user.",
        S["body"],
    ))
    story.append(sp(5))

    story.append(SubHeader("Color Theme", W))
    story.append(sp(4))

    color_rows = [
        ["Element",            "Color",    "Hex Code"],
        ["Window background",  "Dark Navy",      "#1a1a2e"],
        ["Panel background",   "Deep Blue",      "#16213e"],
        ["Buttons / Accent",   "Royal Blue",     "#0f3460"],
        ["Button hover",       "Crimson Red",    "#e94560"],
        ["Success indicator",  "Emerald Green",  "#00b894"],
        ["Error indicator",    "Coral Red",      "#e17055"],
        ["Gold accent bar",    "Amber Gold",     "#f0a500"],
        ["Table header",       "Royal Blue",     "#0f3460"],
        ["Text primary",       "White",          "#ffffff"],
        ["Text secondary",     "Slate Gray",     "#a0aec0"],
    ]

    color_extra = []
    swatch_colors = [
        None, NAVY, DARK_PANEL, ACCENT, HIGHLIGHT,
        GREEN, colors.HexColor("#e17055"), GOLD, ACCENT,
        WHITE, LIGHT_GRAY,
    ]
    story.append(info_table(color_rows, [4*cm, 3*cm, W - 7*cm]))
    story.append(sp(8))

    story.append(SubHeader("Main Window Layout", W))
    story.append(sp(4))

    layout_text = """\
┌─────────────────────────────────────────────────────────────┐
│  Bank Statement ETL Engine                    [─] [□] [✕]  │
├─────────────────────────────────────────────────────────────┤
│  SELECT BANK:   [▼ ABA Bank                          ]      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │   Drag & Drop your statement file here              │   │
│  │   or  [ Browse File ]                               │   │
│  │   Supported: .csv  .xls  .xlsx  .pdf                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [ ▶  Process Statement ]                                   │
│  ████████████░░░░  Transforming...  72%                     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  RESULTS — 145 transactions                                 │
│  ┌──────────┬───────────────────┬────────┬────────┬──────┐  │
│  │ Date     │ Description       │ Debit  │ Credit │ Bal  │  │
│  │ 01/01/25 │ Transfer In       │        │ 500.00 │ ...  │  │
│  │ 02/01/25 │ ATM Withdrawal    │ 100.00 │        │ ...  │  │
│  └──────────┴───────────────────┴────────┴────────┴──────┘  │
│  ✅ Exported → output/aba/2025/202501/USD/aba_202501_USD.xlsx│
│  [ 📁 Open Output Folder ]                                  │
└─────────────────────────────────────────────────────────────┘"""

    story.append(arch_box(layout_text, S, W, bg=NAVY, fg=WHITE))
    story.append(sp(10))
    story.append(PageBreak())

    # ── 11. Database Strategy ─────────────────────────────────────────────
    story.append(SectionHeader("11.  Database Strategy", W))
    story.append(sp(6))

    db_rows = [
        ["Phase",    "Database",    "Status",    "When"],
        ["Phase 1",  "SQLite",      "Active",    "Now — single file, no server needed"],
        ["Phase 2",  "PostgreSQL",  "Future",    "When volume or multi-user access requires it"],
    ]
    extra_db = [
        ("TEXTCOLOR", (2, 1), (2, 1), GREEN),
        ("TEXTCOLOR", (2, 2), (2, 2), GOLD),
        ("FONTNAME",  (2, 1), (2, 1), "Helvetica-Bold"),
    ]
    story.append(info_table(db_rows, [1.8*cm, 2.5*cm, 2*cm, W - 6.3*cm], extra_db))
    story.append(sp(6))

    schema_sql = """\
-- SQLite schema (database/bank_statements.db)

CREATE TABLE IF NOT EXISTS transactions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name        TEXT    NOT NULL,
    account_number   TEXT,
    account_name     TEXT,
    transaction_date DATE    NOT NULL,
    reference_id     TEXT,
    description      TEXT,
    debit_amount     REAL,
    credit_amount    REAL,
    balance          REAL,
    currency         TEXT    NOT NULL,
    source_file      TEXT,
    imported_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bank_name, transaction_date, reference_id, debit_amount, credit_amount)
);

-- INSERT OR IGNORE → re-processing same file never creates duplicates"""

    story.append(arch_box(schema_sql, S, W))
    story.append(sp(10))

    # ── 12. ABA Bank — Proof of Concept ──────────────────────────────────
    story.append(SectionHeader("12.  Bank ABA — Proof of Concept", W))
    story.append(sp(6))

    aba_rows = [
        ["Property",          "Value"],
        ["Bank Name",         "ABA Bank"],
        ["Country",           "Cambodia"],
        ["Engine ID",         "aba"],
        ["Source Folder",     "downloads/aba/"],
        ["Output Folder",     "output/aba/"],
        ["Common Currencies", "USD, KHR"],
        ["Status",            "Phase 1 — Active Development"],
    ]
    story.append(info_table(aba_rows, [4.5*cm, W - 4.5*cm]))
    story.append(sp(6))
    story.append(p(
        "<b>Before the ABA engine is built, the following must be confirmed "
        "by reviewing a real ABA bank statement file:</b>",
        S["body"],
    ))
    story.append(sp(4))

    checklist = [
        "Exact column headers as they appear in the source file",
        "File format ABA provides (CSV, XLSX, PDF — or multiple formats)",
        "Date format used (e.g. 01/01/2025 or 2025-01-01)",
        "Amount format: single column +/- or separate Debit/Credit columns",
        "Which row the data starts from (any header/summary rows to skip?)",
        "If XLSX: which sheet name contains the transaction data",
        "If PDF: does the column header repeat on every page?",
    ]
    for item in checklist:
        story.append(p(f"• {item}", S["bullet"]))
    story.append(sp(10))

    # ── 13. Scalability Plan ──────────────────────────────────────────────
    story.append(SectionHeader("13.  Scalability Plan — Up to 200 Banks", W))
    story.append(sp(6))
    story.append(p(
        "Adding a new bank requires editing <b>exactly one file</b> — the "
        "bank's own <b>config.py</b>. All other files are copied unchanged "
        "from the ABA template. The GUI, launcher, database, and output "
        "structure require zero changes.",
        S["body"],
    ))
    story.append(sp(5))

    steps_text = """\
How to add Bank #2 (and every bank after that):

Step 1 — Copy the template
   cp -r banks/aba/  banks/newbank/

Step 2 — Edit only config.py with the new bank's column names
   BANK_NAME  = "newbank"
   COLUMN_MAP = {
       "TransDate"  :  "transaction_date",
       "Details"    :  "description",
       "DR"         :  "debit_amount",
       "CR"         :  "credit_amount",
       ...
   }

Step 3 — Create the downloads folder
   mkdir downloads/newbank/

Step 4 — Done.
   The GUI auto-discovers the new bank and shows it in the dropdown.
   No changes to launcher.bat, gui/, other banks, or the database."""

    story.append(arch_box(steps_text, S, W))
    story.append(sp(10))
    story.append(PageBreak())

    # ── 14. Development Roadmap ───────────────────────────────────────────
    story.append(SectionHeader("14.  Development Roadmap", W))
    story.append(sp(6))

    roadmap = [
        ["Phase",     "Deliverable",                              "Status"],
        ["Phase 1",   "ABA standalone ETL engine (no GUI)",       "In Progress"],
        ["Phase 1",   "SQLite loader and schema",                 "Pending"],
        ["Phase 1",   "launcher.bat (CLI mode, no GUI yet)",      "Pending"],
        ["Phase 1",   "Test with real ABA statement files",       "Pending"],
        ["Phase 2",   "PyQt6 GUI — main window and bank selector","Pending"],
        ["Phase 2",   "File drop zone + process button",          "Pending"],
        ["Phase 2",   "Results table + open folder button",       "Pending"],
        ["Phase 2",   "Color theme applied",                      "Pending"],
        ["Phase 3",   "PyInstaller packaged executable",          "Pending"],
        ["Phase 4",   "Second bank added (pattern proof)",        "Pending"],
        ["Phase 4",   "PostgreSQL / Docker planning",             "Pending"],
        ["Phase 5",   "Banks 3 through N",                       "Future"],
        ["Phase 5",   "Reporting features in GUI",               "Future"],
    ]
    phase_colors = {
        "Phase 1": colors.HexColor("#0f3460"),
        "Phase 2": colors.HexColor("#005f73"),
        "Phase 3": colors.HexColor("#6a0572"),
        "Phase 4": colors.HexColor("#774936"),
        "Phase 5": colors.HexColor("#4a4e69"),
    }
    roadmap_extra = []
    for i, row in enumerate(roadmap[1:], start=1):
        bg = phase_colors.get(row[0], ACCENT)
        roadmap_extra.append(("BACKGROUND", (0, i), (0, i), bg))
        roadmap_extra.append(("TEXTCOLOR",  (0, i), (0, i), WHITE))
        roadmap_extra.append(("FONTNAME",   (0, i), (0, i), "Helvetica-Bold"))

    story.append(info_table(roadmap, [2*cm, W - 5.5*cm, 3.5*cm], roadmap_extra))
    story.append(sp(10))

    # ── 15. Glossary ──────────────────────────────────────────────────────
    story.append(SectionHeader("15.  Glossary", W))
    story.append(sp(6))

    glossary = [
        ["Term",         "Definition"],
        ["ETL",          "Extract, Transform, Load — the three-stage data processing pipeline"],
        ["Source File",  "Raw bank statement file received from the bank (any format)"],
        ["COLUMN_MAP",   "Dictionary in config.py mapping bank column names → standard names"],
        ["Venv",         "Python virtual environment — isolated Python + packages per bank"],
        ["XLSX",         "Microsoft Excel Open XML format — the output format for all statements"],
        ["KHR",          "Cambodian Riel — the local currency of Cambodia"],
        ["SQLite",       "Lightweight, serverless, file-based SQL database (Phase 1)"],
        ["PostgreSQL",   "Full-featured SQL database server, run in Docker (Phase 2)"],
        ["PyQt6",        "Python library for building professional desktop GUI applications"],
        ["subprocess",   "Python mechanism to run one program from inside another"],
        ["Upsert",       "Insert a record if it does not exist; skip if it already exists"],
        ["Drop Zone",    "GUI area where you drag and drop a file to process it"],
        ["launcher.bat", "The single Windows batch file the user double-clicks to start the app"],
    ]
    story.append(info_table(glossary, [3*cm, W - 3*cm]))
    story.append(sp(12))

    # ── Footer note ───────────────────────────────────────────────────────
    story.append(hr(HIGHLIGHT, thickness=1.5))
    story.append(sp(4))
    story.append(p(
        "<i>This document is the authoritative reference for all design and "
        "implementation decisions. When in doubt about any aspect of the "
        "system, refer to this document. When a decision is made that "
        "contradicts or extends this document, update this document first. "
        "<b>Last Updated: 2026-06-21</b></i>",
        S["body"],
    ))

    return story


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    output_path = "PRD.pdf"

    doc = BaseDocTemplate(
        output_path,
        pagesize=A4,
        title="Bank Statement ETL Engine — PRD",
        author="channa.meng",
        subject="Product Requirements Document v1.0",
    )

    # Cover page template — full bleed, no margins
    cover_frame = Frame(0, 0, PAGE_W, PAGE_H,
                        leftPadding=0, bottomPadding=0,
                        rightPadding=0, topPadding=0,
                        id="cover")
    cover_tpl = PageTemplate(id="cover", frames=[cover_frame])

    # Content page template — with header/footer
    content_frame = Frame(
        MARGIN, MARGIN + 12*mm,
        PAGE_W - 2*MARGIN, PAGE_H - 2*MARGIN - 26*mm,
        id="content",
    )
    content_tpl = PageTemplate(id="content", frames=[content_frame],
                                onPage=header_footer)

    doc.addPageTemplates([cover_tpl, content_tpl])

    styles = build_styles()
    story  = build_story(styles)

    doc.build(story)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    main()
