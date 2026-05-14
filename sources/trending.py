"""Candidate source: GitHub Trending repositories for the weekly period."""

from __future__ import annotations

import re
import time

import requests
from bs4 import BeautifulSoup

from .github import github_headers


def _parse_weekly_stars(text: str) -> int:
    match = re.search(r"([\d,]+)\s+stars?\s+this\s+week", text, flags=re.IGNORECASE)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def _repo_metadata(full_name: str, weekly_hint: int) -> dict | None:
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{full_name}",
            headers=github_headers(),
            timeout=20,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[trending_weekly] {full_name} 元数据请求失败: {exc}")
        return None

    item = resp.json()
    return {
        "full_name": item["full_name"],
        "name": item["name"],
        "owner": item["owner"]["login"],
        "description": (item.get("description") or "").strip(),
        "language": item.get("language") or "",
        "total_stars": int(item.get("stargazers_count") or 0),
        "weekly_stars": 0,
        "weekly_stars_hint": weekly_hint,
        "weekly_stars_estimated": False,
        "weekly_growth_rate": 0.0,
        "forks_count": int(item.get("forks_count") or 0),
        "url": item["html_url"],
        "source": "trending_weekly",
    }


def fetch_trending() -> list[dict]:
    """Fetch weekly GitHub Trending candidates and their current metadata."""
    resp = None
    for attempt in range(1, 4):
        try:
            resp = requests.get(
                "https://github.com/trending",
                params={"since": "weekly"},
                headers={"User-Agent": "weekly-github-rising-repos"},
                timeout=60,
            )
            resp.raise_for_status()
            break
        except requests.RequestException as exc:
            print(f"[trending_weekly] 页面请求失败({attempt}/3): {exc}")
            if attempt == 3:
                return []
            time.sleep(3 * attempt)

    soup = BeautifulSoup(resp.text, "html.parser")
    repos: list[dict] = []
    for article in soup.select("article.Box-row"):
        link = article.select_one("h2 a")
        if not link:
            continue
        parts = [part.strip() for part in link.get_text("/", strip=True).split("/") if part.strip()]
        if len(parts) != 2:
            continue
        full_name = "/".join(parts)
        weekly_hint = _parse_weekly_stars(article.get_text(" ", strip=True))
        repo = _repo_metadata(full_name, weekly_hint)
        if repo:
            repos.append(repo)

    return repos
