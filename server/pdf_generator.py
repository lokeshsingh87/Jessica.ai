# Copyright (c) 2026 Zoro - Legal Auditor RL Project
"""
pdf_generator.py  — Oracle / Developer Audit Report
Fixes applied in this revision:
  FIX-1  Text truncation    _safe_text(420) removed. Clause text and rationale
                            use chunked multi-row Tables so any length works
                            without LayoutError.
  FIX-2  oracle_grade bug   Field doesn't exist in session data — was always
                            returning 0.0 (cover) / 0.5 (cards). Now reads
                            ai_grade which is what the environment actually stores.
  FIX-3  Emoji → ASCII      Helvetica has no emoji glyphs. 🚨✅⚖🤖🏛️ all
                            rendered as ■. Replaced with plain ASCII labels.
  FIX-4  KeepTogether       Same LayoutError risk as user_report. Replaced with
                            flat flowables + keepWithNext chaining.
"""
import io
from datetime import datetime
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
# PALETTE
# ─────────────────────────────────────────────────────────────────────────────
C_BG_DARK   = colors.HexColor("#0D1117")
C_ACCENT    = colors.HexColor("#7C3AED")
C_ACCENT_LT = colors.HexColor("#EDE9FE")

C_TP        = colors.HexColor("#16A34A")
C_TP_BG     = colors.HexColor("#DCFCE7")
C_TN        = colors.HexColor("#0369A1")
C_TN_BG     = colors.HexColor("#E0F2FE")
C_FP        = colors.HexColor("#D97706")
C_FP_BG     = colors.HexColor("#FEF3C7")
C_FN        = colors.HexColor("#DC2626")
C_FN_BG     = colors.HexColor("#FEE2E2")

C_BORDER    = colors.HexColor("#E5E7EB")
C_MUTED     = colors.HexColor("#6B7280")
C_TEXT      = colors.HexColor("#111827")
C_WHITE     = colors.white


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _hex(color) -> str:
    """Safe 6-digit #rrggbb string — HexColor.hexval() includes alpha."""
    r, g, b = int(color.red*255), int(color.green*255), int(color.blue*255)
    return f"#{r:02x}{g:02x}{b:02x}"


