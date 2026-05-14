#!/usr/bin/env python3
"""Generate a weekly report of GitHub repositories with the fastest star growth."""

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

from formatter import generate_report
from merger import merge_and_rank
from sources.github import enrich_weekly_stars, previous_week_window
from sources.graphql_api import fetch_graphql_api
from sources.search_api import fetch_search_api
from sources.trending import fetch_trending


def _merge_candidates(repo_lists: list[list[dict]]) -> list[dict]:
    merged: dict[str, dict] = {}
    for repo_list in repo_lists:
        for repo in repo_list:
            key = repo["full_name"].lower()
            if key not in merged:
                merged[key] = repo
                continue

            existing = merged[key]
            if len(repo.get("description", "")) > len(existing.get("description", "")):
                existing["description"] = repo["description"]
            if repo.get("language") and not existing.get("language"):
                existing["language"] = repo["language"]
            existing["total_stars"] = max(existing.get("total_stars", 0), repo.get("total_stars", 0))
            existing["forks_count"] = max(existing.get("forks_count", 0), repo.get("forks_count", 0))
            existing["weekly_stars_hint"] = max(
                existing.get("weekly_stars_hint", 0),
                repo.get("weekly_stars_hint", 0),
            )
            existing.setdefault("sources", {existing["source"]}).add(repo["source"])

    candidates = []
    for repo in merged.values():
        sources = repo.get("sources", {repo["source"]})
        repo["source"] = "+".join(sorted(sources))
        candidates.append(repo)
    return candidates


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(script_dir, ".env"))

    output_dir = os.getenv("OUTPUT_DIR", "reports")
    window = previous_week_window()

    print(f"GITHUB_TOKEN: {'已配置' if os.getenv('GITHUB_TOKEN') else '未配置，API 请求将受限'}")
    print(f"输出目录: {output_dir}")
    print(
        "统计区间: "
        f"{window['week_start']} ~ {window['week_end']} ({window['timezone']})"
    )

    sources = {
        "GitHub Trending weekly": lambda: fetch_trending(),
        "Search active by stars": lambda: fetch_search_api(window),
        "Search active by forks": lambda: fetch_graphql_api(window),
    }

    results_by_name: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fn): name for name, fn in sources.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                repos = future.result()
                results_by_name[name] = repos
                print(f"[{name}] 获取 {len(repos)} 个候选仓库")
            except Exception as exc:
                print(f"[{name}] 请求失败: {exc}")

    trending_candidates = results_by_name.get("GitHub Trending weekly", [])
    supplemental_candidates = (
        results_by_name.get("Search active by stars", [])
        + results_by_name.get("Search active by forks", [])
    )
    if len(trending_candidates) >= 10:
        results = [trending_candidates]
        print("Trending weekly 候选已足够，Search API 仅作为备用未进入本次榜单")
    else:
        results = [trending_candidates, supplemental_candidates]
        print("Trending weekly 候选不足 10 个，加入 Search API 补充候选")

    candidates = _merge_candidates(results)
    if not candidates:
        print("错误：没有获取到候选仓库")
        sys.exit(1)

    max_candidates = int(os.getenv("MAX_CANDIDATES", "60"))
    max_workers = int(os.getenv("STAR_SCAN_WORKERS", "4"))
    max_pages = int(os.getenv("STAR_SCAN_MAX_PAGES", "120"))
    scan_missing_only = os.getenv("STAR_SCAN_MISSING_ONLY", "1") != "0"
    candidates = sorted(
        candidates,
        key=lambda repo: (
            int(repo.get("weekly_stars_hint") or 0),
            int(repo.get("total_stars") or 0),
            int(repo.get("forks_count") or 0),
        ),
        reverse=True,
    )[:max_candidates]
    print(f"合并去重后 {len(candidates)} 个候选仓库，开始计算上一周新增 star")

    enriched = enrich_weekly_stars(
        candidates,
        window,
        max_workers=max_workers,
        max_pages=max_pages,
        scan_missing_only=scan_missing_only,
    )
    top10 = merge_and_rank(enriched, top_n=10)

    if not top10:
        print("错误：候选仓库在统计窗口内都没有新增 star")
        sys.exit(1)

    filepath = generate_report(top10, output_dir, window)
    if not filepath:
        sys.exit(1)

    print(f"\n周报已生成: {filepath}")
    print("\nTop 10 上升最快仓库:")
    for index, repo in enumerate(top10, 1):
        print(
            f"  {index:2}. {repo['full_name']} +{repo['weekly_stars']:,} "
            f"stars，总 star {repo['total_stars']:,}"
        )


if __name__ == "__main__":
    main()
