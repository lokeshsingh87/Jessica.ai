# Copyright (c) 2026 Zoro - Legal Auditor RL Project — PATCHED v3
# oracle.py — Deterministic legal-risk grader (no LLM, no network)
#
# v3 changes:
#   - Difficulty now derived from severity_score, not just jargon heuristic
#     severity >= 0.85 -> hard, >= 0.60 -> medium, else jargon heuristic
#   - This makes risk_audit produce medium/hard rewards instead of easy
#   - All 9 curriculum clauses produce correct is_risk AND varied difficulty
#   - 11 critical rules covering original + new curriculum patterns

import re
from typing import Dict, Any


class StrictLegalOracle:
    def __init__(self):
        self.negation_pattern = (
            r"\b(not|never|no|none|neither|void|excludes|excluding|"
            r"isn't|won't|without|disclaims|waives|prohibits|precludes)\b"
        )
        self.safe_harbors = [
            r"(?i)\bshall\s+not\s+be\s+liable\b",
            r"(?i)\bmutual(ly)?\b",
            r"(?i)\bcapped\s+at\b",
            r"(?i)\bexcept\s+for\s+gross\s+negligence\b",
            r"(?i)\bopt-out\b",
            r"(?i)\bwith\s+prior\s+written\s+notice\b",
        ]

        # Critical rules — severity 1.0, override safe harbors
        # Maps rule name -> (regex_pattern, severity_score)
        self.critical_rules: Dict[str, tuple] = {
            # ── Original rules ──────────────────────────────────────────────
            "Uncapped_Indemnity": (
                r"(?i)indemnif.{0,120}(?:unlimited|without\s+limit|no\s+cap|solely)", 1.0
            ),
            "Unilateral_Power": (
                r"(?i)sole\s+discretion|without\s+notice|at\s+any\s+time", 0.90
            ),
            "Unilateral_Termination": (
                r"(?i)terminate.{0,120}(?:at\s+any\s+time|without\s+cause|sole\s+discretion)", 0.95
            ),
            "Unilateral_Amendment": (
                r"(?i)(?:modify|amend|change).{0,120}(?:terms|agreement).{0,120}without\s+notice", 0.85
            ),
            "Class_Action_Waiver": (
                r"(?i)waive.{0,120}(?:class\s+action|representative\s+action|jury\s+trial)", 1.0
            ),
            # ── New rules — match actual curriculum clauses ─────────────────
            "Unlimited_Liability": (
                r"(?i)unlimited\s+liabilit", 1.0
            ),
            "Uncapped_Indemnity_v2": (
                r"(?i)indemnif.{0,150}(?:without\s+any.{0,50}cap|no\s+financial)", 0.95
            ),
            "Unilateral_Price_Change": (
                r"(?i)(?:change|modify|alter)\s+pric.{0,80}without\s+(?:prior\s+)?notice", 0.80
            ),
            "Payment_Term_Conflict": (
                r"(?i)\b(?:30|60|90|120)\s+days?.{0,100}\b(?:30|60|90|120)\s+days?", 0.75
            ),
            "Jurisdiction_Conflict": (
                r"(?i)(?:governed\s+by|law\s+of|under\s+the\s+laws?\s+of)"
                r".{0,60}(?:yet|but|however|while|whereas|although|notwithstanding)"
                r".{0,120}(?:court|arbitrat|mandates|venue|tribunal)",
                0.85
            ),
            "Termination_Conflict": (
                r"(?i)(?:30|60|90)\s+days?\s+notice.{0,120}(?:immediate|without\s+(?:cause|notice))",
                0.80
            ),
            # ── Compliance defect rules (basic_compliance curriculum) ────────
            "Missing_Execution_Date": (
                r"(?i)missing.{0,60}(?:execution\s+date|valid\s+date|effective\s+date)"
                r"|(?:execution|effective|valid)\s+date.{0,60}(?:missing|absent|omitted|not\s+(?:present|found|included))",
                0.65
            ),
            "Missing_Signature": (
                r"(?i)(?:signature|sign(?:ed|ature)\s+of).{0,80}(?:absent|missing|omitted|not\s+(?:present|found|included))"
                r"|(?:absent|missing).{0,80}(?:signature|authorized\s+representative)",
                0.65
            ),
            "Missing_Governing_Law": (
                r"(?i)fails?\s+to\s+(?:specify|identify|include|state|define).{0,60}"
                r"(?:governing\s+law|applicable\s+law|jurisdiction\s+of|choice\s+of\s+law)"
                r"|governing\s+law.{0,60}(?:absent|missing|unspecified|not\s+(?:specified|identified|included))",
                0.70
            ),
        }

        # Standard rules — severity 0.6, can be neutralised by safe harbor
        self.standard_rules: Dict[str, str] = {
            "General_Indemnity":        r"(?i)\bindemnif\b|\bhold\s+harmless\b",
            "Limitation_Of_Liability":  r"(?i)limit(ation)?\s+of\s+liabil|maximum\s+aggregate",
            "Automatic_Renewal":        r"(?i)auto(matically)?\s+renew",
            "Non_Refundable":           r"(?i)non-refundable|no\s+refunds",
        }

        self.jargon = [
            "notwithstanding", "heretofore", "severability", "fiduciary",
            "force majeure", "jurisdiction", "pursuant",
        ]

    # ── PII masking ───────────────────────────────────────────────────────────
    def mask_pii(self, text: str) -> str:
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[EMAIL]', text)
        text = re.sub(r'[\$€£¥]\d+(?:,\d{3})*(?:\.\d{2})?', '[AMOUNT]', text)
        text = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '[DATE]', text)
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
        text = re.sub(r'\(?\d{3}\)?[\s\-]\d{3}[\s\-]\d{4}', '[PHONE]', text)
        text = re.sub(r'\b\d{1,3}(?:\.\d{1,3}){3}\b', '[IP]', text)
        return text

    # ── Negation check ────────────────────────────────────────────────────────
    def _is_negated(self, text: str, match_start: int) -> bool:
        lookback = text[max(0, match_start - 80): match_start]
        return bool(re.search(self.negation_pattern, lookback))

    # ── Core evaluation ───────────────────────────────────────────────────────
    def evaluate_clause(self, text: str) -> Dict[str, Any]:
        text_clean = " ".join(text.split()).strip()
        word_count = len(text_clean.split())

        critical_hits = []
        for name, (pat, sev) in self.critical_rules.items():
            m = re.search(pat, text_clean)
            if m and not self._is_negated(text_clean, m.start()):
                critical_hits.append((name, sev))

        standard_hits = [
            name for name, pat in self.standard_rules.items()
            if (m := re.search(pat, text_clean)) and not self._is_negated(text_clean, m.start())
        ]
        has_safe_harbor = any(re.search(p, text_clean) for p in self.safe_harbors)

        is_risk   = False
        severity  = 0.0
        rationale = "Compliance verified: No unmitigated risk triggers detected."
        category  = "General"

        if critical_hits:
            # Take the highest-severity matched rule
            top_name, top_sev = max(critical_hits, key=lambda x: x[1])
            severity  = top_sev
            is_risk   = True
            category  = top_name
            names_str = ", ".join(n for n, _ in critical_hits)
            rationale = f"CRITICAL FAILURE: Detected {names_str}."
        elif standard_hits:
            if has_safe_harbor:
                is_risk   = False
                severity  = 0.2
                rationale = (
                    f"NEUTRALIZED: Found {', '.join(standard_hits)}, "
                    "but mitigated by Safe Harbor."
                )
            else:
                is_risk   = True
                severity  = 0.6
                category  = standard_hits[0]
                rationale = f"STANDARD RISK: Unmitigated {', '.join(standard_hits)} detected."

        jargon_count   = sum(1 for w in self.jargon if w in text_clean.lower())
        jargon_density = jargon_count / max(1, word_count)
        raw_entropy    = (word_count * 0.01) + (jargon_count * 0.05)
        complexity_entropy = round(max(0.0, min(1.0, float(raw_entropy))), 4)

        # Difficulty: primarily driven by severity_score so that risk clauses
        # are graded appropriately hard/medium rather than defaulting to easy.
        # Jargon heuristic acts as a tiebreaker for non-risk clauses.
        if severity >= 0.85:
            difficulty = "hard"
        elif severity >= 0.60:
            difficulty = "medium"
        elif (has_safe_harbor and (critical_hits or standard_hits)) or jargon_density > 0.07:
            difficulty = "hard"
        elif jargon_density > 0.03 or word_count > 30:
            difficulty = "medium"
        else:
            difficulty = "easy"

        return {
            "is_actually_risk":       is_risk,
            "severity_score":         round(severity, 4),
            "difficulty":             difficulty,
            "legal_category":         category,
            "ground_truth_rationale": rationale,
            "complexity_entropy":     complexity_entropy,
            "metadata": {
                "word_count":      word_count,
                "jargon_density":  round(jargon_density, 3),
                "has_safe_harbor": has_safe_harbor,
                "critical_hits":   [n for n, _ in critical_hits],
                "standard_hits":   standard_hits,
            },
        }


# Module-level singleton
oracle_judge = StrictLegalOracle()


def evaluate_clause_difficulty_and_truth(text: str) -> Dict[str, Any]:
    """Public API used by inference.py and app.py."""
    return oracle_judge.evaluate_clause(text)