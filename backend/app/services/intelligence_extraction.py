"""
Research Intelligence Extraction — runs after paper upload.
Stores paper-level embedding and LLM-extracted structured data in MongoDB.
Do NOT compute embeddings during graph render; compute at upload only.
"""
from typing import List, Dict, Any, Optional
import json
import re
import logging
import traceback
from datetime import datetime

from app.config import settings
from app.db.mongo import get_paper_intelligence_collection
from app.utils.pdf_parser import (
    parse_pdf,
    get_abstract_and_conclusion_text,
    get_full_pdf_text_first_chars,
)
from app.core.embeddings import generate_embedding
from app.core.llm import generate_completion_json

logger = logging.getLogger(__name__)

MIN_TEXT_LENGTH_FOR_ABSTRACT_CONCLUSION = 100
FALLBACK_FULL_TEXT_CHARS = 2000
EXTRACTION_TEXT_CAP = 12000

EXTRACTION_PROMPT = """Extract structured information from this research paper text (abstract and/or conclusion, or excerpt).
Return ONLY valid JSON with no markdown or extra text. Use this exact structure:

{{
  "main_problem": "One sentence describing the main problem addressed.",
  "methods_used": ["method1", "method2"],
  "key_findings": ["finding1", "finding2"],
  "datasets_used": ["dataset1", "dataset2"],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "domain": "NLP",
  "claims": ["claim1", "claim2"]
}}

Rules:
- methods_used: techniques, algorithms, or approaches (e.g. Transformer, BERT, reinforcement learning).
- datasets_used: named datasets or data sources mentioned.
- keywords: at least 3 and ideally 5-10 key terms for search/topology. Include domain terms and key concepts from the title.
- domain: one of NLP, CV, Healthcare, ML, Robotics, HCI, or a short label.
- claims: explicit or strongly implied factual claims (optional, can be empty array).
- If a field cannot be determined, use empty array [] or empty string "".
- Trim whitespace from all strings. Do not return null; use "" or [].

Paper title: {title}

Text:
{text}
"""


def _generate_paper_embedding_openai(text: str) -> Optional[List[float]]:
    if not text or not text.strip():
        return None
    key = getattr(settings, "openai_api_key", None) or ""
    if not key or not key.strip():
        logger.error("OPENAI_API_KEY is not set; cannot generate paper embedding with OpenAI.")
        raise ValueError("OPENAI_API_KEY is not configured")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key.strip())
        text_trim = text[:30000] if len(text) > 30000 else text
        resp = client.embeddings.create(
            model=getattr(settings, "openai_embedding_model", "text-embedding-3-small"),
            input=text_trim,
        )
        vec = resp.data[0].embedding
        if not vec or not isinstance(vec, list):
            logger.error("OpenAI embedding returned empty or non-list for paper.")
            return None
        return [float(x) for x in vec]
    except Exception as e:
        logger.exception("OpenAI embedding failed: %s", e)
        raise


def generate_paper_embedding(text: str) -> Optional[List[float]]:
    """Generate one embedding for the paper. Returns list of floats or None. Raises on OpenAI config error."""
    if not text or not text.strip():
        logger.warning("generate_paper_embedding called with empty text.")
        return None
    provider = getattr(settings, "paper_embedding_provider", "local")
    logger.info("Paper embedding provider: %s", provider)
    if provider == "openai":
        return _generate_paper_embedding_openai(text)
    try:
        vec = generate_embedding(text)
        if vec is None:
            return None
        if isinstance(vec, list):
            return [float(x) for x in vec]
        # numpy or similar
        return [float(x) for x in vec] if hasattr(vec, "__iter__") else None
    except Exception as e:
        logger.exception("Local paper embedding failed: %s", e)
        raise


def _ensure_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    return [str(x).strip()] if str(x).strip() else []


def _dedupe_keywords(keywords: List[str]) -> List[str]:
    seen = set()
    out = []
    for k in keywords:
        n = k.strip().lower()
        if n and n not in seen:
            seen.add(n)
            out.append(k.strip())
    return out


