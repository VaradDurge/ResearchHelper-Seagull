"""
DOI lookup + import service.

PDF download priority:
  1. Unpaywall API  (most reliable — returns verified OA PDF links)
  2. Semantic Scholar API  (good fallback for arXiv & OA papers)
  3. arXiv direct link  (if landing URL points to arxiv.org)
  4. Metadata pdf_url from Crossref / OpenAlex  (last resort)
"""
from typing import List, Optional
import logging
import os
import re
import uuid
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.services.ingestion_service import ingest_pdf
from app.utils.doi_fetcher import fetch_doi_metadata, normalize_doi
from app.models.schemas import DoiLookupResult, PaperResponse

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
}

# Per-request timeout (seconds). Short so one bad URL doesn't block the rest.
_REQ_TIMEOUT = 20


# ── Lookup (unchanged) ───────────────────────────────────────────────────

def lookup_dois(dois: List[str], max_items: int = 5) -> List[DoiLookupResult]:
    unique_dois: List[str] = []
    seen: set[str] = set()
    for doi in dois:
        normalized = normalize_doi(doi)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_dois.append(normalized)
        if len(unique_dois) >= max_items:
            break
    results: List[DoiLookupResult] = []
    for doi in unique_dois:
        data = fetch_doi_metadata(doi)
        results.append(DoiLookupResult(**data))
    return results


# ── Helpers ──────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", name).strip("._-")
    return cleaned or "paper"


def _is_pdf(resp: httpx.Response) -> bool:
    ct = (resp.headers.get("content-type") or "").lower()
    return "application/pdf" in ct or resp.content[:5] == b"%PDF-"


def _get(client: httpx.Client, url: str) -> Optional[httpx.Response]:
    """GET with short timeout; returns None on any failure."""
    try:
        r = client.get(url, follow_redirects=True, headers=_HEADERS, timeout=_REQ_TIMEOUT)
        return r if r.status_code == 200 else None
    except Exception as exc:
        log.debug("  GET failed: %s – %s", url, exc)
        return None


def _download(client: httpx.Client, url: str) -> Optional[bytes]:
    """Try to download a PDF from *url*. Returns bytes or None."""
    resp = _get(client, url)
    if resp is None:
        return None
    if _is_pdf(resp):
        return resp.content
    return None


# ── PDF URL finders ──────────────────────────────────────────────────────

def _unpaywall_urls(doi: str) -> List[str]:
    """Query the free Unpaywall API for direct OA PDF links."""
    urls: List[str] = []
    try:
        with httpx.Client(timeout=12) as c:
            r = c.get(
                f"https://api.unpaywall.org/v2/{doi}",
                params={"email": "seagull-research@users.noreply.github.com"},
            )
            if r.status_code != 200:
                return urls
            data = r.json()
            best = data.get("best_oa_location") or {}
            if best.get("url_for_pdf"):
                urls.append(best["url_for_pdf"])
            for loc in data.get("oa_locations") or []:
                pdf = loc.get("url_for_pdf")
                if pdf and pdf not in urls:
                    urls.append(pdf)
    except Exception as exc:
        log.debug("Unpaywall failed: %s", exc)
    return urls


def _semantic_scholar_urls(doi: str) -> List[str]:
    """Query Semantic Scholar for an open-access PDF link."""
    urls: List[str] = []
    try:
        with httpx.Client(timeout=12) as c:
            r = c.get(
                f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
                params={"fields": "isOpenAccess,openAccessPdf"},
            )
            if r.status_code != 200:
                return urls
            data = r.json()
            oa_pdf = data.get("openAccessPdf") or {}
            if oa_pdf.get("url"):
                urls.append(oa_pdf["url"])
    except Exception as exc:
        log.debug("Semantic Scholar failed: %s", exc)
    return urls


def _arxiv_url(landing_url: Optional[str]) -> Optional[str]:
    """If the landing URL is an arXiv abs page, return the direct PDF link."""
    if not landing_url:
        return None
    m = re.search(r"arxiv\.org/abs/([\w.]+)", landing_url)
    if m:
        return f"https://arxiv.org/pdf/{m.group(1)}.pdf"
    return None


# ── Main import ──────────────────────────────────────────────────────────

def import_doi(
    doi: str,
    workspace_id: str,
    user_id: str,
) -> PaperResponse:
    normalized = normalize_doi(doi)
    if not normalized:
        raise ValueError("Invalid DOI")

    metadata = fetch_doi_metadata(normalized)
    if metadata.get("error"):
        raise ValueError(metadata["error"])

    landing_url = metadata.get("url")
    meta_pdf = metadata.get("pdf_url")

    # ── Build candidate list (order matters) ──

    candidates: List[str] = []

    # 1. Unpaywall  (verified OA links — most reliable)
    candidates.extend(_unpaywall_urls(normalized))

    # 2. Semantic Scholar  (good for arXiv + OA)
    candidates.extend(_semantic_scholar_urls(normalized))

    # 3. arXiv direct
    arxiv = _arxiv_url(landing_url)
    if arxiv:
        candidates.append(arxiv)

    # 4. Metadata pdf_url from Crossref/OpenAlex
    if meta_pdf:
        candidates.append(meta_pdf)

    # Deduplicate
    seen: set[str] = set()
    unique: List[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    candidates = unique

    if not candidates:
        raise ValueError(
            "No open-access PDF found for this DOI. "
            "The paper may not be available as open access."
        )

    log.info("DOI %s – %d candidate PDF URLs:", normalized, len(candidates))
    for i, url in enumerate(candidates):
        log.info("  [%d] %s", i + 1, url)

    # ── Try each candidate ──

    with httpx.Client() as client:
        for url in candidates:
            pdf_bytes = _download(client, url)
            if pdf_bytes:
                log.info("  ✓ Downloaded %d bytes from %s", len(pdf_bytes), url)
                break
        else:
            raise ValueError(
                "Could not download an open-access PDF from any known source. "
                "The paper may be behind a paywall or require browser access."
            )

    if len(pdf_bytes) > settings.max_upload_size:
        raise ValueError("Downloaded PDF exceeds maximum allowed size")

    # ── Save & ingest ──

    paper_id = str(uuid.uuid4())
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, f"{paper_id}.pdf")
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    original_name = metadata.get("title") or normalized
    original_filename = f"{_safe_filename(original_name)}.pdf"

    paper_metadata = {"doi": normalized}
    if metadata.get("publication_date"):
        paper_metadata["publication_date"] = metadata["publication_date"]
    try:
        return ingest_pdf(
            pdf_path=file_path,
            paper_id=paper_id,
            workspace_id=workspace_id,
            user_id=user_id,
            original_filename=original_filename,
            paper_metadata=paper_metadata,
        )
    except Exception as exc:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise exc
