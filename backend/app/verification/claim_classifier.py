"""
Phase 3 — Support / Contradiction Classification.
LLM classifies each chunk as SUPPORT, CONTRADICT, or NEUTRAL.
JSON-only output; no free-form explanation beyond the "reason" field.
"""
import json
import re
import logging
from typing import Optional

from app.core.llm import _get_client
from app.config import settings
from app.verification.schemas import ClassificationResult, EvidenceLabel, RetrievedEvidence

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT_TEMPLATE = """You are a scientific evidence classifier. Your task is to classify whether a piece of evidence SUPPORTS, CONTRADICTS, or is NEUTRAL with respect to the given claim.

RULES:
- Base your classification ONLY on the evidence text. Do not use external knowledge.
- SUPPORT: the evidence explicitly or strongly implies the claim is true.
- CONTRADICT: the evidence explicitly or strongly implies the claim is false or opposes it.
- NEUTRAL: the evidence does not clearly support or contradict (irrelevant, ambiguous, or inconclusive).
- If the evidence is about a different topic, use NEUTRAL.
- Do not summarize. Do not generate paragraphs. Output ONLY valid JSON.

CLAIM:
{claim}

EVIDENCE (excerpt):
{evidence_text}

Respond with exactly one JSON object, no other text:
{{"classification": "SUPPORT"|"CONTRADICT"|"NEUTRAL", "confidence": <number between 0 and 1>, "reason": "<one short sentence>"}}
"""


def _parse_classification_response(raw: str) -> Optional[ClassificationResult]:
    """Parse LLM response into ClassificationResult. Enforces JSON-only; strips markdown code blocks."""
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    # Strip optional markdown code block
    if "```json" in text:
        text = text.split("```json", 1)[-1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[-1].rsplit("```", 1)[0].strip()
    # Extract first {...} if there is extra text
    match = re.search(r"\{[^{}]*\"classification\"[^{}]*\}", text)
    if match:
        text = match.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("ClaimClassifier: invalid JSON from LLM: %s", raw[:200])
        return None
    cls_raw = (data.get("classification") or "").upper().strip()
    if "SUPPORT" in cls_raw:
        label = EvidenceLabel.SUPPORT
    elif "CONTRADICT" in cls_raw:
        label = EvidenceLabel.CONTRADICT
    else:
        label = EvidenceLabel.NEUTRAL
    try:
        conf = float(data.get("confidence", 0.5))
        conf = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        conf = 0.5
    reason = str(data.get("reason", ""))[:500]
    return ClassificationResult(classification=label, confidence=conf, reason=reason)


def classify_claim_evidence(claim: str, evidence_text: str) -> Optional[ClassificationResult]:
    """
    Call LLM once to classify one evidence chunk. Returns structured result or None on failure.
    """
    prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
        claim=claim,
        evidence_text=evidence_text[:3000],
    )
    client = _get_client()
    try:
        # Request JSON-only to reduce hallucination
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=300,
        )
        raw = (response.choices[0].message.content or "").strip()
        return _parse_classification_response(raw)
    except Exception as e:
        logger.exception("ClaimClassifier LLM call failed: %s", e)
        return None


class ClaimClassifier:
    """
    Classifies each retrieved evidence chunk as SUPPORT / CONTRADICT / NEUTRAL.
    Uses strict prompt and JSON parsing; no free-form answer.
    """

    def __init__(self, evidence_max_chars: int = 3000):
        self.evidence_max_chars = evidence_max_chars

    def classify(self, claim: str, retrieved: RetrievedEvidence) -> Optional[ClassificationResult]:
        text = retrieved.metadata.text
        if len(text) > self.evidence_max_chars:
            text = text[: self.evidence_max_chars] + "..."
        return classify_claim_evidence(claim, text)
