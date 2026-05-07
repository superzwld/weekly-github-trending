#!/usr/bin/env python3
"""
GitHub 每周热点仓库报告生成器
=================================

功能说明：
  本程序从三个不同维度的数据源并行抓取 GitHub 上本周最热门的开源仓库，
  合并去重后按热度排序，取前 10 名，生成一份 Obsidian 兼容的 Markdown
  周报文件，保存到指定的 Obsidian Vault 目录中。

三路数据源：
  1. GitHub Search API — 查询本周新创建的仓库，按 Stars（星标数）降序
     排列。这是"本周新秀"视角，能发现刚诞生就受追捧的项目。
  2. GitHub Search API — 同样查询本周新创建的仓库，但按 Forks（复刻数）
     降序排列。Fork 数反映了实际使用和二次开发的活跃度，与 Stars 形成
     互补，能命中 Star 少但 Fork 多的实用项目。
  3. GitHub GraphQL API — 使用与第 1 路相同的查询条件，但通过 GraphQL
     接口获取更结构化和丰富的仓库元数据。作为前两路的交叉验证和补充。

合并排序规则：
  1. 三路结果以仓库全名（owner/repo）的小写形式为键合并去重
  2. 同一仓库被多个源命中时，保留最完整的描述信息，source_count 累加
  3. 主排序：total_stars 降序；次排序：source_count（多源命中加权）
  4. 截取前 10 名输出

定时调度：
  通过 WSL 内部 cron 直接调度，每周一早上 8:00 (CST) 自动触发。
  cron 配置：0 8 * * 1 /home/laomeo/weekly_github/run.sh
  前提条件：WSL2 实例需保持运行（systemd 已启用，cron 开机自启）

用法：
  python3 main.py          # 手动运行，立即生成当周周报
  /home/laomeo/weekly_github/run.sh   # cron 调用的 shell 包装脚本
"""

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

from sources.trending import fetch_trending
from sources.search_api import fetch_search_api
from sources.graphql_api import fetch_graphql_api
from merger import merge_and_rank
from formatter import generate_report


def main():
    """
    主流程入口。

    执行步骤：
      1. 加载 .env 配置文件，读取 GITHUB_TOKEN 和 OUTPUT_DIR
      2. 启动 3 个工作线程，并行调用三个数据源接口
      3. 等待所有接口返回后，调用 merge_and_rank 合并去重排序
      4. 调用 generate_report 生成 Obsidian 格式的 Markdown 周报
      5. 打印 Top 10 摘要到终端
    """
    # 解析 .env 配置文件（与 main.py 同目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(script_dir, ".env"))

    # 输出目录必须在 .env 中配置
    output_dir = os.getenv("OUTPUT_DIR", "")
    if not output_dir:
        print("错误：OUTPUT_DIR 未在 .env 中设置，请检查配置文件")
        sys.exit(1)

    # 定义三路数据源及其显示名称
    sources = {
        "新仓库(按Stars)": fetch_trending,
        "新仓库(按Forks)": fetch_search_api,
        "GraphQL(补充)": fetch_graphql_api,
    }

    # 使用线程池并行请求三个数据源，加快总响应速度
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fn): name for name, fn in sources.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
                print(f"[{name}] 获取 {len(results[name])} 个仓库")
            except Exception as exc:
                print(f"[{name}] 请求失败: {exc}")
                results[name] = []

    # 提取三路结果（直接用 key 名匹配）
    source_names = list(sources.keys())
    top10 = merge_and_rank(
        results.get(source_names[0], []),
        results.get(source_names[1], []),
        results.get(source_names[2], []),
        top_n=10,
    )

    if not top10:
        print("错误：所有数据源均未返回有效数据，请检查网络或 GitHub Token")
        sys.exit(1)

    # 生成 Obsidian Markdown 并写入文件
    filepath = generate_report(top10, output_dir)

    if filepath:
        print(f"\n✅ 周报已生成: {filepath}")
        print(f"\n📊 本周 Top 10 热门仓库:")
        for i, repo in enumerate(top10, 1):
            stars = repo["total_stars"]
            print(f"  {i:2}. {repo['full_name']} — ⭐{stars:,} ({repo['language'] or '未知语言'})")
    else:
        print("错误：无法写入周报文件，请检查 OUTPUT_DIR 路径是否正确")
        sys.exit(1)


if __name__ == "__main__":
    main()
