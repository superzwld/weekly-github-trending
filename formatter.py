"""Render the weekly rising repository report as Markdown."""

import os
from datetime import datetime


def _format_number(num: int) -> str:
    if num >= 10000:
        return f"{num / 1000:.1f}k"
    return f"{num:,}"


def _format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def generate_report(repos: list[dict], output_dir: str, window: dict[str, object]) -> str:
    week_start = window["week_start"]
    week_end = window["week_end"]
    timezone_name = window["timezone"]
    iso_year, iso_week, _ = week_start.isocalendar()

    filename = f"{week_start.isoformat()}  GitHub上升最快仓库周报-W{iso_week}.md"
    filepath = os.path.join(output_dir, filename)

    lines = [
        "---",
        f'tags: [github-trending, weekly, "{iso_year}-W{iso_week}"]',
        f"date: {week_start.isoformat()}",
        f'aliases: ["GitHub上升最快仓库周报 Week {iso_week}"]',
        "---",
        "",
        f"# GitHub 上升最快仓库周报 — Week {iso_week} ({week_start:%m/%d} - {week_end:%m/%d})",
        "",
        f"> 统计区间：{week_start} ~ {week_end} ({timezone_name})",
        "> 排名依据：统计区间内新增 star 数，按 `weekly_stars` 降序排列。",
        "",
        "## Top 10 上升最快仓库",
        "",
    ]

    for index, repo in enumerate(repos, 1):
        total = _format_number(repo["total_stars"])
        weekly = _format_number(repo["weekly_stars"])
        forks = _format_number(repo.get("forks_count", 0))
        growth = _format_percent(repo.get("weekly_growth_rate", 0.0))
        lang = repo["language"] or "未知"
        desc = repo["description"] or "(暂无描述)"
        estimate = "（估算）" if repo.get("weekly_stars_estimated") else ""
        sources = ", ".join(sorted(repo.get("sources", [])))

        lines.append(f"### {index}. [{repo['full_name']}]({repo['url']})")
        lines.append("")
        lines.append(f"- 本周新增 star：**+{weekly}**{estimate}")
        lines.append(f"- 当前总 star：{total}")
        lines.append(f"- 本周增长率：{growth}")
        lines.append(f"- Fork：{forks}")
        lines.append(f"- 作者：[@{repo['owner']}](https://github.com/{repo['owner']})")
        lines.append(f"- 语言：{lang}")
        lines.append(f"- 来源：{sources}")
        lines.append(f"- 简介：{desc}")
        lines.append("")

    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append("---")
    lines.append(f"*自动生成于 {gen_time} | 数据来源: GitHub Trending weekly + GitHub REST/GraphQL API*")
    lines.append(f"*共合并候选源后输出 {len(repos)} 个仓库，最终按统计窗口内新增 star 排序。*")

    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as file:
            file.write("\n".join(lines))
        return filepath
    except OSError as exc:
        print(f"写入周报失败: {exc}")
        return ""