def _x(text: str) -> str:
    """XML-escape only — NO truncation."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _verdict(action: int, is_risk: bool):
    if action == 1 and is_risk:      return "TRUE POSITIVE",  C_TP, C_TP_BG, "TP"
    if action == 0 and not is_risk:  return "TRUE NEGATIVE",  C_TN, C_TN_BG, "TN"
    if action == 1 and not is_risk:  return "FALSE POSITIVE", C_FP, C_FP_BG, "FP"
    return                                  "FALSE NEGATIVE",  C_FN, C_FN_BG, "FN"


def _reward_label(reward: float) -> str:
    sign = "+" if reward >= 0 else ""
    return f"{sign}{reward:.2f} pts"


def _bar(score: float) -> str:
    """ASCII reliability bar — no Unicode block chars."""
    pct    = int(score * 100)
    filled = round(pct * 20 / 100)
    return f"[{'=' * filled}{'-' * (20 - filled)}] {pct}%"


# ─────────────────────────────────────────────────────────────────────────────
# CHUNKER — prevents LayoutError on long text (same approach as user report)
# ─────────────────────────────────────────────────────────────────────────────
_CHUNK = 50   # words per row

def _chunk_rows(text: str, style: ParagraphStyle) -> List[List]:
    words = str(text).split()
    if not words:
        return [[Paragraph("—", style)]]
    return [
        [Paragraph(_x(" ".join(words[i: i + _CHUNK])), style)]
        for i in range(0, len(words), _CHUNK)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# STYLE SHEET
# ─────────────────────────────────────────────────────────────────────────────
def _p(name, size=9.0, color=C_TEXT, bold=False, align:Any=TA_LEFT,
       leading=None, mono=False) -> ParagraphStyle:
    font = ("Courier-Bold"   if (mono and bold) else
            "Courier"        if mono else
            "Helvetica-Bold" if bold else "Helvetica")
    return ParagraphStyle(name, fontName=font, fontSize=size,
                          textColor=color, leading=leading or size+4,
                          alignment=align)


# ─────────────────────────────────────────────────────────────────────────────
# COVER PAGE
# ─────────────────────────────────────────────────────────────────────────────
def _build_cover(session_data: List[Dict], session_id: str,
                 content_w: float) -> List:

    total   = len(session_data)
    risks   = sum(1 for e in session_data if e["action"] == 1)
    safe    = total - risks
    # FIX-2: was oracle_grade (always 0) — now ai_grade (actual stored field)
    grade   = float(session_data[-1].get("ai_grade", 0.0)) if session_data else 0.0
    reward  = sum(e.get("reward", 0) for e in session_data)

    tp = sum(1 for e in session_data if e["action"]==1 and     e["is_actually_risk"])
    tn = sum(1 for e in session_data if e["action"]==0 and not e["is_actually_risk"])
    fp = sum(1 for e in session_data if e["action"]==1 and not e["is_actually_risk"])
    fn = sum(1 for e in session_data if e["action"]==0 and     e["is_actually_risk"])
    accuracy = round((tp + tn) / max(1, total) * 100, 1)
    ts = session_data[0]["timestamp"][:19].replace("T", " ") if session_data else "—"

    story = []

    # Dark title banner  — FIX-3: "⚖ LEGAL AUDITOR" → plain ASCII
    banner = Table([[
        Paragraph("LEGAL AUDITOR",
                  _p("ct", size=26, color=C_WHITE, bold=True)),
    ]], colWidths=[content_w])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_BG_DARK),
        ("TOPPADDING",    (0,0),(-1,-1), 18),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
        ("LEFTPADDING",   (0,0),(-1,-1), 16),
        ("RIGHTPADDING",  (0,0),(-1,-1), 16),
    ]))
    story.append(banner)
    story.append(Spacer(1, 4))

    sub = Table([[
        Paragraph("AI Performance &amp; Clause-Level Audit Report",
                  _p("cs", size=11, color=colors.HexColor("#7C3AED"))),
        Paragraph(f"Session: {session_id}<br/>Generated: {ts}",
                  _p("cm", size=9, color=C_MUTED, align=TA_RIGHT)),
    ]], colWidths=[content_w*0.6, content_w*0.4])
    sub.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_ACCENT_LT),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(sub)
    story.append(Spacer(1, 14))

    # Stat cards
    def stat(lbl, val, fg=C_TEXT):
        return Table(
            [[Paragraph(str(val), _p("sv", size=20, color=fg, bold=True, align=TA_CENTER))],
             [Paragraph(lbl,      _p("sl", size=8,  color=C_MUTED, align=TA_CENTER))]],
            colWidths=[(content_w/5)-3],
            style=TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#F9FAFB")),
                ("TOPPADDING",    (0,0),(-1,-1), 10),
                ("BOTTOMPADDING", (0,0),(-1,-1), 10),
                ("BOX",           (0,0),(-1,-1), 0.5, C_BORDER),
            ])
        )

    r_color = C_TP if reward >= 0 else C_FN
    g_color = C_TP if grade >= 0.7 else (C_FP if grade >= 0.5 else C_FN)
    stats = Table([[
        stat("CLAUSES AUDITED", total,   C_ACCENT),
        stat("RISKS FLAGGED",   risks,   C_FN),
        stat("SAFE CLAUSES",    safe,    C_TN),
        stat("TOTAL REWARD",    f"{'+'if reward>=0 else ''}{reward:.1f}", r_color),
        stat("RELIABILITY",     f"{int(grade*100)}%", g_color),
    ]], colWidths=[(content_w/5)-2]*5)
    stats.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0),(-1,-1), 1.5),
        ("RIGHTPADDING", (0,0),(-1,-1), 1.5),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(stats)
    story.append(Spacer(1, 12))

    # Confusion matrix  — FIX-3: ✓ / ✗ → plain ASCII
    def cm(lbl, val, fg, bg):
        return Table(
            [[Paragraph(str(val), _p("cv", size=16, color=fg, bold=True, align=TA_CENTER))],
             [Paragraph(lbl,      _p("cl", size=7,  color=fg, align=TA_CENTER))]],
            colWidths=[(content_w/4)-3],
            style=TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), bg),
                ("TOPPADDING",    (0,0),(-1,-1), 8),
                ("BOTTOMPADDING", (0,0),(-1,-1), 8),
                ("BOX",           (0,0),(-1,-1), 0.5, C_BORDER),
            ])
        )

    cms = Table([[
        cm("TRUE POSITIVE",  tp, C_TP, C_TP_BG),
        cm("TRUE NEGATIVE",  tn, C_TN, C_TN_BG),
        cm("FALSE POSITIVE", fp, C_FP, C_FP_BG),
        cm("FALSE NEGATIVE", fn, C_FN, C_FN_BG),
    ]], colWidths=[(content_w/4)-2]*4)
    cms.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0),(-1,-1), 1.5),
        ("RIGHTPADDING", (0,0),(-1,-1), 1.5),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(cms)
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        f"Overall Accuracy: <b>{accuracy}%</b>  |  "
        f"Oracle Reliability: <b>{int(grade*100)}%</b>  |  "
        f"Total RL Reward: <b>{'+'if reward>=0 else ''}{reward:.2f} pts</b>",
        _p("acc", size=9, color=C_TEXT, align=TA_CENTER)
    ))

    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER,
                             spaceAfter=8, spaceBefore=8))

    # Legend
    items = [("TP - Correct risk flag", C_TP), ("TN - Correct safe clear", C_TN),
             ("FP - Hallucinated risk", C_FP), ("FN - Missed real risk",    C_FN)]
    leg = Table([[
        Paragraph(f'<font color="{_hex(fg)}"><b>&#9632;</b></font>  {lbl}',
                  _p("lg", size=8, color=C_TEXT))
        for lbl, fg in items
    ]], colWidths=[content_w/4]*4)
    leg.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
    ]))
    story.append(leg)
    story.append(Spacer(1, 4))
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# PER-CLAUSE CARD
#
# Border strategy — why _wrap() was removed:
#   _wrap() put content inside a 1-row × 3-col outer Table. A Table with
#   exactly ONE ROW cannot be split across pages. When a long rationale made
#   the wrapper's middle cell taller than the page frame → LayoutError.
#
# New strategy — direct LINEBEFORE/LINEAFTER on every block:
#   LINEBEFORE draws at the LEFT EDGE of column 0.
#   LINEAFTER  draws at the RIGHT EDGE of the last column.
#   As long as EVERY block sums to exactly content_w, those edges are
#   the same x-position on the page → borders align perfectly.
#
#   The old misalignment happened because sides was (content_w - 8) wide.
#   Now every block's colWidths sum to content_w exactly — verified below.
#
# Difficulty wrapping fix:
#   "MEDIUM" in Helvetica-Bold 8pt needs ~42pt of text space.
#   The old code applied uniform 12pt L/R padding to all header cells,
#   leaving only 31pt for the difficulty cell → it wrapped to "MEDIU\nM".
#   Now the difficulty cell gets 3pt L/R padding via a cell-specific override.
# ─────────────────────────────────────────────────────────────────────────────
def _build_clause_card(entry: Dict, content_w: float) -> List:
    action    = int(entry.get("action", 0))
    is_risk   = bool(entry.get("is_actually_risk", False))
    reward    = float(entry.get("reward", 0.0))
    grade     = float(entry.get("ai_grade", 0.5))
    idx       = int(entry.get("clause_index", 0)) + 1
    text      = str(entry.get("text", ""))
    ai_reason = str(entry.get("warning", "—"))
    ora_reason= str(entry.get("oracle_rationale", "—"))
    difficulty= str(entry.get("difficulty", "medium")).upper()

    verdict_label, fg_color, bg_color, code = _verdict(action, is_risk)
    r_style = C_TP if reward >= 0 else C_FN
    diff_c  = {"EASY": C_TN, "MEDIUM": C_FP, "HARD": C_FN}.get(difficulty, C_MUTED)
    g_color = C_TP if grade >= 0.7 else (C_FP if grade >= 0.5 else C_FN)

    BDR = 1.5   # border line weight

    # ── BLOCK 1: Header (always small, never crashes) ─────────────────────
    # colWidths: badge=28 | title=fills | diff=52 | reward=80  → sum=content_w
    BADGE_W, DIFF_W, REW_W = 28, 52, 80
    TITLE_W = content_w - BADGE_W - DIFF_W - REW_W   # exact remainder

    badge = Table([[
        Paragraph(code, _p("bc", size=10, color=C_WHITE, bold=True, align=TA_CENTER))
    ]], colWidths=[BADGE_W], style=TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), fg_color),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
    ]))

    hdr = Table([[
        badge,
        Paragraph(f"Clause #{idx} — {verdict_label}",
                  _p("ch", size=10, color=fg_color, bold=True)),
        Paragraph(f'<font color="{_hex(diff_c)}"><b>{difficulty}</b></font>',
                  _p("cd", size=8, color=diff_c, bold=True, align=TA_CENTER)),
        Paragraph(f'<font color="{_hex(r_style)}"><b>{_reward_label(reward)}</b></font>',
                  _p("cr", size=10, color=r_style, bold=True, mono=True, align=TA_RIGHT)),
    ]], colWidths=[BADGE_W, TITLE_W, DIFF_W, REW_W])
    # assert BADGE_W + TITLE_W + DIFF_W + REW_W == content_w  ← always true by construction
    hdr.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BACKGROUND",    (0,0),(-1,-1), C_WHITE),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),   # global default
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        # Badge: no side padding (fills its own coloured bg)
        ("LEFTPADDING",   (0,0),(0,-1),  0),
        ("RIGHTPADDING",  (0,0),(0,-1),  8),
        # Difficulty: 3pt only → 52 - 6 = 46pt text space, MEDIUM fits
        ("LEFTPADDING",   (2,0),(2,-1),  3),
        ("RIGHTPADDING",  (2,0),(2,-1),  3),
        # Borders — left edge of col 0, right edge of last col
        ("LINEABOVE",     (0,0),(-1,0),  BDR, fg_color),
        ("LINEBEFORE",    (0,0),(0,-1),  BDR, fg_color),
        ("LINEAFTER",     (-1,0),(-1,-1),BDR, fg_color),
    ]))
    hdr.keepWithNext = True

    # ── BLOCK 2: Clause text — chunked multi-row (crash-proof) ───────────
    # colWidths=[content_w] → left/right borders at exact same x as hdr
    c_style = _p("ct", size=9, color=C_TEXT, leading=14)
    c_tbl   = Table(_chunk_rows(text, c_style), colWidths=[content_w])
    c_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), bg_color),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("TOPPADDING",    (0,0),(-1,0),  8),
        ("BOTTOMPADDING", (0,-1),(-1,-1),8),
        ("LINEBEFORE",    (0,0),(0,-1),  BDR, fg_color),
        ("LINEAFTER",     (-1,0),(-1,-1),BDR, fg_color),
    ]))
    c_tbl.keepWithNext = True

    # ── BLOCK 3: AI decision vs Oracle truth ─────────────────────────────
    # colWidths: half_L + half_R = content_w exactly.
    # Each side block is its own chunked multi-row table → splittable.
    # The outer sides table has 1 row × 2 cols. This row CAN be large if
    # rationale is long, but since BOTH sides are chunked internally, the
    # outer row height is bounded by the taller of the two sides. If either
    # side alone exceeds a page, we emit them STACKED (one above the other)
    # rather than side-by-side — eliminating the 1-row crash path entirely.
    ai_decision  = "RISK FLAGGED" if action == 1 else "SAFE"
    ora_decision = "ACTUAL RISK"  if is_risk  else "ACTUALLY SAFE"

    half = content_w / 2   # exact half — cols sum to content_w

    def _side(lbl, decision, rationale, side_bg, col_w):
        rat_style = _p("rv", size=8.5, color=C_TEXT, leading=13)
        rows = (
            [[Paragraph(lbl, _p("rh", size=7, color=C_MUTED, bold=True))],
             [Paragraph(f"<b>{_x(decision)}</b>",
                        _p("rd", size=9, color=C_TEXT, bold=True))]]
            + _chunk_rows(rationale, rat_style)
        )
        t = Table(rows, colWidths=[col_w])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), side_bg),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("RIGHTPADDING",  (0,0),(-1,-1), 8),
            ("TOPPADDING",    (0,0),(-1,0),  8),
            ("BOTTOMPADDING", (0,-1),(-1,-1),8),
            ("BOX",           (0,0),(-1,-1), 0.5, C_BORDER),
        ]))
        return t

    # Estimate rough height: ~15pt per 50-word chunk
    def _est_height(rationale):
        return max(1, len(rationale.split()) / 50) * 15 + 40

    PAGE_H = 773   # usable frame height in pts

    if _est_height(ai_reason) + _est_height(ora_reason) < PAGE_H * 0.8:
        # Normal case: side-by-side — safe because combined height fits a page
        sides = Table([[
            _side("AI AGENT DECISION",   ai_decision,  ai_reason,
                  colors.HexColor("#F8F9FF"), half),
            _side("ORACLE GROUND TRUTH", ora_decision, ora_reason,
                  colors.HexColor("#FFFBF0"), half),
        ]], colWidths=[half, half])
        sides.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), C_WHITE),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("LINEBEFORE",    (0,0),(0,-1),  BDR, fg_color),
            ("LINEAFTER",     (-1,0),(-1,-1),BDR, fg_color),
        ]))
        sides.keepWithNext = True
        sides_blocks = [sides]
    else:
        # Long rationale fallback: stack vertically — each is a single-col
        # multi-row table → guaranteed splittable, never causes LayoutError.
        # Build a fresh helper that includes border styles inline — no
        # Build styles inline — no internal Table attribute access needed.
        def _side_full(lbl, decision, rationale, side_bg):
            rat_style = _p("rv", size=8.5, color=C_TEXT, leading=13)
            rows = (
                [[Paragraph(lbl, _p("rh", size=7, color=C_MUTED, bold=True))],
                 [Paragraph(f"<b>{_x(decision)}</b>",
                            _p("rd", size=9, color=C_TEXT, bold=True))]]
                + _chunk_rows(rationale, rat_style)
            )
            t = Table(rows, colWidths=[content_w])
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), side_bg),
                ("TOPPADDING",    (0,0),(-1,-1), 4),
                ("BOTTOMPADDING", (0,0),(-1,-1), 4),
                ("LEFTPADDING",   (0,0),(-1,-1), 8),
                ("RIGHTPADDING",  (0,0),(-1,-1), 8),
                ("TOPPADDING",    (0,0),(-1,0),  8),
                ("BOTTOMPADDING", (0,-1),(-1,-1),8),
                ("BOX",           (0,0),(-1,-1), 0.5, C_BORDER),
                ("LINEBEFORE",    (0,0),(0,-1),  BDR, fg_color),
                ("LINEAFTER",     (-1,0),(-1,-1),BDR, fg_color),
            ]))
            return t

        ai_block  = _side_full("AI AGENT DECISION",   ai_decision,  ai_reason,
                               colors.HexColor("#F8F9FF"))
        ora_block = _side_full("ORACLE GROUND TRUTH", ora_decision, ora_reason,
                               colors.HexColor("#FFFBF0"))
        ai_block.keepWithNext  = True
        ora_block.keepWithNext = True
        sides_blocks = [ai_block, ora_block]

    # ── BLOCK 4: Reliability bar (always small) ───────────────────────────
    # colWidths: 0.44 + 0.56 = 1.0 × content_w exactly
    bar = Table([[
        Paragraph("CUMULATIVE ORACLE RELIABILITY AFTER THIS CLAUSE:",
                  _p("bl", size=7, color=C_MUTED, bold=True)),
        Paragraph(f'<font color="{_hex(g_color)}"><b>{_bar(grade)}</b></font>',
                  _p("bv", size=8, color=g_color, mono=True, align=TA_RIGHT)),
    ]], colWidths=[content_w * 0.44, content_w * 0.56])
    bar.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_WHITE),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LINEBELOW",     (0,0),(-1,-1), BDR, fg_color),
        ("LINEBEFORE",    (0,0),(0,-1),  BDR, fg_color),
        ("LINEAFTER",     (-1,0),(-1,-1),BDR, fg_color),
    ]))

    return [hdr, c_tbl, *sides_blocks, bar, Spacer(1, 10)]


# ─────────────────────────────────────────────────────────────────────────────
# PAGE DECORATOR
# FIX-3: "⚖  LEGAL AUDITOR" → "LEGAL AUDITOR" (no emoji in canvas fonts)
# ─────────────────────────────────────────────────────────────────────────────
def _make_page_decorator(session_id: str, total_clauses: int):
    def decorator(canvas, doc):
        W, H = A4
        canvas.saveState()
        canvas.setFillColor(C_BG_DARK)
        canvas.rect(0, H-22, W, 22, fill=1, stroke=0)
        canvas.setFillColor(C_WHITE)
        canvas.setFont("Helvetica-Bold", 8)
        # FIX-3: removed ⚖ emoji — not in Helvetica
        canvas.drawString(20, H-14, "LEGAL AUDITOR  -  AI PERFORMANCE REPORT")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(W-20, H-14, f"Session: {session_id}")
        canvas.setStrokeColor(C_ACCENT)
        canvas.setLineWidth(2)
        canvas.line(0, H-23, W, H-23)
        canvas.setStrokeColor(C_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(20, 25, W-20, 25)
        canvas.setFillColor(C_MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(
            W/2, 14,
            f"Page {doc.page}  |  {total_clauses} clauses audited  |  "
            f"Zoro Legal Auditor RL Project 2026",
        )
        canvas.restoreState()
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────
def generate_audit_pdf(session_data: List[Dict[str, Any]], session_id: str) -> bytes:
    """
    Build the Oracle / Developer audit PDF and return raw bytes.
    All clause text is rendered in full — no truncation.
    """
    buf    = io.BytesIO()
    W, _H  = A4
    margin = 20 * mm

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=28, bottomMargin=30,
    )

    content_w = W - 2 * margin
    story: List = []

    story.extend(_build_cover(session_data, session_id, content_w))

    story.append(Paragraph("Clause-by-Clause Analysis",
                            _p("sh", size=13, color=C_ACCENT, bold=True)))
    story.append(HRFlowable(width="100%", thickness=1, color=C_ACCENT,
                             spaceAfter=10, spaceBefore=0))

    for entry in session_data:
        story.extend(_build_clause_card(entry, content_w))

    doc.build(
        story,
        onFirstPage=_make_page_decorator(session_id, len(session_data)),
        onLaterPages=_make_page_decorator(session_id, len(session_data)),
    )
    return buf.getvalue()
