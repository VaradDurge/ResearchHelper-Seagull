"""
DOI Fetcher Utility

Fetches metadata and official landing page URL from Crossref and OpenAlex.
Does not download PDFs.
"""

from typing import Dict, Any, Optional, List
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
        with httpx.Client(timeout=10) as client:
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
            return {
                "title": title,
                "authors": authors,
                "url": url,
                "source": "crossref",
            }
    except Exception:
        return None


def _fetch_openalex(doi: str) -> Optional[Dict[str, Any]]:
    try:
        with httpx.Client(timeout=10) as client:
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
            primary_location = data.get("primary_location") or {}
            if primary_location.get("landing_page_url"):
                landing_page_url = primary_location.get("landing_page_url")
            return {
                "title": title,
                "authors": authors,
                "url": landing_page_url,
                "source": "openalex",
            }
    except Exception:
        return None


def fetch_doi_metadata(doi: str) -> Dict[str, Any]:
    normalized = normalize_doi(doi)
    if not normalized:
        return {"doi": doi, "error": "Invalid DOI"}

    crossref = _fetch_crossref(normalized)
    openalex = _fetch_openalex(normalized)

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
    source = None
    if openalex and openalex.get("url"):
        url = openalex.get("url")
        source = "openalex"
    elif crossref and crossref.get("url"):
        url = crossref.get("url")
        source = "crossref"

    if not title and not url:
        return {"doi": normalized, "error": "DOI not found"}

    return {
        "doi": normalized,
        "title": title,
        "authors": authors,
        "url": url,
        "source": source,
    }

