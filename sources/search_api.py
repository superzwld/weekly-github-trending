"""Candidate source: recently active public repositories from GitHub Search."""

from __future__ import annotations

from .github import format_utc, search_repositories


def fetch_search_api(window: dict[str, object] | None = None) -> list[dict]:
    """Fetch active repository candidates updated during the report window."""
    if not window:
        raise ValueError("fetch_search_api requires a report window")

    start = format_utc(window["start_utc"])[:10]  # type: ignore[arg-type]
    query = f"pushed:>={start} stars:>100 archived:false fork:false"
    return search_repositories(query, sort="stars", source="search_active_stars", per_page=50)
