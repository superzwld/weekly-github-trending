"""
数据源 2：GitHub Search API — 本周新仓库 × Forks 排序
========================================================

定位说明：
  本模块同样使用 GitHub REST Search API，查询条件与数据源 1 完全相同
  （本周新创建的、星标数超过 10 的仓库），但排序方式改为按 Forks
  （复刻数）降序排列。

为什么需要 "同一维度 + 不同排序" 作为第二数据源：
  - Stars（星标）反映的是"关注度"：用户看到感兴趣的项目，点一下 Star
    表示收藏或赞赏，是一种轻量的社交信号
  - Forks（复刻）反映的是"使用度"：用户只有真正打算用这个项目，才会
    Fork 一份到自己的账号下进行修改或部署，是比 Star 更重的参与信号
  - 两者从不同侧面衡量仓库的热度：有些项目宣传做得好 Star 很多但实际
    可操作性差、Fork 寥寥；有些实用工具 Star 不多但被大量 Fork 使用
  - 综合 Stars 和 Forks 两榜，能更全面地覆盖"真·热门"项目

查询参数说明：
  - created:>=周一日期  —— 与数据源 1 相同的时间窗口
  - stars:>10           —— 相同的质量门槛
  - sort:forks          —— 按 Fork 数降序排列（与数据源 1 的关键差异）
  - per_page:30         —— 每页 30 条

与数据源 1 的差异总结：
  数据源 1（trending.py）：sort=stars  → 发现"被星标最多"的新项目
  数据源 2（本文件）    ：sort=forks  → 发现"被使用最多"的新项目
  数据源 3（graphql_api）：GraphQL 查询 → 提供结构化补充验证
"""

import os
from datetime import date, timedelta

import requests


def _monday_of_this_week() -> str:
    """
    计算本周一的日期，返回 ISO 8601 格式字符串（YYYY-MM-DD）。

    与 trending.py 中的同名函数逻辑完全一致。
    """
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def fetch_search_api() -> list[dict]:
    """
    从 GitHub Search API 获取本周新创建的、按 Fork 数排序的热门仓库。

    工作流程：
      1. 计算本周一日期作为查询起点
      2. 向 GitHub Search API 发起请求，按 forks 降序排列
      3. 解析响应中的仓库列表，提取标准字段
      4. 返回统一格式的字典列表供 merger 模块合并

    与 fetch_trending() 的唯一区别是 sort 参数：
      fetch_trending()  → sort=stars
      fetch_search_api() → sort=forks
    """
    token = os.getenv("GITHUB_TOKEN", "")
    monday = _monday_of_this_week()

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # 与数据源 1 唯一的区别：sort 参数改为 forks
    params = {
        "q": f"created:>={monday} stars:>10",
        "sort": "forks",
        "order": "desc",
        "per_page": 30,
    }

    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            headers=headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return []

    results = []
    for item in data.get("items", []):
        results.append({
            "full_name": item["full_name"],
            "name": item["name"],
            "owner": item["owner"]["login"],
            "description": (item.get("description") or "").strip(),
            "language": item.get("language") or "",
            "total_stars": item["stargazers_count"],
            "weekly_stars": None,
            "url": item["html_url"],
            "source": "search_forks",
        })

    return results
