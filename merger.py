"""
三路数据源合并、去重与排序引擎
================================

功能说明：
  将三个 GitHub 数据源返回的仓库列表合并为统一的排行榜。由于不同数据源
  可能返回相同的仓库，需要以仓库全名（owner/repo）为唯一标识进行去重。
  同时，一个仓库被越多的数据源命中，说明它在不同维度上都表现突出，应当
  获得更高的综合排名。

合并规则（逐条说明）：
  1. 以仓库全名的小写形式作为合并主键，确保大小写差异不影响去重
  2. 当同一仓库出现在多个数据源时：
     - 保留最长的描述文本（描述更详细的来源通常数据质量更高）
     - 若主源缺少编程语言信息，从其他源补充
     - source_count 自增，sources 集合追加来源标签
  3. 合并完成后，按以下优先级排序：
     - 第一关键字：total_stars（总星标数）降序 —— 星标是最直观的热度指标
     - 第二关键字：source_count（被命中源数量）降序 —— 多源共识更可靠
  4. 截取前 top_n 个仓库作为最终结果

设计考量：
  - 如果某仓库仅出现在一个数据源中，source_count=1，不影响排名
  - 如果同时出现在 Stars 和 Forks 排行榜中，说明它既有"看热闹"的 Star
    又有"真干活"的 Fork，source_count=2 会获得加权排序优势
  - GraphQL 源查询条件与 Stars 源相同，因此两者命中相同的仓库时，
    source_count 至少为 2，这恰好是"经过双重验证"的热门项目
"""


def merge_and_rank(
    trending: list[dict],
    active: list[dict],
    graphql: list[dict],
    top_n: int = 10,
) -> list[dict]:
    """
    合并三个数据源的仓库列表，去重后按热度排序，返回 Top N。

    参数：
      trending  : 数据源 1 返回的仓库列表（按 Stars 排序的新仓库）
      active    : 数据源 2 返回的仓库列表（按 Forks 排序的新仓库）
      graphql   : 数据源 3 返回的仓库列表（GraphQL 补充数据）
      top_n     : 最终返回的仓库数量，默认 10

    返回：
      排序后的仓库字典列表，每个字典包含以下字段：
        - full_name     : 仓库全名，格式 "owner/repo"
        - name          : 仓库名（不含 owner）
        - owner         : 仓库所有者（用户或组织）
        - description   : 仓库简介
        - language      : 主要编程语言
        - total_stars   : 总星标数
        - weekly_stars  : 本周新增星标数（当前实现中为 None）
        - url           : 仓库 GitHub 页面地址
        - source_count  : 该仓库被多少个数据源命中
        - sources       : 命中的数据源标签集合
    """
    merged: dict[str, dict] = {}

    # 按顺序遍历三个数据源（后出现的与前面的合并）
    for repo_list in [trending, active, graphql]:
        for repo in repo_list:
            # 统一用小写作为去重键，避免 Manual/Repo 和 manual/repo 被视为不同
            key = repo["full_name"].lower()

            if key in merged:
                # 仓库已存在：合并补充信息
                existing = merged[key]

                # 取两者中较长的描述（更详细的优先）
                if len(repo["description"]) > len(existing["description"]):
                    existing["description"] = repo["description"]

                # 补充缺失的语言信息
                if repo["language"] and not existing["language"]:
                    existing["language"] = repo["language"]

                # 累加来源计数
                existing["source_count"] += 1
                existing["sources"].add(repo["source"])
            else:
                # 首次出现：直接录入
                merged[key] = {
                    "full_name": repo["full_name"],
                    "name": repo["name"],
                    "owner": repo["owner"],
                    "description": repo["description"],
                    "language": repo["language"],
                    "total_stars": repo["total_stars"],
                    "weekly_stars": repo["weekly_stars"],
                    "url": repo["url"],
                    "source_count": 1,
                    "sources": {repo["source"]},
                }

    # 组合排序：总星标数（主要） + 来源数量（次要），均为降序
    ranked = sorted(
        merged.values(),
        key=lambda r: (r["total_stars"], r["source_count"]),
        reverse=True,
    )

    return ranked[:top_n]
