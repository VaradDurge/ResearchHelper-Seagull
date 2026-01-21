"""
DOI lookup service.
"""
from typing import List

from app.utils.doi_fetcher import fetch_doi_metadata, normalize_doi
from app.models.schemas import DoiLookupResult


def lookup_dois(dois: List[str], max_items: int = 5) -> List[DoiLookupResult]:
    unique_dois = []
    seen = set()
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
