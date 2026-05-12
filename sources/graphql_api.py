"""
数据源 3：GitHub GraphQL API — 结构化补充验证
================================================

定位说明：
  本模块通过 GitHub GraphQL API 查询与数据源 1 相同条件的热门仓库，
  作为前两个 REST API 数据源的交叉验证和补充。GraphQL 的优势在于
  可以精确指定需要返回的字段，一次请求获取恰好所需的数据，避免
  REST API 返回过多无用字段的问题。

为什么需要 GraphQL API 作为第三数据源：
  - REST Search API 返回的字段相对固定，某些边界情况（如空描述、
    缺失语言字段）处理不够灵活
  - GraphQL 允许我们精确定义返回结构，确保所有必要字段都得到填充
  - 作为 REST API 的对照，如果 GraphQL 和 REST 的结果有显著差异，
    可以通过查看 source_count 发现需要人工关注的异常情况
  - 三路数据源的设计确保了"多数投票"的可靠性：即使某一路数据源
    出现异常（如 API 变更、限流），其他两路仍能保证结果的可用性

技术细节：
  - GraphQL 查询中使用的字段名是 stargazerCount（无 s），这是
    GitHub GraphQL schema v4 的正确拼写，与 REST API 中的
    stargazers_count 不同，容易混淆
  - 必须携带 GITHUB_TOKEN 才能调用 GraphQL API（不支持匿名访问）
  - 如果 token 未配置，本模块直接返回空列表，不影响主流程

注意事项：
  GitHub GraphQL API 对复杂查询有节点数限制（node count limit），
  首次查询需要 30 个仓库，每个仓库展开约 7 个字段，总节点数在
  限制范围内（约 500 个节点，限制为 500,000）。如果将来需要扩大
  per_page 到更大值，需注意计算节点预算。
"""

import os
from datetime import date, timedelta

import requests


def _monday_of_this_week() -> str:
    """
    计算本周一的日期，返回 ISO 8601 格式字符串（YYYY-MM-DD）。
    """
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def fetch_graphql_api() -> list[dict]:
    """
    通过 GitHub GraphQL API 查询本周新创建的、星标数较高的仓库。

    工作流程：
      1. 检查 GITHUB_TOKEN 是否已配置（必须，否则直接返回空列表）
      2. 构造 GraphQL 查询语句和对应的变量字典
      3. 向 https://api.github.com/graphql 发送 POST 请求
      4. 解析响应中的 edges 列表，将每个 node 转为标准字典格式
      5. 遇到 errors 字段时（查询语法错误、权限不足等）返回空列表

    GraphQL 查询说明：
      - search(query, type, first) 与 REST Search API 语义一致
      - 内联片段 ... on Repository 用于限定返回字段类型
      - primaryLanguage { name } 获取主要语言名（REST API 对应字段为 language）

    错误处理：
      - 无 token：直接返回空列表（不报错，允许降级运行）
      - 网络异常：捕获 RequestException，返回空列表
      - GraphQL errors：检查响应中的 errors 字段，有则返回空列表
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        # GraphQL API 不支持匿名访问，必须配置 token
        return []

    monday = _monday_of_this_week()

    # GraphQL 查询：与数据源 1 的搜索条件一致
    query = """
    query($searchQuery: String!) {
      search(query: $searchQuery, type: REPOSITORY, first: 30) {
        edges {
          node {
            ... on Repository {
              nameWithOwner
              name
              description
              stargazerCount
              url
              owner { login }
              primaryLanguage { name }
            }
          }
        }
      }
    }
    """

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    variables = {
        "searchQuery": f"created:>={monday} stars:>10 sort:stars",
    }

    try:
        resp = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": query, "variables": variables},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        print(f"[graphql] 请求超时（15秒），请检查网络连接")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"[graphql] API 返回错误: {e.response.status_code} - {e.response.text[:300] if e.response else '无响应体'}")
        return []
    except requests.RequestException as e:
        print(f"[graphql] 请求失败: {e}")
        return []

    # GraphQL 即使 HTTP 200 也可能包含业务错误
    if "errors" in data:
        return []

    # 从嵌套的 edges → node 结构中提取仓库信息
    results = []
    for edge in data.get("data", {}).get("search", {}).get("edges", []):
        node = edge["node"]
        results.append({
            "full_name": node["nameWithOwner"],
            "name": node["name"],
            "owner": node["owner"]["login"],
            "description": (node.get("description") or "").strip(),
            # primaryLanguage 可能为 null（仓库未检测到语言）
            "language": (node.get("primaryLanguage") or {}).get("name", "") if node.get("primaryLanguage") else "",
            "total_stars": node["stargazerCount"],
            "weekly_stars": None,
            "url": node["url"],
            "source": "graphql",
        })

    return results
