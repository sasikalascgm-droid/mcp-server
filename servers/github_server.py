"""GitHub MCP Server (Python implementation).

Interacts with the GitHub REST API using the official Model Context Protocol.
Supports authenticated requests via GITHUB_PERSONAL_ACCESS_TOKEN while protecting secrets.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP

mcp = FastMCP("GitHub MCP Server")


def _get_auth_headers() -> Dict[str, str]:
    """Builds headers for GitHub API requests without leaking credentials."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "MCP-GitHub-Server-Sasikala/1.0",
    }
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN") or os.environ.get(
        "GITHUB_TOKEN"
    )
    if token:
        # Strip whitespace/quotes
        clean_token = token.strip().strip("'\"")
        headers["Authorization"] = f"token {clean_token}"
    return headers


def _make_github_request(url: str) -> Dict[str, Any]:
    """Performs a safe GET request to the GitHub REST API."""
    headers = _get_auth_headers()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(body)
            msg = err_json.get("message", body)
        except Exception:
            msg = body
        raise RuntimeError(f"GitHub API returned HTTP {status}: {msg}")
    except Exception as e:
        raise RuntimeError(f"Network error contacting GitHub API: {str(e)}")


@mcp.tool(
    name="get_repository",
    description="Get public or accessible repository metadata (stars, forks, open issues, description) from GitHub.",
)
def get_repository(owner: str, repo: str) -> str:
    """Fetches details for a specific GitHub repository."""
    owner = (owner or "").strip()
    repo = (repo or "").strip()
    if not owner or not repo:
        return "Error: Both 'owner' and 'repo' are required."

    url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        data = _make_github_request(url)
        return (
            f"Repository: {data.get('full_name')}\n"
            f"Description: {data.get('description') or 'No description provided.'}\n"
            f"Stars: {data.get('stargazers_count', 0)} | Forks: {data.get('forks_count', 0)}\n"
            f"Open Issues: {data.get('open_issues_count', 0)}\n"
            f"Default Branch: {data.get('default_branch', 'main')}\n"
            f"URL: {data.get('html_url')}"
        )
    except Exception as e:
        return f"Failed to retrieve repository: {str(e)}"


@mcp.tool(
    name="search_repositories",
    description="Search GitHub repositories matching a query term.",
)
def search_repositories(query: str, max_results: int = 5) -> str:
    """Searches repositories on GitHub."""
    clean_query = (query or "").strip()
    if not clean_query:
        return "Error: Search query cannot be empty."

    encoded_query = urllib.parse.quote(clean_query)
    url = f"https://api.github.com/search/repositories?q={encoded_query}&per_page={max(1, min(max_results, 10))}"
    try:
        data = _make_github_request(url)
        items = data.get("items", [])
        if not items:
            return f"No repositories found matching '{clean_query}'."

        lines = [f"Found {data.get('total_count', len(items))} repositories (showing top {len(items)}):"]
        for item in items:
            lines.append(
                f"- {item.get('full_name')} (Stars: {item.get('stargazers_count', 0)}) — {item.get('description') or 'No description'}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Failed to search repositories: {str(e)}"


@mcp.tool(
    name="list_issues",
    description="List open issues for a given repository (owner/repo).",
)
def list_issues(owner: str, repo: str, state: str = "open") -> str:
    """Lists recent issues for a repository."""
    owner = (owner or "").strip()
    repo = (repo or "").strip()
    if not owner or not repo:
        return "Error: Both 'owner' and 'repo' are required."

    url = f"https://api.github.com/repos/{owner}/{repo}/issues?state={state}&per_page=5"
    try:
        issues = _make_github_request(url)
        if not issues:
            return f"No {state} issues found in {owner}/{repo}."

        lines = [f"Recent {state} issues for {owner}/{repo}:"]
        for issue in issues:
            # Exclude pull requests (GitHub API returns PRs in issues endpoint)
            is_pr = "pull_request" in issue
            kind = "PR" if is_pr else "Issue"
            lines.append(f"- #{issue.get('number')} [{kind}] {issue.get('title')} (by @{issue.get('user', {}).get('login')})")
        return "\n".join(lines)
    except Exception as e:
        return f"Failed to list issues: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
