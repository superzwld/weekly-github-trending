# GitHub Weekly Rising Repos

Generate a weekly Markdown report of the GitHub repositories that gained the most stars during the previous full week.

This project is designed for people who want a lightweight, automated way to track fast-rising open source projects. It can run locally, write reports into an Obsidian vault, or run on GitHub Actions and commit reports back into the repository.

## Features

- Ranks repositories by weekly star growth instead of total stars.
- Uses the previous complete Monday-Sunday week as the reporting window.
- Uses GitHub Trending weekly as the primary candidate source.
- Falls back to GitHub Search API candidates when Trending does not provide enough results.
- Enriches each repository with description, language, total stars, weekly stars, growth rate, forks, author, and source.
- Outputs clean Markdown reports under `reports/`.
- Supports scheduled generation with GitHub Actions.

## Example Output

Reports are written as Markdown files such as:

```text
reports/2026-05-04  GitHub上升最快仓库周报-W19.md
```

Each report includes a Top 10 list:

```markdown
### 1. [owner/repo](https://github.com/owner/repo)

- 本周新增 star：**+15.9k**
- 当前总 star：28.3k
- 本周增长率：129.1%
- Fork：2,353
- 作者：[@owner](https://github.com/owner)
- 语言：Rust
- 来源：trending_weekly
- 简介：...
```

## How It Works

The project separates candidate discovery from ranking.

1. Candidate discovery:
   - Fetch weekly candidates from GitHub Trending.
   - Fetch active repositories from GitHub Search API as a fallback.

2. Weekly star calculation:
   - Prefer the weekly star count exposed by GitHub Trending.
   - For fallback candidates, scan stargazer timestamps with the GitHub API.

3. Ranking:
   - Sort by `weekly_stars` descending.
   - Use growth rate, source count, and total stars only as tie-breakers.

The default reporting window is the previous complete natural week in `Asia/Hong_Kong`, from Monday 00:00:00 through Sunday 23:59:59.

## Requirements

- Python 3.11+
- A GitHub token is recommended.
- Dependencies listed in `requirements.txt`.

The token can be the default `GITHUB_TOKEN` in GitHub Actions or a personal access token for local runs. No special repository permissions are required for public data reads, but authenticated requests are more reliable.

## Installation

```bash
git clone https://github.com/superzwld/weekly-github-trending.git
cd weekly-github-trending
pip install -r requirements.txt
```

Create a `.env` file:

```env
GITHUB_TOKEN=ghp_your_token_here
OUTPUT_DIR=reports
REPORT_TIMEZONE=Asia/Hong_Kong
MAX_CANDIDATES=60
STAR_SCAN_WORKERS=4
STAR_SCAN_MAX_PAGES=120
STAR_SCAN_MISSING_ONLY=1
```

## Usage

Run locally:

```bash
python main.py
```

The generated report will be written to `OUTPUT_DIR`.

You can also run the shell wrapper if you use the WSL/cron setup:

```bash
./run.sh
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `GITHUB_TOKEN` | empty | GitHub API token. Strongly recommended for reliable API calls. |
| `OUTPUT_DIR` | `reports` | Directory where Markdown reports are written. |
| `REPORT_TIMEZONE` | `Asia/Hong_Kong` | Timezone used to calculate the previous full week. |
| `MAX_CANDIDATES` | `60` | Maximum number of candidate repositories to evaluate. |
| `STAR_SCAN_WORKERS` | `4` | Number of parallel workers used when scanning stargazer timestamps. |
| `STAR_SCAN_MAX_PAGES` | `120` | Maximum stargazer pages to scan per repository. |
| `STAR_SCAN_MISSING_ONLY` | `1` | When `1`, only scan candidates that do not already have a weekly star count. |

## GitHub Actions

The included workflow runs every Monday at 00:00 UTC, which is Monday 08:00 in UTC+8:

```yaml
on:
  schedule:
    - cron: "0 0 * * 1"
```

It installs dependencies, runs `python3 main.py`, and commits newly generated reports under `reports/`.

You can also trigger it manually from the GitHub Actions tab with `workflow_dispatch`.

## Data Notes

GitHub does not provide a simple repository search sort for "stars gained this week". Repository search can filter or sort by fields such as `stars`, `forks`, `created`, `pushed`, and `updated`, but those are not the same as weekly star growth.

This project therefore uses GitHub Trending weekly as the main weekly-growth signal and API timestamp scans as a fallback. For a fully exhaustive all-GitHub ranking, a future version could use GH Archive `WatchEvent` data.

## Project Structure

```text
.
├── main.py                 # Orchestrates fetching, ranking, and report generation
├── formatter.py            # Renders Markdown reports
├── merger.py               # Deduplicates and ranks repositories
├── sources/
│   ├── github.py           # Shared GitHub API helpers
│   ├── trending.py         # GitHub Trending weekly source
│   ├── search_api.py       # Search API candidate source by stars
│   └── graphql_api.py      # Search API candidate source by forks
├── reports/                # Generated weekly reports
└── .github/workflows/      # Scheduled GitHub Actions workflow
```

## License

No license has been declared yet. Add a `LICENSE` file before redistributing or accepting external contributions.
