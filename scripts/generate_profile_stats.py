#!/usr/bin/env python3
"""Generate a dark-themed SVG card from GitHub's authenticated REST API."""

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


def collect_stats(token: str):
    user, _ = api_get(f"{API_ROOT}/users/{USERNAME}", token)
    if (
        not isinstance(user, dict)
        or not isinstance(user.get("followers"), int)
        or isinstance(user["followers"], bool)
    ):
        raise RuntimeError("GitHub user API returned invalid follower data.")

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

    return {
        "followers": user["followers"],
        "repositories": len(repositories),
        "stars": sum(stars for stars, _ in repositories.values()),
        "forks": sum(forks for _, forks in repositories.values()),
    }


def render_svg(stats):
    labels = (
        ("FOLLOWERS", stats["followers"]),
        ("PUBLIC REPOSITORIES", stats["repositories"]),
        ("STARS", stats["stars"]),
        ("FORKS", stats["forks"]),
    )
    tiles = []
    for index, (label, value) in enumerate(labels):
        x = 26 + index * 190
        tiles.append(
            f'<g transform="translate({x},74)">'
            '<rect width="174" height="86" rx="12" fill="#111a2e" stroke="#283552"/>'
            f'<text x="16" y="30" fill="#9ba9c7" font-size="11" '
            f'font-family="Segoe UI,Arial,sans-serif" letter-spacing="1">{label}</text>'
            f'<text x="16" y="66" fill="#c4b5fd" font-size="27" font-weight="700" '
            f'font-family="Segoe UI,Arial,sans-serif">{value:,}</text>'
            "</g>"
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="190" viewBox="0 0 800 190" role="img" aria-labelledby="title description">
  <title id="title">GitHub profile statistics for {html.escape(USERNAME)}</title>
  <desc id="description">Live GitHub API totals: {stats["followers"]} followers, {stats["repositories"]} public repositories, {stats["stars"]} stars, and {stats["forks"]} forks.</desc>
  <rect width="800" height="190" rx="16" fill="#0b1220"/>
  <text x="26" y="42" fill="#e2e8f0" font-size="18" font-weight="700" font-family="Segoe UI,Arial,sans-serif">GitHub profile stats</text>
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
