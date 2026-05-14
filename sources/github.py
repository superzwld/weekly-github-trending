"""Shared GitHub API helpers for weekly rising repository reports."""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import requests

API_URL = "https://api.github.com"
DEFAULT_TIMEZONE = "Asia/Hong_Kong"


def github_headers(accept: str = "application/vnd.github+json") -> dict[str, str]:
    headers = {
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "weekly-github-rising-repos",
    }
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def previous_week_window(tz_name: str | None = None) -> dict[str, object]:
    """Return the previous complete Monday-Sunday week in local and UTC forms."""
    tz = ZoneInfo(tz_name or os.getenv("REPORT_TIMEZONE", DEFAULT_TIMEZONE))
    today = datetime.now(tz).date()
    current_monday = today - timedelta(days=today.weekday())
    week_start = current_monday - timedelta(days=7)
    week_end = current_monday - timedelta(days=1)

    start_local = datetime.combine(week_start, time.min, tzinfo=tz)
    end_exclusive_local = start_local + timedelta(days=7)

    return {
        "timezone": tz.key,
        "week_start": week_start,
        "week_end": week_end,
        "start_local": start_local,
        "end_exclusive_local": end_exclusive_local,
        "start_utc": start_local.astimezone(timezone.utc),
        "end_utc": end_exclusive_local.astimezone(timezone.utc),
    }


def parse_github_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_from_search_item(item: dict, source: str, weekly_stars_hint: int = 0) -> dict:
    return {
        "full_name": item["full_name"],
        "name": item["name"],
        "owner": item["owner"]["login"],
        "description": (item.get("description") or "").strip(),
        "language": item.get("language") or "",
        "total_stars": int(item.get("stargazers_count") or 0),
        "weekly_stars": 0,
        "weekly_stars_hint": weekly_stars_hint,
        "weekly_stars_estimated": False,
        "weekly_growth_rate": 0.0,
        "forks_count": int(item.get("forks_count") or item.get("forks") or 0),
        "url": item["html_url"],
        "source": source,
    }


def search_repositories(query: str, sort: str, source: str, per_page: int = 30) -> list[dict]:
    params = {
        "q": query,
        "sort": sort,
        "order": "desc",
        "per_page": per_page,
    }

    try:
        resp = requests.get(
            f"{API_URL}/search/repositories",
            headers=github_headers(),
            params=params,
            timeout=20,
        )
        resp.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        body = exc.response.text[:300] if exc.response is not None else "无响应体"
        print(f"[{source}] API 返回错误: {exc.response.status_code} - {body}")
        return []
    except requests.RequestException as exc:
        print(f"[{source}] 请求失败: {exc}")
        return []

    return [repo_from_search_item(item, source) for item in resp.json().get("items", [])]


def parse_link_header(value: str) -> dict[str, str]:
    links: dict[str, str] = {}
    matches = re.finditer(r'<([^>]+)>;\s*rel="([^"]+)"', value)
    for match in matches:
        links[match.group(2)] = match.group(1)
    return links


def page_number_from_url(url: str | None) -> int | None:
    if not url:
        return None
    page = parse_qs(urlparse(url).query).get("page", [None])[0]
    return int(page) if page and page.isdigit() else None


def count_weekly_stars(
    full_name: str,
    start_utc: datetime,
    end_utc: datetime,
    max_pages: int,
) -> tuple[int, bool, int]:
    if os.getenv("GITHUB_TOKEN"):
        return count_weekly_stars_graphql(full_name, start_utc, end_utc, max_pages)
    return count_weekly_stars_rest(full_name, start_utc, end_utc, max_pages)


