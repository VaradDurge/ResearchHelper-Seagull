"""
DOI Fetcher Utility

Fetches metadata and official landing page URL from Crossref and OpenAlex.
Does not download PDFs.
"""

from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx

CROSSREF_API = "https://api.crossref.org/works/"
OPENALEX_API = "https://api.openalex.org/works/https://doi.org/"


def normalize_doi(raw_doi: str) -> str:
    doi = (raw_doi or "").strip()
    doi = doi.replace("https://doi.org/", "")
    doi = doi.replace("http://doi.org/", "")
    if doi.lower().startswith("doi:"):
        doi = doi[4:]
    return doi.strip()


def _fetch_crossref(doi: str) -> Optional[Dict[str, Any]]:
    try:
        with httpx.Client(timeout=15) as client:
            response = client.get(f"{CROSSREF_API}{doi}")
            if response.status_code != 200:
                return None
            data = response.json().get("message", {})
            title_list = data.get("title") or []
            title = title_list[0] if title_list else None
            authors = []
            for author in data.get("author", []) or []:
                name_parts = [author.get("given"), author.get("family")]
                name = " ".join([part for part in name_parts if part])
                if name:
                    authors.append(name)
            url = data.get("URL")
            pdf_url = None
            for link in data.get("link", []) or []:
                content_type = (link.get("content-type") or "").lower()
                if "pdf" in content_type:
                    pdf_url = link.get("URL") or pdf_url
                    if pdf_url:
                        break
            return {
                "title": title,
                "authors": authors,
                "url": url,
                "pdf_url": pdf_url,
                "source": "crossref",
            }
    except Exception:
        return None


def _fetch_openalex(doi: str) -> Optional[Dict[str, Any]]:
    try:
        with httpx.Client(timeout=15) as client:
            response = client.get(f"{OPENALEX_API}{doi}")
            if response.status_code != 200:
                return None
            data = response.json()
            title = data.get("title")
            authors = []
            for auth in data.get("authorships", []) or []:
                author = auth.get("author", {})
                name = author.get("display_name")
                if name:
                    authors.append(name)
            landing_page_url = None
            pdf_url = None
            primary_location = data.get("primary_location") or {}
            if primary_location.get("landing_page_url"):
                landing_page_url = primary_location.get("landing_page_url")
            if primary_location.get("pdf_url"):
                pdf_url = primary_location.get("pdf_url")
            best_oa_location = data.get("best_oa_location") or {}
            if best_oa_location.get("landing_page_url") and not landing_page_url:
                landing_page_url = best_oa_location.get("landing_page_url")
            if best_oa_location.get("pdf_url"):
                pdf_url = best_oa_location.get("pdf_url")
            open_access = data.get("open_access") or {}
            if open_access.get("oa_url") and not landing_page_url:
                landing_page_url = open_access.get("oa_url")
            return {
                "title": title,
                "authors": authors,
                "url": landing_page_url,
                "pdf_url": pdf_url,
                "source": "openalex",
            }
    except Exception:
        return None


def _is_valid_metadata(result: Optional[Dict[str, Any]]) -> bool:
    """True if result has enough data to show (title or url)."""
    if not result:
        return False
    return bool(result.get("title") or result.get("url"))


def fetch_doi_metadata_first(doi: str) -> Dict[str, Any]:
    """
    Fetch metadata from Crossref and OpenAlex in parallel; return as soon as the
    first source returns valid data (title or url). Reduces lookup latency.
    """
    normalized = normalize_doi(doi)
    if not normalized:
        return {"doi": doi, "error": "Invalid DOI"}

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_crossref = executor.submit(_fetch_crossref, normalized)
        future_openalex = executor.submit(_fetch_openalex, normalized)
        futures = {future_crossref: "crossref", future_openalex: "openalex"}
        for future in as_completed(futures):
            try:
                result = future.result()
                if _is_valid_metadata(result):
                    return {
                        "doi": normalized,
                        "title": result.get("title"),
                        "authors": result.get("authors") or [],
                        "url": result.get("url"),
                        "pdf_url": result.get("pdf_url"),
                        "source": result.get("source"),
                    }
            except Exception:
                pass

    crossref = None
    openalex = None
    try:
        crossref = future_crossref.result()
    except Exception:
        pass
    try:
        openalex = future_openalex.result()
    except Exception:
        pass

    title = None
    authors: List[str] = []
    if crossref:
        title = crossref.get("title")
        authors = crossref.get("authors") or []
    if openalex:
        title = title or openalex.get("title")
        if not authors:
            authors = openalex.get("authors") or []
    url = (openalex and openalex.get("url")) or (crossref and crossref.get("url"))
    pdf_url = (openalex and openalex.get("pdf_url")) or (crossref and crossref.get("pdf_url"))
    source = "openalex" if (openalex and openalex.get("url")) else "crossref"

    if not title and not url:
        return {"doi": normalized, "error": "DOI not found"}
    return {
        "doi": normalized,
        "title": title,
        "authors": authors,
        "url": url,
        "pdf_url": pdf_url,
        "source": source,
    }


def fetch_doi_metadata(doi: str) -> Dict[str, Any]:
    normalized = normalize_doi(doi)
    if not normalized:
        return {"doi": doi, "error": "Invalid DOI"}

    # Fetch from both sources in parallel to reduce total wait time
    crossref = None
    openalex = None
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(_fetch_crossref, normalized): "crossref",
            executor.submit(_fetch_openalex, normalized): "openalex",
        }
        for future in as_completed(futures):
            source = futures[future]
            try:
                result = future.result()
                if source == "crossref":
                    crossref = result
                else:
                    openalex = result
            except Exception:
                pass

    title = None
    authors: List[str] = []
    if crossref:
        title = crossref.get("title") or title
        authors = crossref.get("authors") or authors
    if openalex:
        title = title or openalex.get("title")
        if not authors:
            authors = openalex.get("authors") or authors

    url = None
    pdf_url = None
    source = None
    if openalex and openalex.get("url"):
        url = openalex.get("url")
        source = "openalex"
    elif crossref and crossref.get("url"):
        url = crossref.get("url")
        source = "crossref"
    if openalex and openalex.get("pdf_url"):
        pdf_url = openalex.get("pdf_url")
    elif crossref and crossref.get("pdf_url"):
        pdf_url = crossref.get("pdf_url")

    if not title and not url:
        return {"doi": normalized, "error": "DOI not found"}

    return {
        "doi": normalized,
        "title": title,
        "authors": authors,
        "url": url,
        "pdf_url": pdf_url,
        "source": source,
    }

