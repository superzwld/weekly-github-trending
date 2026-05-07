"""
数据源 1：GitHub Search API — 本周新仓库 × Stars 排序
========================================================

定位说明：
  本模块使用 GitHub REST Search API，查询在本周（自然周，周一~周日）内
  新创建的、且星标数超过 10 的开源仓库，按星标数降序排列返回前 30 个。

为什么选择 "本周新创建" 作为第一数据源：
  - 一个仓库如果在本周刚创建就获得了大量 Stars，说明它在极短时间内引发
    了社区关注，这是最直接的"热点"信号
  - 与 GitHub Trending 页面的逻辑一致：Trending 页面展示的也是"近期"
    表现突出的仓库，而非历史上总星标数最多的仓库

查询参数说明：
  - created:>=周一日期  —— 限定只查本周新创建的仓库
  - stars:>10           —— 过滤掉星标数过低的噪音仓库
  - sort:stars          —— 按星标数降序排列
  - order:desc          —— 降序
  - per_page:30         —— 每页 30 条，为后续合并提供足够样本

认证说明：
  - 调用 GitHub Search API 需要认证（Personal Access Token）
  - 有 Token 时请求频率限制为 5000 次/小时，足够日常使用
  - 无 Token 时降级到 60 次/小时（不推荐，仅用于调试）

返回值格式：
  每个仓库以字典形式返回，字段包括：
    full_name    — 仓库全名，如 "nexu-io/open-design"
    name         — 仓库名，如 "open-design"
    owner        — 所有者，如 "nexu-io"
    description  — 项目简介文字
    language     — 主要编程语言
    total_stars  — 总星标数
    weekly_stars — 本周新增星标数（当前实现置 None，因为 Search API
                   不直接提供增量数据；对于本周新建仓库，total_stars
                   实际上就等于 weekly_stars）
    url          — 仓库 GitHub 页面 URL
    source       — 数据源标签，固定为 "search_new"
"""

import os
from datetime import date, timedelta

import requests


def _monday_of_this_week() -> str:
    """
    计算本周一的日期，返回 ISO 8601 格式字符串（YYYY-MM-DD）。

    算法说明：
      Python date.weekday() 返回 0（周一）到 6（周日），
      当天日期减去 weekday() 天即可得到周一的日期。
      例如：周四（weekday=3）→ 减去 3 天 → 本周一。
    """
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def fetch_trending() -> list[dict]:
    """
    从 GitHub Search API 获取本周新创建的、按星标数排序的热门仓库。

    工作流程：
      1. 计算本周一的日期（作为查询的时间下界）
      2. 构造 GitHub Search API 请求，查询 created>=周一 的仓库
      3. 发送 HTTP GET 请求，解析 JSON 响应
      4. 提取每个仓库的关键字段，组装为统一格式的字典列表
      5. 请求失败时（网络异常、限流等）返回空列表，不影响主流程

    错误处理：
      - 网络超时（15 秒）：捕获 RequestException，返回空列表
      - API 返回错误状态码：raise_for_status 触发异常，同样返回空列表
      - 这种设计确保单个数据源失败不会中断整个周报生成流程
    """
    token = os.getenv("GITHUB_TOKEN", "")
    monday = _monday_of_this_week()

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    # 如果配置了 Token，添加认证头以获得更高的请求频率配额
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # 构造查询参数
    params = {
        "q": f"created:>={monday} stars:>10",
        "sort": "stars",
        "order": "desc",
        "per_page": 30,
    }

    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            headers=headers,
            params=params,
            timeout=15,  # 15 秒超时，避免无限等待
        )
        resp.raise_for_status()  # 非 2xx 状态码抛出异常
        data = resp.json()
    except requests.RequestException:
        # 网络错误或 API 异常：静默处理，返回空列表
        return []

    # 解析搜索结果，提取仓库信息
    results = []
    for item in data.get("items", []):
        results.append({
            "full_name": item["full_name"],
            "name": item["name"],
            "owner": item["owner"]["login"],
            "description": (item.get("description") or "").strip(),
            "language": item.get("language") or "",
            "total_stars": item["stargazers_count"],
            "weekly_stars": None,  # Search API 不提供增量数据
            "url": item["html_url"],
            "source": "search_new",
        })

    return results