def count_weekly_stars_graphql(
    full_name: str,
    start_utc: datetime,
    end_utc: datetime,
    max_pages: int,
) -> tuple[int, bool, int]:
    owner, name = full_name.split("/", 1)
    query = """
    query($owner: String!, $name: String!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        stargazers(first: 100, after: $cursor, orderBy: {field: STARRED_AT, direction: DESC}) {
          edges {
            starredAt
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """
    cursor = None
    count = 0
    pages_scanned = 0

    while pages_scanned < max_pages:
        pages_scanned += 1
        try:
            resp = requests.post(
                f"{API_URL}/graphql",
                headers=github_headers(),
                json={
                    "query": query,
                    "variables": {"owner": owner, "name": name, "cursor": cursor},
                },
                timeout=20,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[stargazers] {full_name} GraphQL 请求失败: {exc}")
            return count, True, pages_scanned

        data = resp.json()
        if data.get("errors"):
            print(f"[stargazers] {full_name} GraphQL 返回错误: {data['errors'][:1]}")
            return count, True, pages_scanned

        stargazers = data.get("data", {}).get("repository", {}).get("stargazers")
        if not stargazers:
            return count, True, pages_scanned

        saw_before_start = False
        for edge in stargazers.get("edges", []):
            starred_at = parse_github_datetime(edge["starredAt"])
            if start_utc <= starred_at < end_utc:
                count += 1
            elif starred_at < start_utc:
                saw_before_start = True

        if saw_before_start:
            return count, False, pages_scanned

        page_info = stargazers.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            return count, False, pages_scanned
        cursor = page_info.get("endCursor")

    return count, True, pages_scanned


def count_weekly_stars_rest(
    full_name: str,
    start_utc: datetime,
    end_utc: datetime,
    max_pages: int,
) -> tuple[int, bool, int]:
    """Count stargazer events within [start_utc, end_utc).

    GitHub returns stargazers oldest-first. We fetch page 1 to discover the last
    page, then scan backward until we reach stars older than the report window.
    """
    url = f"{API_URL}/repos/{full_name}/stargazers"
    params = {"per_page": 100, "page": 1}
    headers = github_headers("application/vnd.github.star+json")

    try:
        first_resp = requests.get(url, headers=headers, params=params, timeout=20)
        first_resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[stargazers] {full_name} 请求失败: {exc}")
        return 0, True, 0

    links = parse_link_header(first_resp.headers.get("Link", ""))
    last_page = page_number_from_url(links.get("last")) or 1

    count = 0
    pages_scanned = 0

    for page in range(last_page, 0, -1):
        pages_scanned += 1
        if page == 1:
            resp = first_resp
        else:
            try:
                resp = requests.get(
                    url,
                    headers=headers,
                    params={"per_page": 100, "page": page},
                    timeout=20,
                )
                resp.raise_for_status()
            except requests.RequestException as exc:
                print(f"[stargazers] {full_name} 第 {page} 页请求失败: {exc}")
                return count, True, pages_scanned

        saw_before_start = False
        for item in resp.json():
            starred_at = parse_github_datetime(item["starred_at"])
            if start_utc <= starred_at < end_utc:
                count += 1
            elif starred_at < start_utc:
                saw_before_start = True

        if saw_before_start:
            return count, False, pages_scanned
        if pages_scanned >= max_pages:
            return count, True, pages_scanned

    return count, False, pages_scanned


def enrich_weekly_stars(
    repos: Iterable[dict],
    window: dict[str, object],
    max_workers: int = 4,
    max_pages: int = 120,
    scan_missing_only: bool = True,
) -> list[dict]:
    enriched = [dict(repo) for repo in repos]
    start_utc = window["start_utc"]
    end_utc = window["end_utc"]

    def enrich(repo: dict) -> dict:
        hint = int(repo.get("weekly_stars_hint") or 0)
        if scan_missing_only and hint:
            repo["weekly_stars"] = hint
            repo["weekly_stars_estimated"] = False
            previous_total = max(int(repo.get("total_stars", 0)) - repo["weekly_stars"], 0)
            repo["weekly_growth_rate"] = (
                repo["weekly_stars"] / previous_total if previous_total else float(repo["weekly_stars"] > 0)
            )
            repo["stargazer_pages_scanned"] = 0
            return repo

        weekly, truncated, pages = count_weekly_stars(
            repo["full_name"],
            start_utc,  # type: ignore[arg-type]
            end_utc,  # type: ignore[arg-type]
            max_pages=max_pages,
        )
        repo["weekly_stars"] = max(weekly, hint) if truncated and hint else weekly
        repo["weekly_stars_estimated"] = bool(truncated and hint and hint > weekly)
        previous_total = max(int(repo.get("total_stars", 0)) - repo["weekly_stars"], 0)
        repo["weekly_growth_rate"] = (
            repo["weekly_stars"] / previous_total if previous_total else float(repo["weekly_stars"] > 0)
        )
        repo["stargazer_pages_scanned"] = pages
        return repo

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(enrich, repo): repo["full_name"] for repo in enriched}
        completed = []
        for future in as_completed(futures):
            repo = future.result()
            completed.append(repo)
            if repo["stargazer_pages_scanned"]:
                print(
                    f"[stargazers] {repo['full_name']} +{repo['weekly_stars']} "
                    f"stars ({repo['stargazer_pages_scanned']} 页)"
                )
            else:
                print(f"[trending_hint] {repo['full_name']} +{repo['weekly_stars']} stars")

    return completed