def run_llm_extraction(text: str, title: str) -> Dict[str, Any]:
    """
    Call LLM with strict JSON mode. Retry once on parse failure.
    Ensures keywords has at least 3 items when possible; trims and deduplicates.
    """
    if not text or not text.strip():
        logger.warning("run_llm_extraction called with empty text.")
        return _empty_extraction()
    prompt = EXTRACTION_PROMPT.format(
        title=title or "Untitled",
        text=text[:EXTRACTION_TEXT_CAP],
    )
    raw = None
    for attempt in range(2):
        try:
            raw = generate_completion_json(prompt)
            logger.info("LLM raw response (first 500 chars): %s", (raw[:500] if raw else "") + ("..." if len(raw or "") > 500 else ""))
            if not raw or not raw.strip():
                logger.warning("LLM returned empty response (attempt %s).", attempt + 1)
                if attempt == 0:
                    continue
                return _empty_extraction()
            # Strip markdown code block if present (some models still add it)
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```\s*$", "", raw)
            data = json.loads(raw)
            if not isinstance(data, dict):
                logger.warning("LLM response is not a JSON object (attempt %s).", attempt + 1)
                if attempt == 0:
                    continue
                return _empty_extraction()
            main_problem = (data.get("main_problem") or "").strip()
            methods_used = _ensure_list(data.get("methods_used"))
            key_findings = _ensure_list(data.get("key_findings"))
            datasets_used = _ensure_list(data.get("datasets_used"))
            keywords = _ensure_list(data.get("keywords"))
            keywords = _dedupe_keywords(keywords)
            if len(keywords) < 3 and (title or text):
                # Try to add title-derived terms
                title_words = re.findall(r"[a-zA-Z0-9]{4,}", (title or "") + " " + text[:500])
                for w in title_words:
                    w = w.strip().lower()
                    if w and w not in {k.lower() for k in keywords} and len(keywords) < 10:
                        keywords.append(w)
                keywords = _dedupe_keywords(keywords)
            domain = (data.get("domain") or "").strip()
            claims = _ensure_list(data.get("claims"))
            logger.info("LLM extraction success: main_problem=%s chars, methods=%s, keywords=%s", len(main_problem), len(methods_used), len(keywords))
            return {
                "main_problem": main_problem,
                "methods_used": methods_used,
                "key_findings": key_findings,
                "datasets_used": datasets_used,
                "keywords": keywords,
                "domain": domain,
                "claims": claims,
            }
        except json.JSONDecodeError as e:
            logger.warning("LLM JSON parse failure (attempt %s): %s. Raw (first 300): %s", attempt + 1, e, (raw or "")[:300])
            if attempt == 0:
                continue
            logger.error("LLM extraction failed after retry; not storing empty intelligence.")
            return _empty_extraction()
        except Exception as e:
            logger.exception("LLM extraction error (attempt %s): %s", attempt + 1, e)
            if attempt == 0:
                continue
            return _empty_extraction()
    return _empty_extraction()


def _empty_extraction() -> Dict[str, Any]:
    return {
        "main_problem": "",
        "methods_used": [],
        "key_findings": [],
        "datasets_used": [],
        "keywords": [],
        "domain": "",
        "claims": [],
    }


def _is_valid_intelligence(
    embedding_vector: Optional[List[float]],
    extracted: Dict[str, Any],
) -> bool:
    """Return True only if we have at least an embedding or meaningful structured data."""
    if embedding_vector and len(embedding_vector) > 0:
        return True
    if (extracted.get("main_problem") or "").strip():
        return True
    if extracted.get("keywords"):
        return True
    if extracted.get("methods_used"):
        return True
    if extracted.get("datasets_used"):
        return True
    return False


def store_paper_intelligence(
    paper_id: str,
    workspace_id: str,
    embedding_vector: Optional[List[float]] = None,
    main_problem: Optional[str] = None,
    methods_used: Optional[List[str]] = None,
    key_findings: Optional[List[str]] = None,
    datasets_used: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    domain: Optional[str] = None,
    claims: Optional[List[str]] = None,
) -> None:
    """Upsert one document into paper_intelligence. Requires workspace_id. Logs Mongo result."""
    coll = get_paper_intelligence_collection()
    doc = {
        "paper_id": paper_id,
        "workspace_id": workspace_id,
        "embedding_vector": embedding_vector,
        "main_problem": (main_problem or "").strip(),
        "methods_used": methods_used or [],
        "key_findings": key_findings or [],
        "datasets_used": datasets_used or [],
        "keywords": keywords or [],
        "domain": (domain or "").strip(),
        "claims": claims or [],
        "extracted_at": datetime.utcnow(),
    }
    result = coll.update_one(
        {"paper_id": paper_id},
        {"$set": doc},
        upsert=True,
    )
    logger.info(
        "Stored paper_intelligence for paper_id=%s workspace_id=%s (matched=%s modified=%s upserted_id=%s)",
        paper_id,
        workspace_id,
        result.matched_count,
        result.modified_count,
        result.upserted_id,
    )


def run_intelligence_extraction(
    paper_id: str,
    pdf_path: str,
    workspace_id: str,
    title: str,
    abstract: Optional[str] = None,
) -> None:
    """
    Entry point: extract text, generate embedding, run LLM extraction, store only if valid.
    Does NOT upsert empty/minimal documents on failure. Logs everything; does not swallow exceptions.
    """
    logger.info("run_intelligence_extraction started: paper_id=%s workspace_id=%s", paper_id, workspace_id)
    try:
        pdf_data = parse_pdf(pdf_path)
        text = get_abstract_and_conclusion_text(pdf_data)
        if abstract and abstract.strip() and (abstract.strip() not in (text or "")):
            text = (abstract.strip() + "\n\n" + (text or "")) if text else abstract.strip()

        text_len = len(text or "")
        text_preview = (text or "")[:200]
        logger.info(
            "Extracted abstract+conclusion: length=%s empty=%s first_200=%s",
            text_len,
            not (text or "").strip(),
            repr(text_preview),
        )

        if not (text or "").strip() or text_len < MIN_TEXT_LENGTH_FOR_ABSTRACT_CONCLUSION:
            fallback = get_full_pdf_text_first_chars(pdf_data, FALLBACK_FULL_TEXT_CHARS)
            if fallback and len(fallback.strip()) >= 50:
                text = fallback
                text_len = len(text)
                logger.info("Using fallback full PDF text (first %s chars), length=%s", FALLBACK_FULL_TEXT_CHARS, text_len)
            else:
                logger.error("No sufficient text for paper_id=%s (abstract+conclusion empty or short, fallback also insufficient). Not storing empty intelligence.", paper_id)
                return

        provider = getattr(settings, "paper_embedding_provider", "local")
        logger.info("Embedding provider for paper: %s", provider)

        embedding_vector = None
        try:
            embedding_vector = generate_paper_embedding(text)
        except Exception as e:
            logger.exception("Paper embedding generation failed: %s", e)
            traceback.print_exc()
            raise

        if embedding_vector is None:
            logger.error("Embedding result is None for paper_id=%s. Not storing empty intelligence.", paper_id)
            return
        if not isinstance(embedding_vector, list) or len(embedding_vector) == 0:
            logger.error("Embedding is empty or not a list for paper_id=%s. Not storing.", paper_id)
            return
        logger.info("Embedding vector length: %s", len(embedding_vector))

        extracted = run_llm_extraction(text, title)
        if not _is_valid_intelligence(embedding_vector, extracted):
            logger.warning("Extraction produced no meaningful data (no embedding, no main_problem, no keywords/methods/datasets) for paper_id=%s. Not storing empty intelligence.", paper_id)
            return

        store_paper_intelligence(
            paper_id=paper_id,
            workspace_id=workspace_id,
            embedding_vector=embedding_vector,
            main_problem=extracted.get("main_problem"),
            methods_used=extracted.get("methods_used"),
            key_findings=extracted.get("key_findings"),
            datasets_used=extracted.get("datasets_used"),
            keywords=extracted.get("keywords"),
            domain=extracted.get("domain"),
            claims=extracted.get("claims"),
        )
        logger.info("run_intelligence_extraction completed successfully: paper_id=%s", paper_id)
    except Exception as e:
        logger.exception("Intelligence extraction failed for paper_id=%s: %s", paper_id, e)
        traceback.print_exc()
        raise
