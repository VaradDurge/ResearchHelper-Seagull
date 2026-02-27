"""
Part 3 — Structured Answer Templates (No Free Text).
Enforces JSON-only response schema; validates and retries on invalid format.
Prevents hallucinated citations by validating evidence_summary against scored_evidence.
"""
import json
import re
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.verification.schemas import (
    ConfidenceLabel,
    VerificationResult,
    VerificationStatus,
)

logger = logging.getLogger(__name__)

REQUIRED_TOP_LEVEL_KEYS = frozenset({
    "claim", "support_count", "contradict_count", "confidence_score",
    "confidence_label", "evidence_summary", "verification_status",
})
ALLOWED_VERIFICATION_STATUSES = frozenset({"VERIFIED", "INSUFFICIENT_EVIDENCE", "CONTRADICTED"})
ALLOWED_CONFIDENCE_LABELS = frozenset({
    "Strong", "Moderate", "Weak", "Inconclusive", "Contradicted", "Insufficient Evidence",
})
MAX_LLM_RETRIES = 3


def _verification_status_from_result(result: VerificationResult) -> VerificationStatus:
    """Map VerificationResult to canonical VerificationStatus."""
    if result.confidence_label == ConfidenceLabel.CONTRADICTED:
        return VerificationStatus.CONTRADICTED
    if result.confidence_label == ConfidenceLabel.INSUFFICIENT_EVIDENCE or result.evidence_count == 0:
        return VerificationStatus.INSUFFICIENT_EVIDENCE
    return VerificationStatus.VERIFIED


def _build_evidence_summary_from_result(result: VerificationResult) -> List[Dict[str, Any]]:
    """Build evidence_summary list from VerificationResult (no free text)."""
    summary: List[Dict[str, Any]] = []
    for se in result.scored_evidence:
        if isinstance(se, dict):
            cls = se.get("classification") or {}
            label = (cls.get("classification") or "NEUTRAL").upper()
            if "SUPPORT" in label:
                label = "SUPPORT"
            elif "CONTRADICT" in label:
                label = "CONTRADICT"
            else:
                label = "NEUTRAL"
            summary.append({
                "paper_id": se.get("paper_id", ""),
                "label": label,
                "evidence_score": se.get("evidence_score", 0.0),
                "doi": se.get("doi"),
            })
    return summary


class StructuredOutputEnforcer:
    """
    Ensures every output conforms to the structured JSON schema.
    - Validates VerificationResult (or dict) against required schema.
    - Optional: parse LLM-generated JSON with retry on invalid format.
    - Validates evidence_summary length vs support_count to prevent hallucinated citations.
    """

    def __init__(self, max_retries: int = MAX_LLM_RETRIES):
        self.max_retries = max_retries

    def result_to_structured_dict(self, result: VerificationResult) -> Dict[str, Any]:
        """
        Convert VerificationResult to the canonical structured format (no free-form prose).
        """
        verification_status = _verification_status_from_result(result)
        evidence_summary = _build_evidence_summary_from_result(result)
        return {
            "claim": result.claim,
            "support_count": result.support_count,
            "contradict_count": result.contradict_count,
            "confidence_score": result.confidence_score,
            "confidence_label": result.confidence_label.value,
            "evidence_summary": evidence_summary,
            "verification_status": verification_status.value,
        }

    def validate_structure(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate that data has required keys and allowed enum values.
        Returns (valid, error_message).
        """
        if not isinstance(data, dict):
            return False, "Output must be a JSON object"
        missing = REQUIRED_TOP_LEVEL_KEYS - set(data.keys())
        if missing:
            return False, f"Missing required keys: {sorted(missing)}"
        vs = data.get("verification_status")
        if vs not in ALLOWED_VERIFICATION_STATUSES:
            return False, f"verification_status must be one of {sorted(ALLOWED_VERIFICATION_STATUSES)}"
        cl = data.get("confidence_label")
        if cl not in ALLOWED_CONFIDENCE_LABELS:
            return False, f"confidence_label must be one of {sorted(ALLOWED_CONFIDENCE_LABELS)}"
        if not isinstance(data.get("support_count"), (int, float)) or data["support_count"] < 0:
            return False, "support_count must be a non-negative number"
        if not isinstance(data.get("contradict_count"), (int, float)) or data["contradict_count"] < 0:
            return False, "contradict_count must be a non-negative number"
        if not isinstance(data.get("confidence_score"), (int, float)):
            return False, "confidence_score must be a number"
        summary = data.get("evidence_summary")
        if not isinstance(summary, list):
            return False, "evidence_summary must be a list"
        support_count = int(data["support_count"])
        support_in_summary = sum(1 for e in summary if isinstance(e, dict) and (e.get("label") or "").upper() == "SUPPORT")
        if support_in_summary != support_count:
            return False, (
                f"evidence_summary support count ({support_in_summary}) does not match support_count ({support_count})"
            )
        return True, None

    def validate_result(self, result: VerificationResult) -> Tuple[bool, Optional[str]]:
        """Validate VerificationResult-derived structure (e.g. after aggregation)."""
        structured = self.result_to_structured_dict(result)
        return self.validate_structure(structured)

    def parse_llm_json(self, raw: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Parse LLM output as JSON. Strips markdown code blocks; extracts first JSON object.
        Returns (parsed_dict, error_message). On success error_message is None.
        """
        if not raw or not raw.strip():
            return None, "Empty response"
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json", 1)[-1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[-1].rsplit("```", 1)[0].strip()
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            text = match.group(0)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return None, str(e)
        if not isinstance(data, dict):
            return None, "Response is not a JSON object"
        return data, None

    def parse_and_validate_llm(self, raw: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Parse LLM output and validate structure. Retry not applied here (caller may retry).
        Returns (validated_dict, error_message).
        """
        data, parse_err = self.parse_llm_json(raw)
        if parse_err:
            return None, parse_err
        valid, struct_err = self.validate_structure(data)
        if not valid:
            return None, struct_err
        return data, None

    def enforce_from_result(self, result: VerificationResult) -> Dict[str, Any]:
        """
        Produce final structured output from VerificationResult.
        Never returns free-form LLM paragraphs; only the fixed schema.
        """
        structured = self.result_to_structured_dict(result)
        valid, err = self.validate_structure(structured)
        if not valid:
            logger.warning("StructuredOutputEnforcer: validation failed: %s", err)
            structured["verification_status"] = VerificationStatus.INSUFFICIENT_EVIDENCE.value
        return structured
