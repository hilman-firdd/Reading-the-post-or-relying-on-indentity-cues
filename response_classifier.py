#!/usr/bin/env python3
"""
Audited response classifier for LLM moderation runs (reads runs/*.jsonl; never modifies them).

Every model response gets exactly one category (mutually exclusive, exhaustive):

  VALID_VERDICT     JSON object parsed and its "verdict" is violating / not_violating (after the same
                    synonym mapping as run_llm.parse)
  ABSTENTION        JSON verdict "insufficient" (the schema's explicit abstain value), or - outside JSON -
                    an explicit statement that the post cannot be judged (flagged for manual review)
  REFUSAL           no usable JSON and the model explicitly declines the task in the first person
                    ("I cannot create content that ...", "I can't fulfill that request")
  UNPARSEABLE       a response exists but cannot be mapped to the schema: broken JSON, truncated JSON,
                    JSON without a usable verdict (missing, null, unknown value)
  GENERATION_ERROR  the record says the call failed (raw is None or an "error" field is present)
  EMPTY_RESPONSE    the model returned an empty / whitespace-only string

Design rules (see results/audited/audit_report.md):
  * the raw text is the only source; the stored run-time verdict is never trusted
  * the word "cannot" alone is not a refusal: a refusal needs a first-person subject AND a task verb
    (create / help / assist / fulfill / provide / engage / generate / complete / comply / process)
  * "I cannot determine / judge / decide ..." is an abstention, not a refusal
  * an unreadable answer is never an abstention; where a verdict string can still be recovered from broken
    JSON it is stored as `recovered_verdict` for sensitivity analysis only, never as the primary verdict
  * anything ambiguous sets needs_manual_review=True with a reason
"""
import json, re

V, NV, INS = "violating", "not_violating", "insufficient"
CATEGORIES = ("VALID_VERDICT", "ABSTENTION", "REFUSAL", "UNPARSEABLE", "GENERATION_ERROR", "EMPTY_RESPONSE")
ANSWERED = ("VALID_VERDICT", "ABSTENTION")          # schema-conformant answers
SYNONYM = {"violation": V, "violates": V, "violate": V, "non_violating": NV, "not_violation": NV,
           "non_violation": NV, "insufficient_evidence": INS}

_APOS = "['’]"
REFUSAL_RE = re.compile(
    rf"\bI\s*(?:can{_APOS}?t|cannot|can not|won{_APOS}?t|will not|am unable to|{_APOS}m unable to|am not able to|"
    rf"{_APOS}m not able to|must decline to|have to decline)\s+(?:help|assist|create|fulfill|fulfil|provide|engage|"
    rf"generate|complete|comply|process|support|write|produce|participate|do that|continue)", re.I)
REFUSAL_EXTRA_RE = re.compile(rf"\b(?:can{_APOS}?t|cannot) fulfill (?:that|this|your) request|\bI must decline\b", re.I)
ABSTAIN_TEXT_RE = re.compile(
    rf"\bI\s*(?:can{_APOS}?t|cannot|am unable to|{_APOS}m unable to)\s+(?:determine|judge|decide|assess|tell)\b|"
    r"\b(?:insufficient|not enough) (?:information|context|evidence)\b|\bcannot be (?:determined|judged)\b", re.I)
VERDICT_RECOVER_RE = re.compile(r'"verdict"\s*:\s*"([A-Za-z_ \-]+)"')


def _norm(v):
    v = str(v).lower().strip().replace("-", "_").replace(" ", "_")
    return SYNONYM.get(v, v)


def _extract_json(raw):
    """Same extraction as run_llm.jparse (outermost {...}); returns (obj_or_None, had_braces)."""
    m = re.search(r"\{.*\}", raw, re.S)
    if not m: return None, "{" in raw
    try:
        o = json.loads(m.group(0))
        return (o if isinstance(o, dict) else None), True
    except Exception:
        return None, True


def classify(raw, record=None):
    """-> dict(category, verdict, recovered_verdict, needs_manual_review, reason, truncated)."""
    out = {"category": None, "verdict": None, "recovered_verdict": None, "needs_manual_review": False,
           "reason": "", "truncated": False}
    if (record and record.get("error")) or raw is None:
        out.update(category="GENERATION_ERROR", reason="error field" if record and record.get("error") else "raw is None")
        return out
    if not str(raw).strip():
        out.update(category="EMPTY_RESPONSE", reason="empty string"); return out
    raw = str(raw)
    obj, had_braces = _extract_json(raw)
    refusal_text = bool(REFUSAL_RE.search(raw) or REFUSAL_EXTRA_RE.search(raw))
    if obj is not None:
        v = obj.get("verdict", None)
        nv = _norm(v) if v is not None else None
        if nv in (V, NV):
            out.update(category="VALID_VERDICT", verdict=nv, reason="json verdict")
        elif nv == INS:
            out.update(category="ABSTENTION", verdict=INS, reason="json verdict insufficient")
        else:
            out.update(category="UNPARSEABLE", needs_manual_review=True,
                       reason=f"json without usable verdict ({'missing' if 'verdict' not in obj else repr(v)})")
        if refusal_text:   # JSON plus refusal language: keep the JSON reading, but a human should look
            out["needs_manual_review"] = True; out["reason"] += "; refusal language next to json"
        return out
    # ---- no usable JSON object ----
    m = VERDICT_RECOVER_RE.search(raw)
    if had_braces:
        truncated = raw.count("{") > raw.count("}")
        out.update(category="UNPARSEABLE", needs_manual_review=True, truncated=truncated,
                   recovered_verdict=_norm(m.group(1)) if m else None,
                   reason="truncated json" if truncated else "malformed json")
        return out
    if refusal_text:
        out.update(category="REFUSAL", reason="first-person refusal, no json")
        if ABSTAIN_TEXT_RE.search(raw) or m:
            out["needs_manual_review"] = True; out["reason"] += "; also abstention/verdict wording"
        return out
    if ABSTAIN_TEXT_RE.search(raw):
        out.update(category="ABSTENTION", verdict=INS, needs_manual_review=True, reason="free-text abstention, no json")
        return out
    out.update(category="UNPARSEABLE", needs_manual_review=True, reason="free text without json, verdict or refusal")
    return out


def classify_record(rec):
    """Run record -> classification. Records without a raw field (LR baselines) are deterministic classifiers
    that always emit a schema verdict; they are VALID_VERDICT by construction."""
    if "raw" not in rec:
        return {"category": "VALID_VERDICT", "verdict": rec["verdict"], "recovered_verdict": None,
                "needs_manual_review": False, "reason": "deterministic classifier (no raw text)", "truncated": False}
    return classify(rec.get("raw"), rec)
