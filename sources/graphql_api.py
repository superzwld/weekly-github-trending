"""Candidate source: recently active repositories sorted by forks."""

from __future__ import annotations

from .github import format_utc, search_repositories


def fetch_graphql_api(window: dict[str, object] | None = None) -> list[dict]:
    """Fetch an additional active candidate set using fork count as the signal.

    The historical module used GraphQL as a duplicate of the star search. Keeping
    the public function name avoids touching the scheduler while making this a
    genuinely different candidate source.
    """
    if not window:
        raise ValueError("fetch_graphql_api requires a report window")

    start = format_utc(window["start_utc"])[:10]  # type: ignore[arg-type]
    query = f"pushed:>={start} stars:>100 archived:false fork:false"
    return search_repositories(query, sort="forks", source="search_active_forks", per_page=50)
