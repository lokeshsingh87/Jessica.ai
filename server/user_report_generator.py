# Copyright (c) 2026 Zoro - Legal Auditor RL Project
"""
user_report_generator.py
User-facing Document Analysis Summary PDF.

Design principles:
  • White page background — easy on the eyes, printer-friendly
  • Two accent colours only: RED for flagged risk, BLUE for cleared safe
  • No text truncation — clause text chunked into multi-row tables (crash-safe)
  • Distinct from oracle PDF — no reward values exposed anywhere:
      _build_trajectory  → accumulates ai_grade, not reward
      Cover pill         → AVG AI CONFIDENCE SCORE (0.0–1.0), not RL reward sum
      Trajectory log     → AI GRADE column, not REWARD column
      Clause card header → ai_grade decimal, not reward pts
"""
import io
from typing import List, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)

# ─────────────────────────────────────────────────────────────────────────────
# PALETTE  — light theme, two accent colours
# ─────────────────────────────────────────────────────────────────────────────
C_DARK   = colors.HexColor("#0F172A")   # header bars / dark text
C_BLUE   = colors.HexColor("#2563EB")   # CLEARED accent
C_BLUE_L = colors.HexColor("#EFF6FF")   # CLEARED card tint
C_RED    = colors.HexColor("#DC2626")   # FLAGGED accent
C_RED_L  = colors.HexColor("#FEF2F2")   # FLAGGED card tint
C_AMBER  = colors.HexColor("#D97706")   # medium grade / warning
C_AMBER_L= colors.HexColor("#FFFBEB")
C_GREEN  = colors.HexColor("#16A34A")   # high grade
C_BORDER = colors.HexColor("#E2E8F0")   # card borders
C_MUTED  = colors.HexColor("#64748B")   # secondary text
C_TEXT   = colors.HexColor("#1E293B")   # primary body text
C_WHITE  = colors.white


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _x(text: str) -> str:
    """XML-escape for Paragraph — no truncation."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _grade_color(g: float) -> colors.Color:
    return C_GREEN if g >= 0.7 else (C_AMBER if g >= 0.5 else C_RED)


def _grade_str(g: float) -> str:
    """Format ai_grade as a clean 4-decimal string."""
    return f"{g:.4f}"


# ─────────────────────────────────────────────────────────────────────────────
# TRAJECTORY BUILDER
# Change 1 of 4: accumulate ai_grade (running average), not reward sum.
# "cumulative" now means average ai_grade across steps seen so far (0.0–1.0).
# The reward field is intentionally dropped — it belongs to the oracle PDF.
# ─────────────────────────────────────────────────────────────────────────────
def _build_trajectory(audit_data: List[Dict]) -> List[Dict]:
    """
    Build per-step display data for the trajectory log.

    cumulative = running average of ai_grade up to this step.
    This is a completely different number from the oracle PDF's reward sum —
    it lives on the 0.0–1.0 scale and represents AI confidence, not RL reward.
    """
    grade_sum = 0.0
    out = []
    for i, item in enumerate(audit_data):
        grade     = float(item.get("ai_grade", 0.5))
        grade_sum += grade
        avg_grade = round(grade_sum / (i + 1), 4)
        action    = int(item.get("action", 0))
        out.append({
            "step":       i + 1,
            "ai_grade":   grade,        # this step's grade
            "cumulative": avg_grade,    # running average — NOT reward sum
            "opinion":    "FLAGGED" if action == 1 else "CLEARED",
        })
    return out


# ─────────────────────────────────────────────────────────────────────────────
# PARAGRAPH STYLE FACTORY
# ─────────────────────────────────────────────────────────────────────────────
def _p(name, size=9.0,color=C_TEXT, bold=False, align:Any=TA_LEFT,
       leading=None, mono=False) -> ParagraphStyle:
    font = ("Courier-Bold"   if (mono and bold) else
            "Courier"        if mono else
            "Helvetica-Bold" if bold else "Helvetica")
    return ParagraphStyle(name, fontName=font, fontSize=size,
                          textColor=color, leading=leading or size + 4,
                          alignment=align)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE DECORATOR
# ─────────────────────────────────────────────────────────────────────────────
def _decorator(session_id: str, flagged: int, cleared: int):
    def draw(canvas, doc):
        W, H = A4
        canvas.saveState()
        canvas.setFillColor(C_DARK)
        canvas.rect(0, H - 20, W, 20, fill=1, stroke=0)
        canvas.setFillColor(C_WHITE)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawString(18, H - 13, "LEGAL AUDITOR  —  Document Analysis Report")
        canvas.setFont("Courier", 7)
        canvas.drawRightString(W - 18, H - 13, f"SESSION  {session_id.upper()}")
        canvas.setStrokeColor(C_BLUE)
        canvas.setLineWidth(2)
        canvas.line(0, H - 21, W, H - 21)
        canvas.setStrokeColor(C_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(18, 20, W - 18, 20)
        canvas.setFillColor(C_MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(
            W / 2, 10,
            f"Page {doc.page}  |  {flagged} Flagged  ·  {cleared} Cleared  "
            f"|  Zoro Legal Auditor 2026"
        )
        canvas.restoreState()
    return draw


# ─────────────────────────────────────────────────────────────────────────────
# COVER
# Change 2 of 4: sigma pill replaced with AVG AI CONFIDENCE SCORE.
# Value = traj[-1]["cumulative"] which is now avg ai_grade (0.0–1.0).
# Label and color logic updated to match the new 0–1 scale.
# ─────────────────────────────────────────────────────────────────────────────
def _cover(audit_data: List[Dict], traj: List[Dict],
           session_id: str, cw: float) -> List:

    avg_grade = traj[-1]["cumulative"] if traj else 0.0
    flagged   = sum(1 for d in traj if d["opinion"] == "FLAGGED")
    cleared   = len(traj) - flagged
    grade     = float(audit_data[-1].get("ai_grade", 0)) if audit_data else 0.0
    ts        = (audit_data[0].get("timestamp", "")[:19].replace("T", " ")
                 if audit_data else "—")

    story = []

    # Title banner
    banner = Table([[
        Paragraph("Document Analysis Report",
                  _p("bt", size=16, color=C_WHITE, bold=True)),
        Paragraph(f"Session: {session_id.upper()}<br/>{ts}",
                  _p("bm", size=8, color=colors.HexColor("#94A3B8"),
                     mono=True, align=TA_RIGHT)),
    ]], colWidths=[cw * 0.6, cw * 0.4])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_DARK),
        ("TOPPADDING",    (0,0),(-1,-1), 16),
        ("BOTTOMPADDING", (0,0),(-1,-1), 16),
        ("LEFTPADDING",   (0,0),(-1,-1), 18),
        ("RIGHTPADDING",  (0,0),(-1,-1), 18),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LINEBELOW",     (0,0),(-1,-1), 3, C_BLUE),
    ]))
    story.append(banner)
    story.append(Spacer(1, 12))

    # ── AVG AI CONFIDENCE SCORE pill (was: RL CONVERGENCE SCORE) ─────────
    # avg_grade lives on 0.0–1.0 — completely different scale from oracle PDF.
    conf_color = _grade_color(avg_grade)
    conf_tbl = Table([[
        Paragraph("AVG AI CONFIDENCE SCORE",
                  _p("sl", size=8, color=C_MUTED, bold=True)),
        Paragraph(_grade_str(avg_grade),
                  _p("sv", size=18, color=conf_color, bold=True,
                     mono=True, align=TA_RIGHT)),
    ]], colWidths=[cw * 0.6, cw * 0.4])
    conf_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#F8FAFC")),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ("LEFTPADDING",   (0,0),(-1,-1), 16),
        ("RIGHTPADDING",  (0,0),(-1,-1), 16),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BOX",           (0,0),(-1,-1), 1, C_BORDER),
        ("LINEABOVE",     (0,0),(-1,0),  2, C_BLUE),
    ]))
    story.append(conf_tbl)
    story.append(Spacer(1, 8))

    # Stat cards — 4 cards (TOTAL / FLAGGED / CLEARED / AI GRADE)
    def card(val, lbl, vc=C_TEXT):
        return Table(
            [[Paragraph(str(val), _p("cv", size=20, color=vc, bold=True,
                                     align=TA_CENTER))],
             [Paragraph(lbl,      _p("cl", size=7,  color=C_MUTED,
                                     align=TA_CENTER))]],
            colWidths=[(cw / 4) - 3],
            style=TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), C_WHITE),
                ("TOPPADDING",    (0,0),(-1,-1), 10),
                ("BOTTOMPADDING", (0,0),(-1,-1), 10),
                ("BOX",           (0,0),(-1,-1), 1, C_BORDER),
            ])
        )

    cards = Table([[
        card(len(traj),             "TOTAL CLAUSES"),
        card(flagged,               "FLAGGED",  C_RED),
        card(cleared,               "CLEARED",  C_BLUE),
        card(f"{int(grade*100)}%",  "AI GRADE", _grade_color(grade)),
    ]], colWidths=[(cw / 4) - 2] * 4)
    cards.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0),(-1,-1), 1.5),
        ("RIGHTPADDING", (0,0),(-1,-1), 1.5),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(cards)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=C_BORDER, spaceBefore=2, spaceAfter=10))
    return story


# ─────────────────────────────────────────────────────────────────────────────
# TRAJECTORY LOG
# Change 3 of 4: REWARD column → AI GRADE column.
# Values are now ai_grade decimals (e.g. 0.4462) not reward pts (e.g. -76.89).
# Row tinting based on grade threshold instead of match/mismatch.
# ─────────────────────────────────────────────────────────────────────────────
def _trajectory_log(audit_data: List[Dict], traj: List[Dict], cw: float) -> List:
    story = []

    story.append(Table([[
        Paragraph("INFERENCE TRAJECTORY LOG",
                  _p("tl", size=9, color=C_BLUE, bold=True)),
    ]], colWidths=[cw], style=TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_BLUE_L),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("LINEABOVE",     (0,0),(-1,0),  2, C_BLUE),
        ("LINEBELOW",     (0,0),(-1,-1), 1, C_BORDER),
    ])))
    story.append(Spacer(1, 4))

    # Columns: STEP | AI DECISION | AI GRADE | CLAUSE PREVIEW
    col_w = [32, 68, 68, cw - 32 - 68 - 68]

    def hdr(t):
        return Paragraph(t, _p("th", size=7, color=C_MUTED, bold=True,
                               align=TA_CENTER))

    rows    = [[hdr("STEP"), hdr("AI DECISION"),
                hdr("AI GRADE"), hdr("CLAUSE PREVIEW")]]
    tstyles = [
        ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor("#F1F5F9")),
        ("GRID",          (0,0),(-1,-1), 0.4, C_BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]

    for d in reversed(traj):
        idx     = d["step"] - 1
        opinion = d["opinion"]
        grade   = d["ai_grade"]          # per-step ai_grade — not reward
        gc      = _grade_color(grade)
        o_color = C_RED  if opinion == "FLAGGED" else C_BLUE
        preview = (audit_data[idx].get("text", "")
                   if idx < len(audit_data) else "")
        # Row bg: green tint for high confidence, amber for medium, red-tint for low
        row_bg  = (colors.HexColor("#F0FDF4") if grade >= 0.7 else
                   C_AMBER_L                   if grade >= 0.5 else
                   C_RED_L)

        rows.append([
            Paragraph(f"#{str(d['step']).zfill(3)}",
                      _p("rs", size=9, color=C_MUTED, mono=True, align=TA_CENTER)),
            Paragraph(f"<b>{opinion}</b>",
                      _p("ro", size=9, color=o_color, bold=True, align=TA_CENTER)),
            Paragraph(f"<b>{_grade_str(grade)}</b>",
                      _p("rg", size=8, color=gc, mono=True, align=TA_CENTER)),
            Paragraph(_x(preview[:150] + ("…" if len(preview) > 150 else "")),
                      _p("rp", size=7.5, color=C_MUTED)),
        ])
        r = len(rows) - 1
        tstyles.append(("BACKGROUND", (0,r),(-1,r), row_bg))
        tstyles.append(("LINEBEFORE", (0,r),(0,r),  2, o_color))

    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle(tstyles))
    story.append(tbl)
    story.append(Spacer(1, 14))
    return story


# ─────────────────────────────────────────────────────────────────────────────
# CLAUSE TEXT CHUNKER — prevents LayoutError on long clauses
# ─────────────────────────────────────────────────────────────────────────────
_CHUNK_WORDS = 50


def _chunk_rows(text: str, para_style: ParagraphStyle) -> List[List]:
    words = text.split()
    if not words:
        return [[Paragraph("—", para_style)]]
    rows = []
    for i in range(0, len(words), _CHUNK_WORDS):
        chunk = " ".join(words[i: i + _CHUNK_WORDS])
        rows.append([Paragraph(_x(chunk), para_style)])
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE CLAUSE CARD
# Change 4 of 4: top-right header value changed from reward pts → ai_grade.
# Was: "-76.89 pts" (raw RL reward — oracle concept)
# Now: "0.4462"     (ai_grade decimal — user-facing confidence score)
# ─────────────────────────────────────────────────────────────────────────────
def _clause_card(entry: Dict, step: int, accent: colors.Color,
                 tint: colors.Color, cw: float) -> List:

    action  = int(entry.get("action", 0))
    text    = str(entry.get("text", ""))
    warning = str(entry.get("warning", "—"))
    diff    = str(entry.get("difficulty", "medium")).upper()
    grade   = float(entry.get("ai_grade", 0.5))

    opinion   = "FLAGGED" if action == 1 else "CLEARED"
    diff_c    = {"EASY": C_BLUE, "MEDIUM": C_AMBER, "HARD": C_RED}.get(diff, C_MUTED)
    grade_pct = int(grade * 100)
    gc        = _grade_color(grade)
    filled    = round(grade_pct / 5)
    bar       = "█" * filled + "░" * (20 - filled)

    # ── BLOCK 1: Header — step · opinion · difficulty · AI GRADE ─────────
    # Top-right now shows ai_grade decimal, not reward pts.
    header_tbl = Table([[
        Paragraph(f"#{str(step).zfill(3)}",
                  _p("ch", size=8, color=C_MUTED, mono=True)),
        Paragraph(f"<b>{opinion}</b>",
                  _p("co", size=11, color=accent, bold=True)),
        Paragraph(f"<b>{diff}</b>",
                  _p("cd", size=8, color=diff_c, bold=True, align=TA_CENTER)),
        Paragraph(
            f'<font color="{gc.hexval()}"><b>{_grade_str(grade)}</b></font>',
            _p("cg", size=10, color=gc, bold=True, mono=True, align=TA_RIGHT)),
    ]], colWidths=[34, cw - 34 - 64 - 74, 64, 74])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_WHITE),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LINEABOVE",     (0,0),(-1,0),  1.5, accent),
        ("LINEBEFORE",    (0,0),(0,-1),  1.5, accent),
        ("LINEAFTER",     (-1,0),(-1,-1),1.5, accent),
    ]))
    header_tbl.keepWithNext = True

    # ── BLOCK 2: Clause text — chunked multi-row (crash-safe) ────────────
    clause_style = _p("ctb", size=9, color=C_TEXT, leading=15)
    clause_tbl   = Table(_chunk_rows(text, clause_style), colWidths=[cw])
    clause_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), tint),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("LINEBEFORE",    (0,0),(0,-1),  1.5, accent),
        ("LINEAFTER",     (-1,0),(-1,-1),1.5, accent),
        ("TOPPADDING",    (0,0),(-1,0),  8),
        ("BOTTOMPADDING", (0,-1),(-1,-1),8),
    ]))
    clause_tbl.keepWithNext = True

    # ── BLOCK 3: AI Analysis — chunked ───────────────────────────────────
    warn_style = _p("ab", size=8.5, color=C_TEXT, leading=13)
    warn_rows  = _chunk_rows(warning, warn_style)
    label_col_w = 72
    ai_rows = (
        [[Paragraph("AI ANALYSIS", _p("al", size=7, color=accent, bold=True)),
          warn_rows[0][0]]]
        + [[Paragraph(""), row[0]] for row in warn_rows[1:]]
    )
    ai_tbl = Table(ai_rows, colWidths=[label_col_w, cw - label_col_w])
    ai_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_WHITE),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("LINEABOVE",     (0,0),(-1,0),  0.5, C_BORDER),
        ("LINEBEFORE",    (0,0),(0,-1),  1.5, accent),
        ("LINEAFTER",     (-1,0),(-1,-1),1.5, accent),
        ("TOPPADDING",    (0,0),(-1,0),  8),
        ("BOTTOMPADDING", (0,-1),(-1,-1),8),
    ]))
    ai_tbl.keepWithNext = True

    # ── BLOCK 4: Grade bar ────────────────────────────────────────────────
    bar_tbl = Table([[
        Paragraph("CUMULATIVE AI GRADE:",
                  _p("gl", size=7, color=C_MUTED, bold=True)),
        Paragraph(f'<font color="{gc.hexval()}"><b>{bar}  {grade_pct}%</b></font>',
                  _p("gb", size=7.5, color=gc, mono=True, align=TA_RIGHT)),
    ]], colWidths=[cw * 0.30, cw * 0.70])
    bar_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_WHITE),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LINEBELOW",     (0,0),(-1,-1), 1.5, accent),
        ("LINEBEFORE",    (0,0),(0,-1),  1.5, accent),
        ("LINEAFTER",     (-1,0),(-1,-1),1.5, accent),
    ]))

    return [header_tbl, clause_tbl, ai_tbl, bar_tbl, Spacer(1, 12)]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION BANNER
# ─────────────────────────────────────────────────────────────────────────────
def _section_banner(label: str, count: int,
                    accent: colors.Color, tint: colors.Color, cw: float) -> Table:
    return Table([[
        Paragraph(f"<b>{label}</b>",
                  _p("sb", size=10, color=accent, bold=True)),
        Paragraph(f"<b>{count} clause{'s' if count != 1 else ''}</b>",
                  _p("sc", size=10, color=accent, bold=True, align=TA_RIGHT)),
    ]], colWidths=[cw * 0.75, cw * 0.25],
    style=TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), tint),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LINEABOVE",     (0,0),(-1,0),  2.5, accent),
        ("LINEBELOW",     (0,0),(-1,-1), 0.5, C_BORDER),
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────
def generate_user_report_pdf(audit_data: List[Dict[str, Any]],
                              session_id: str) -> bytes:
    """
    Build the user-facing Document Analysis Summary PDF and return raw bytes.

    Sections:
      1. Cover              — title, AVG AI CONFIDENCE SCORE, 4 stat cards
      2. Trajectory Log     — per-step: step / AI DECISION / AI GRADE / preview
      3. Flagged Clauses    — risks the AI detected, with ai_grade on each card
      4. Cleared Clauses    — safe clauses, with ai_grade on each card

    No reward values appear anywhere in this PDF.
    """
    if not audit_data:
        raise ValueError("audit_data is empty.")

    buf    = io.BytesIO()
    W, H   = A4
    margin = 20 * mm

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=26, bottomMargin=30,
    )

    cw   = W - 2 * margin
    traj = _build_trajectory(audit_data)

    flagged_entries = [e for e in audit_data if int(e.get("action", 0)) == 1]
    cleared_entries = [e for e in audit_data if int(e.get("action", 0)) == 0]

    story: List = []

    story.extend(_cover(audit_data, traj, session_id, cw))
    story.extend(_trajectory_log(audit_data, traj, cw))
    story.append(PageBreak())

    # Flagged
    story.append(_section_banner(
        "FLAGGED CLAUSES  —  Risks Identified by AI",
        len(flagged_entries), C_RED, C_RED_L, cw))
    story.append(Spacer(1, 8))
    if flagged_entries:
        for e in flagged_entries:
            story.extend(_clause_card(
                e, int(e.get("clause_index", 0)) + 1, C_RED, C_RED_L, cw))
    else:
        story.append(Table([[Paragraph(
            "No risks flagged — AI cleared all clauses in this document.",
            _p("nf", size=9, color=C_BLUE))]],
            colWidths=[cw], style=TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), C_BLUE_L),
                ("TOPPADDING",    (0,0),(-1,-1), 12),
                ("BOTTOMPADDING", (0,0),(-1,-1), 12),
                ("LEFTPADDING",   (0,0),(-1,-1), 14),
                ("RIGHTPADDING",  (0,0),(-1,-1), 14),
                ("BOX",           (0,0),(-1,-1), 0.5, C_BORDER),
            ])))

    story.append(Spacer(1, 16))

    # Cleared
    story.append(_section_banner(
        "CLEARED CLAUSES  —  Safe Clauses Identified by AI",
        len(cleared_entries), C_BLUE, C_BLUE_L, cw))
    story.append(Spacer(1, 8))
    if cleared_entries:
        for e in cleared_entries:
            story.extend(_clause_card(
                e, int(e.get("clause_index", 0)) + 1, C_BLUE, C_BLUE_L, cw))
    else:
        story.append(Table([[Paragraph(
            "No clauses cleared — AI flagged every clause in this document.",
            _p("nc", size=9, color=C_RED))]],
            colWidths=[cw], style=TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), C_RED_L),
                ("TOPPADDING",    (0,0),(-1,-1), 12),
                ("BOTTOMPADDING", (0,0),(-1,-1), 12),
                ("LEFTPADDING",   (0,0),(-1,-1), 14),
                ("RIGHTPADDING",  (0,0),(-1,-1), 14),
                ("BOX",           (0,0),(-1,-1), 0.5, C_BORDER),
            ])))

    dec = _decorator(session_id, len(flagged_entries), len(cleared_entries))
    doc.build(story, onFirstPage=dec, onLaterPages=dec)
    return buf.getvalue()