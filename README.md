# GitHub Weekly Rising Repos

每周生成一份 GitHub 过去一周上升最快仓库的 Markdown 周报，适合放进 Obsidian 或提交到 `reports/` 目录归档。

当前仓库已经按下面的口径实现：先发现候选仓库，再计算候选仓库在上一完整自然周内的真实新增 star，最后按 `weekly_stars` 排序输出周报。

## 目标

每周固定生成一份榜单，回答这个问题：

> 在刚刚结束的完整自然周里，GitHub 上哪些公开仓库获得了最多新增 star？

这里的“上升最快”优先定义为绝对新增 star 数，而不是总 star 数、创建时间、fork 总数或更新时间。

## 统计口径

- 统计周期：上一完整自然周，周一 00:00:00 到周日 23:59:59。
- 时区：默认使用 `Asia/Hong_Kong`，也就是 UTC+8。
- 运行时间：建议每周一 08:00 执行，统计上一个完整周。
- 入榜对象：GitHub public repository，默认排除 fork、archived、disabled 仓库。
- 主排序指标：`weekly_stars`，即统计周期内新增 star 数。
- 次排序指标：`weekly_growth_rate`、`total_stars`、`fork_delta` 可作为并列时参考，但不能替代 `weekly_stars`。
- 输出数量：默认 Top 10，后续可配置。

## 输出内容

每个仓库至少包含：

- 排名
- 仓库名和 GitHub 链接
- 简介
- 主要语言
- 当前总 star
- 本周新增 star
- 本周增长率
- fork 数或本周新增 fork 数
- 数据来源和统计时间窗口

周报文件命名建议：

```text
YYYY-MM-DD  GitHub上升最快仓库周报-WNN.md
```

其中 `YYYY-MM-DD` 是统计周的周一日期。

## 推荐的数据方案

GitHub Search API 可以按总 stars、forks 或 updated 排序，也可以用 `created` / `pushed` 按时间过滤，但它不能直接查询“过去一周新增了多少 star”。所以正确实现需要把“候选发现”和“增量计算”分开。

推荐方案：

1. 发现候选仓库
   - 使用 GitHub Trending weekly 页面作为主候选源。
   - 当 Trending weekly 不足 10 个时，使用 GitHub Search API 补充活跃仓库候选，例如 `pushed:>=上周一 stars:>100 archived:false fork:false`。
   - 可选接入 GH Archive / BigQuery 的 `WatchEvent`，直接按 star 事件统计全站榜单。

2. 计算真实新增 star
   - 对候选仓库读取 stargazers 时间线，使用 `application/vnd.github.star+json` 获取 `starred_at`。
   - 或维护本地快照：每周保存候选仓库的总 star，下周用快照差值计算 `weekly_stars`。
   - 对 Top N 结果做二次校验，避免只靠页面文案或搜索排序。

3. 排序和过滤
   - 主排序必须是 `weekly_stars desc`。
   - `total_stars` 只能作为展示字段或并列时的 tie-breaker。
   - 增加异常过滤：明显盗版、破解、恶意、刷星嫌疑、无代码空仓库等应降权或排除。

## 已修复的旧问题

### 1. 把“过去一周上升最快”误写成“本周新创建”

旧实现的三个数据源都在查询当前自然周周一之后创建的仓库：

```text
created:>=本周一 stars:>10
```

这会漏掉绝大多数真正上升最快的仓库，因为爆火仓库通常不是本周刚创建，而是在过去一周集中获得新增 star。

现在已经改为统计上一完整自然周，并用 `starred_at` 计算候选仓库在窗口内的新增 star。

### 2. 运行窗口用的是“本周”，不是“过去一周”

如果任务在周一早上执行，`_monday_of_this_week()` 会返回当天日期。也就是说，周一 08:00 运行时只统计从当天 00:00 到 08:00 创建的新仓库，而不是上一个完整周。

日志里已经出现过这个现象：2026-05-11 运行时三个数据源都只拿到 2 个仓库。

### 3. 排序按总 star，不按新增 star

旧合并排序使用的是：

```python
key=lambda r: (r["total_stars"], r["source_count"])
```

但 `weekly_stars` 在所有数据源里都是 `None`，没有被计算，也没有参与排序。这会导致榜单变成“候选集合里的总 star 排行”，不是“上升最快排行”。现在排序已经改成 `weekly_stars desc`。

### 4. GraphQL 不是独立数据源

旧 GraphQL 查询条件和 Stars 数据源基本相同，只是换了接口。因此它不能真正提供交叉验证，反而会让相同结果获得更高的 `source_count`。现在保留原函数名以兼容主流程，但改成按 forks 排序的活跃仓库候选源。

### 5. Fork 数据没有真正进入评分

旧 `sources/search_api.py` 按 forks 排序拿候选，但返回结构没有保存 fork 数，`merger.py` 也没有用 fork 数排序。现在会保存 fork 数，并在 `weekly_stars` 并列后作为辅助信息展示。

### 6. 报告元数据有年份硬编码

旧 `formatter.py` 里 tags 使用了 `2026-W{iso_week}`。现在改为根据统计周的 ISO year 生成。

## 后续增强

1. 接入 GH Archive 的 `WatchEvent` 作为全站 star 事件来源。
2. 每周保存快照和原始数据，支持复算。
3. 增加异常仓库过滤和人工 review list。
4. 为核心逻辑加测试：时间窗口、去重、排序、报告字段。

## 本地运行

创建 `.env`：

```env
GITHUB_TOKEN=ghp_xxx
OUTPUT_DIR=reports
REPORT_TIMEZONE=Asia/Hong_Kong
MAX_CANDIDATES=60
STAR_SCAN_WORKERS=4
STAR_SCAN_MAX_PAGES=120
STAR_SCAN_MISSING_ONLY=1
```

安装依赖：

```bash
pip install -r requirements.txt
```

运行：

```bash
python main.py
```

GitHub Actions 会在每周一 00:00 UTC 触发，也就是 UTC+8 的周一 08:00。

## 参考

- [GitHub repository search qualifiers](https://github.com/github/docs/blob/main/content/search-github/searching-on-github/searching-for-repositories.md)：支持 `created`、`pushed`、`stars`、`forks` 等过滤，但这些都是仓库当前状态或时间过滤，不是“窗口内新增 star”指标。
- [GitHub sorting search results](https://github.com/github/docs/blob/main/content/search-github/getting-started-with-searching-on-github/sorting-search-results.md)：仓库搜索可按 stars、forks、updated 等维度排序，但没有 weekly star growth 排序。
- [GitHub REST API list stargazers](https://docs.github.com/en/rest/activity/starring?apiVersion=2022-11-28#list-stargazers)：通过 `application/vnd.github.star+json` 可返回 `starred_at`，可用于计算候选仓库在统计窗口内获得的新增 star。
