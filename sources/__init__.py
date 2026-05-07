"""
数据源包 (sources)
===================

本包包含三个 GitHub 数据源模块，各自从不同维度获取本周热门仓库：

  trending.py   — 数据源 1：REST Search API，按 Stars 排序的新仓库
  search_api.py — 数据源 2：REST Search API，按 Forks 排序的新仓库
  graphql_api.py — 数据源 3：GraphQL API，结构化补充查询

所有模块对外暴露统一的 fetch_*() 函数，返回统一格式的仓库字典列表。
main.py 通过 ThreadPoolExecutor 并行调用这三个函数，由 merger.py
负责合并去重排序。

对外接口：
  from sources import fetch_trending, fetch_search_api, fetch_graphql_api
"""

from sources.trending import fetch_trending
from sources.search_api import fetch_search_api
from sources.graphql_api import fetch_graphql_api
