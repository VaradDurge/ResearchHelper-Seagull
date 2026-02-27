"""
Part 4 — Self-Check Pass (Second LLM Verification).
After classification + scoring, a second LLM pass validates:
- Cited DOIs missing?
- Claims unsupported by evidence?
- support_count matches evidence_summary length?
If failed → block final output.
"""
import json
import re
import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.llm import _get_client
from app.verification.schemas import SelfCheckResult, VerificationResult

logger = logging.getLogger(__name__)

SELF_CHECK_PROMPT_TEMPLATE = """You are a verification auditor. Check the following claim verification output for consistency and integrity.

RULES:
- Cite ONLY what is in the evidence. Do not add external knowledge.
- Output ONLY valid JSON.

CLAIM:
{claim}

VERIFICATION OUTPUT:
{verification_json}

Check:
1. Are any cited DOIs missing or invalid in the evidence?
2. Is the claim supported by the listed evidence (support_count and evidence_summary consistent)?
3. Does support_count match the number of SUPPORT items in evidence_summary?

Respond with exactly one JSON object, no other text:
{{"self_check_passed": true|false, "issues": ["issue1", "issue2"]}}
If all checks pass, use self_check_passed: true and issues: [].
"""


def _parse_self_check_response(raw: str) -> Optional[SelfCheckResult]:
    """Parse LLM response into SelfCheckResult. JSON-only; strip markdown."""
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json", 1)[-1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[-1].rsplit("```", 1)[0].strip()
    match = re.search(r"\{[\s\S]*\"self_check_passed\"[\s\S]*\}", text)
    if match:
        text = match.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("SelfCheckValidator: invalid JSON from LLM: %s", raw[:200])
        return None
    passed = bool(data.get("self_check_passed", False))
    issues = data.get("issues")
    if not isinstance(issues, list):
        issues = []
    issues = [str(i) for i in issues[:20]]
    return SelfCheckResult(self_check_passed=passed, issues=issues)


def _deterministic_checks(result: VerificationResult, structured: Dict[str, Any]) -> List[str]:
    """
    Non-LLM checks: support_count vs evidence_summary support count; DOI presence.
    Returns list of issue strings (empty if none).
    """
    issues: List[str] = []
    support_count = result.support_count
    summary = structured.get("evidence_summary") or []
    support_in_summary = sum(
        1 for e in summary
        if isinstance(e, dict) and (e.get("label") or "").upper() == "SUPPORT"
    )
    if support_in_summary != support_count:
        issues.append(
            f"support_count ({support_count}) does not match evidence_summary SUPPORT count ({support_in_summary})"
        )
    # Optional: flag when output claims a DOI that is not in evidence (hallucinated citation)
    # We do not block when DOIs are simply absent (many papers lack DOIs).
    return issues


class SelfCheckValidator:
    """
    Second-pass verification: deterministic checks + optional LLM check.
    Returns SelfCheckResult. If self_check_passed is False, pipeline should block final output.
    """

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm

    def validate(
        self,
        result: VerificationResult,
        structured_output: Optional[Dict[str, Any]] = None,
    ) -> SelfCheckResult:
        """
        Run deterministic checks first; if use_llm, run second LLM pass.
        structured_output can be the canonical dict (claim, support_count, evidence_summary, etc.).
        """
        if structured_output is None:
            from app.verification.firewall.structured_output import StructuredOutputEnforcer
            enforcer = StructuredOutputEnforcer()
            structured_output = enforcer.result_to_structured_dict(result)
        issues = _deterministic_checks(result, structured_output)
        if issues:
            return SelfCheckResult(self_check_passed=False, issues=issues)
        if not self.use_llm:
            return SelfCheckResult(self_check_passed=True, issues=[])
        try:
            prompt = SELF_CHECK_PROMPT_TEMPLATE.format(
                claim=result.claim,
                verification_json=json.dumps(structured_output, indent=0)[:4000],
            )
            client = _get_client()
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=500,
            )
            raw = (response.choices[0].message.content or "").strip()
            llm_result = _parse_self_check_response(raw)
            if llm_result is None:
                return SelfCheckResult(self_check_passed=False, issues=["Self-check LLM returned invalid response"])
            return llm_result
        except Exception as e:
            logger.exception("SelfCheckValidator LLM call failed: %s", e)
            return SelfCheckResult(self_check_passed=False, issues=[f"Self-check failed: {e!s}"])
