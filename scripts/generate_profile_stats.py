#!/usr/bin/env python3
"""Generate a dark-themed SVG card from GitHub's authenticated APIs."""

from datetime import datetime, time, timedelta, timezone
import html
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


USERNAME = "akshat-aetroiddestroyer"
API_ROOT = "https://api.github.com"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "profile-stats.svg"


def api_get(url: str, token: str):
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "profile-stats-generator",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response), response.headers.get("Link", "")
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"GitHub API request failed for {url}: {error}") from error


def graphql_post(query: str, variables: dict, token: str):
    request = Request(
        f"{API_ROOT}/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "profile-stats-generator",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"GitHub GraphQL request failed: {error}") from error
    if result.get("errors"):
        messages = "; ".join(
            error.get("message", "Unknown GraphQL error")
            for error in result["errors"]
            if isinstance(error, dict)
        )
        raise RuntimeError(f"GitHub GraphQL returned errors: {messages}")
    return result.get("data")


def repository_pages(token: str):
    url = f"{API_ROOT}/users/{USERNAME}/repos?type=owner&per_page=100&sort=full_name"
    visited = set()
    while url:
        parsed = urlparse(url)
        expected_path = f"/users/{USERNAME}/repos"
        if parsed.scheme != "https" or parsed.netloc != "api.github.com" or parsed.path != expected_path:
            raise RuntimeError(f"Unexpected GitHub repository pagination URL: {url}")
        if url in visited:
            raise RuntimeError(f"GitHub API pagination loop detected at {url}")
        visited.add(url)

        page, link_header = api_get(url, token)
        if not isinstance(page, list):
            raise RuntimeError("GitHub repository API returned an unexpected response.")
        yield page

        next_url = None
        for link in link_header.split(","):
            match = re.match(r'\s*<([^>]+)>\s*;\s*rel="([^"]+)"', link)
            if match and match.group(2) == "next":
                next_url = match.group(1)
                break
        url = next_url


def contribution_calendar(token: str, start_date, end_date):
    start_datetime = (
        start_date
        if isinstance(start_date, datetime)
        else datetime.combine(start_date, time.min, timezone.utc)
    )
    end_datetime = (
        end_date
        if isinstance(end_date, datetime)
        else datetime.combine(end_date, time(23, 59, 59), timezone.utc)
    )
    start_datetime = start_datetime.astimezone(timezone.utc)
    end_datetime = end_datetime.astimezone(timezone.utc)
    data = graphql_post(
        """
        query($login: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $login) {
            contributionsCollection(from: $from, to: $to) {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    date
                    contributionCount
                  }
                }
              }
            }
          }
        }
        """,
        {
            "login": USERNAME,
            "from": start_datetime.isoformat().replace("+00:00", "Z"),
            "to": end_datetime.isoformat().replace("+00:00", "Z"),
        },
        token,
    )
    try:
        calendar = data["user"]["contributionsCollection"]["contributionCalendar"]
        total_contributions = calendar["totalContributions"]
        days = [
            {
                "date": datetime.strptime(day["date"], "%Y-%m-%d").date(),
                "count": day["contributionCount"],
            }
            for week in calendar["weeks"]
            for day in week["contributionDays"]
        ]
    except (TypeError, KeyError, ValueError) as error:
        raise RuntimeError("GitHub GraphQL returned invalid contribution calendar data.") from error
    if (
        not isinstance(total_contributions, int)
        or isinstance(total_contributions, bool)
        or any(
            not isinstance(day["count"], int) or isinstance(day["count"], bool)
            for day in days
        )
    ):
        raise RuntimeError("GitHub GraphQL returned invalid contribution totals.")
    filtered_days = [
        day
        for day in days
        if start_datetime.date() <= day["date"] <= end_datetime.date()
    ]
    return total_contributions, filtered_days


def calculate_streaks(days, start_date, end_date):
    days = sorted(
        (day for day in days if start_date <= day["date"] <= end_date),
        key=lambda day: day["date"],
    )
    expected_dates = (end_date - start_date).days + 1
    if len(days) != expected_dates:
        raise RuntimeError("GitHub GraphQL contribution calendar is missing dates.")
    if any(
        day["date"] != start_date + timedelta(days=index)
        for index, day in enumerate(days)
    ):
        raise RuntimeError(
            "GitHub GraphQL contribution calendar contains duplicate or missing dates."
        )

    longest_streak = running_streak = 0
    for day in days:
        if day["count"] > 0:
            running_streak += 1
            longest_streak = max(longest_streak, running_streak)
        else:
            running_streak = 0

    last_contribution_date = next(
        (day["date"] for day in reversed(days) if day["count"] > 0),
        None,
    )
    current_streak = 0
    if last_contribution_date in (end_date, end_date - timedelta(days=1)):
        current_streak = 1
        streak_date = last_contribution_date
        for day in reversed(days):
            if day["date"] >= streak_date:
                continue
            if day["date"] == streak_date - timedelta(days=1) and day["count"] > 0:
                current_streak += 1
                streak_date = day["date"]
            elif day["date"] < streak_date:
                break

    return current_streak, longest_streak


def collect_stats(token: str):
    user, _ = api_get(f"{API_ROOT}/users/{USERNAME}", token)
    if (
        not isinstance(user, dict)
        or not isinstance(user.get("followers"), int)
        or isinstance(user["followers"], bool)
        or not isinstance(user.get("public_repos"), int)
        or isinstance(user["public_repos"], bool)
    ):
        raise RuntimeError("GitHub user API returned invalid follower or public repository data.")
    try:
        account_created = datetime.fromisoformat(
            user["created_at"].replace("Z", "+00:00")
        ).astimezone(timezone.utc).date()
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError(
            "GitHub user API returned an invalid account creation date."
        ) from error

    repositories = {}
    for page in repository_pages(token):
        for repo in page:
            if not isinstance(repo, dict) or not isinstance(repo.get("private"), bool):
                raise RuntimeError("GitHub repository API returned an invalid repository.")
            if repo["private"]:
                continue
            owner = repo.get("owner")
            if not isinstance(owner, dict) or not isinstance(owner.get("login"), str):
                raise RuntimeError("GitHub repository API returned invalid owner data.")
            if owner["login"].lower() != USERNAME.lower():
                continue
            repo_id = repo.get("id")
            if not isinstance(repo_id, int) or isinstance(repo_id, bool):
                raise RuntimeError("GitHub repository API returned a repository without a valid id.")
            if repo_id in repositories:
                raise RuntimeError(f"GitHub repository API returned duplicate repository id {repo_id}.")
            stars, forks = repo.get("stargazers_count"), repo.get("forks_count")
            if (
                not isinstance(stars, int)
                or isinstance(stars, bool)
                or not isinstance(forks, int)
                or isinstance(forks, bool)
            ):
                raise RuntimeError("GitHub repository API returned invalid star or fork data.")
            repositories[repo_id] = (stars, forks)

    now = datetime.now(timezone.utc)
    end_date = now.date()
    contributions, _ = contribution_calendar(
        token, now - timedelta(days=365), now
    )

    all_days = []
    chunk_start = account_created
    while chunk_start <= end_date:
        chunk_end = min(chunk_start + timedelta(days=364), end_date)
        _, chunk_days = contribution_calendar(token, chunk_start, chunk_end)
        all_days.extend(chunk_days)
        chunk_start = chunk_end + timedelta(days=1)

    start_date = account_created
    current_streak, longest_streak = calculate_streaks(all_days, start_date, end_date)

    return {
        "followers": user["followers"],
        "repositories": user["public_repos"],
        "stars": sum(stars for stars, _ in repositories.values()),
        "contributions": contributions,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
    }


def render_svg(stats):
    labels = (
        ("Total stars", stats["stars"]),
        ("Public repos", stats["repositories"]),
        ("Followers", stats["followers"]),
        ("Contributions (1y)", stats["contributions"]),
        ("Current streak", f'{stats["current_streak"]:,} days'),
        ("Longest streak", f'{stats["longest_streak"]:,} days'),
    )
    tiles = []
    for index, (label, value) in enumerate(labels):
        column, row = index % 3, index // 3
        x, y = 22 + column * 226, 64 + row * 74
        formatted_value = value if isinstance(value, str) else f"{value:,}"
        tiles.append(
            f'<g transform="translate({x},{y})">'
            '<rect width="210" height="62" rx="9" fill="#111a2e" stroke="#283552"/>'
            f'<text x="14" y="23" fill="#9ba9c7" font-size="11" '
            f'font-family="Segoe UI,Arial,sans-serif">{html.escape(label)}</text>'
            f'<text x="14" y="49" fill="#c4b5fd" font-size="21" font-weight="700" '
            f'font-family="Segoe UI,Arial,sans-serif">{formatted_value}</text>'
            "</g>"
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="222" viewBox="0 0 720 222" role="img" aria-labelledby="title description">
  <title id="title">GitHub profile statistics for {html.escape(USERNAME)}</title>
  <desc id="description">GitHub stats for {html.escape(USERNAME)} at a glance: {stats["stars"]} total stars, {stats["repositories"]} public repositories, {stats["followers"]} followers, {stats["contributions"]} contributions in the last year, {stats["current_streak"]} day current streak, and {stats["longest_streak"]} day longest streak.</desc>
  <rect x="1" y="1" width="718" height="220" rx="14" fill="#0b1220" stroke="#283552"/>
  <text x="22" y="34" fill="#e2e8f0" font-size="17" font-weight="700" font-family="Segoe UI,Arial,sans-serif">{html.escape(USERNAME)} <tspan fill="#9ba9c7" font-weight="400">at a glance</tspan></text>
  {''.join(tiles)}
</svg>
'''


def write_svg(content: str):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=OUTPUT.parent, delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        temp_path.replace(OUTPUT)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required to fetch profile statistics.")
    write_svg(render_svg(collect_stats(token)))
    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"Profile stats generation failed: {error}", file=sys.stderr)
        sys.exit(1)
