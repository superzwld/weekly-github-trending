"""
Obsidian Markdown 周报格式化与输出
===================================

功能说明：
  接收合并排序后的仓库 Top 10 列表，生成一份完整的 Obsidian 兼容 Markdown
  周报文件，保存到用户指定的 Obsidian Vault 目录中。

输出格式：
  - 文件名：{周一日期}  GitHub热点周报-W{ISO周号}.md
    示例：2026-04-27  GitHub热点周报-W18.md
  - YAML frontmatter：包含 tags、date、aliases 三个字段，方便 Obsidian
    通过 Dataview 等插件检索和关联
  - 正文：使用 Markdown 标题层级组织，每个仓库包含仓库名（带链接）、
    星标数、作者（带链接）、编程语言和项目简介

Obsidian 兼容性：
  - YAML frontmatter 使用 --- 包围，被 Obsidian 识别为页面元数据
  - tags 字段使周报能被 Obsidian 标签系统索引
  - aliases 字段提供中文别名，支持通过别名快速搜索
  - 文中链接使用标准 Markdown 格式，在 Obsidian 中可直接点击跳转

自定义调整：
  - 如需修改输出模板（例如增减字段、调整格式），可直接修改本文件的
    generate_report 函数中的 lines 列表
  - 如需添加更多 Obsidian frontmatter 字段（如 cssclass、publish），
    在 lines 列表的 YAML 块中追加即可
"""

import os
from datetime import date, timedelta


def _week_range(monday: date) -> tuple[date, date]:
    """
    计算自然周的起止日期。

    参数：
      monday : 周一日期

    返回：
      (周一日期, 周日日期) 元组
    """
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _format_stars(num: int) -> str:
    """
    格式化星标数，使其更适合阅读。

    规则：
      - 大于等于 10000：显示为 X.Xk 格式（如 15.2k）
      - 小于 10000：使用千位分隔符（如 5,641）
    """
    if num >= 10000:
        return f"{num/1000:.1f}k"
    return f"{num:,}"


def generate_report(repos: list[dict], output_dir: str) -> str:
    """
    生成 Obsidian 兼容的 Markdown 周报文件并保存到指定目录。

    参数：
      repos      : 已排序的仓库 Top 10 列表（由 merger.merge_and_rank 产出）
      output_dir : Obsidian Vault 的目标目录（从 .env 的 OUTPUT_DIR 读取）

    返回：
      成功时返回生成文件的完整路径
      失败时（目录不可写、磁盘满等）返回空字符串

    文件命名规则：
      {周一日期}  GitHub热点周报-W{ISO周号}.md
      周一日期和 ISO 周号均根据系统当前日期自动计算。
    """
    today = date.today()
    # 计算本周一的日期（Python 的 weekday(): 周一=0, 周日=6）
    monday = today - timedelta(days=today.weekday())
    week_start, week_end = _week_range(monday)
    iso_week = monday.isocalendar()[1]

    # 构造文件名：日期在前，方便在文件管理器中按时间排序
    filename = f"{week_start.isoformat()}  GitHub热点周报-W{iso_week}.md"
    filepath = os.path.join(output_dir, filename)

    # ===== 组装 Markdown 内容 =====

    # Part 1: YAML frontmatter（Obsidian 元数据块）
    lines = [
        "---",
        f'tags: [github-trending, weekly, "2026-W{iso_week}"]',
        f"date: {week_start.isoformat()}",
        f'aliases: ["GitHub热点周报 Week {iso_week}"]',
        "---",
        "",
    ]

    # Part 2: 标题与统计区间
    lines += [
        f"# GitHub 热点周报 — Week {iso_week} ({week_start:%m/%d} - {week_end:%m/%d})",
        "",
        f"> 统计区间：{week_start} ~ {week_end}",
        "",
        "## Top 10 本周最热仓库",
        "",
    ]

    # Part 3: 逐个仓库信息
    for i, repo in enumerate(repos, 1):
        total = _format_stars(repo["total_stars"])
        lang = repo["language"] or "未知"
        desc = repo["description"] or "(暂无描述)"

        lines.append(f"### {i}. [{repo['full_name']}]({repo['url']})")
        lines.append("")
        lines.append(f"- ⭐ **星标** {total}")
        lines.append(f"- 👤 **作者** [@{repo['owner']}](https://github.com/{repo['owner']})")
        lines.append(f"- 🗣 **语言** {lang}")
        lines.append(f"- 📝 {desc}")
        lines.append("")

    # Part 4: 页脚（生成时间和数据来源说明）
    gen_time = today.strftime("%Y-%m-%d %H:%M CST")
    lines.append("---")
    lines.append(f"*🤖 自动生成于 {gen_time} | 数据来源: GitHub Search API + GraphQL API*")
    lines.append(f"*📁 共合并来自 3 个数据源的 {len(repos)} 个热门仓库*")

    # ===== 写入文件 =====
    try:
        # 确保目标目录存在（exist_ok=True 避免竞态条件）
        os.makedirs(output_dir, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return filepath
    except OSError:
        # 可能的错误：权限不足、磁盘满、路径不存在且无法创建
        return ""
