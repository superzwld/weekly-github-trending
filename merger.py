"""Merge, de-duplicate, and rank weekly rising GitHub repositories."""


def _merge_repo(existing: dict, repo: dict) -> None:
    if len(repo.get("description", "")) > len(existing.get("description", "")):
        existing["description"] = repo["description"]

    if repo.get("language") and not existing.get("language"):
        existing["language"] = repo["language"]

    for field in ("total_stars", "weekly_stars", "forks_count", "weekly_stars_hint"):
        existing[field] = max(int(existing.get(field) or 0), int(repo.get(field) or 0))

    existing["weekly_stars_estimated"] = (
        bool(existing.get("weekly_stars_estimated")) or bool(repo.get("weekly_stars_estimated"))
    )
    existing["source_count"] += 1
    existing["sources"].add(repo["source"])

    previous_total = max(int(existing.get("total_stars", 0)) - int(existing.get("weekly_stars", 0)), 0)
    existing["weekly_growth_rate"] = (
        existing["weekly_stars"] / previous_total if previous_total else float(existing["weekly_stars"] > 0)
    )


def merge_and_rank(*repo_lists: list[dict], top_n: int = 10) -> list[dict]:
    """Return Top N repositories ranked by stars gained in the report window."""
    merged: dict[str, dict] = {}

    for repo_list in repo_lists:
        for repo in repo_list:
            key = repo["full_name"].lower()
            if key in merged:
                _merge_repo(merged[key], repo)
                continue

            merged[key] = {
                "full_name": repo["full_name"],
                "name": repo["name"],
                "owner": repo["owner"],
                "description": repo.get("description", ""),
                "language": repo.get("language", ""),
                "total_stars": int(repo.get("total_stars") or 0),
                "weekly_stars": int(repo.get("weekly_stars") or 0),
                "weekly_stars_hint": int(repo.get("weekly_stars_hint") or 0),
                "weekly_stars_estimated": bool(repo.get("weekly_stars_estimated")),
                "weekly_growth_rate": float(repo.get("weekly_growth_rate") or 0.0),
                "forks_count": int(repo.get("forks_count") or 0),
                "url": repo["url"],
                "source_count": 1,
                "sources": {repo["source"]},
            }

    ranked = sorted(
        (repo for repo in merged.values() if repo["weekly_stars"] > 0),
        key=lambda r: (
            r["weekly_stars"],
            r["weekly_growth_rate"],
            r["source_count"],
            r["total_stars"],
        ),
        reverse=True,
    )

    return ranked[:top_n]
