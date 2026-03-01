"""Per-repo weekly change research using GitHub API + OpenAI summarisation."""
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from github import Github
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import RepoScore, ResearchResult

log = logging.getLogger(__name__)

_CACHE_DIR = Path(".cache/research")

_SYSTEM_PROMPT = """\
You are a senior developer briefing an audience of experienced engineers about \
what changed in an open-source repository over the last 7 days.

Focus only on changes relevant to developer productivity, AI agent workflows, \
or tooling integrations. Skip maintenance chores and dependency bumps unless \
they are significant. Assume technical literacy — no beginner explanations.

Return a JSON object with exactly these keys:
  "key_changes": list of 3–6 concise strings describing notable changes
  "implications": list of 2–4 strings on practical impact for developers
  "recommendation": one sentence summarising the headline takeaway
"""


def _cache_path(full_name: str, week: str) -> Path:
    safe = full_name.replace("/", "__")
    return _CACHE_DIR / f"{safe}__{week}.json"


def _load_cache(full_name: str, week: str) -> dict | None:
    p = _cache_path(full_name, week)
    if p.exists():
        log.info("Cache hit: %s", p.name)
        return json.loads(p.read_text())
    return None


def _save_cache(full_name: str, week: str, data: dict) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(full_name, week).write_text(json.dumps(data, indent=2))


def _week_key() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-W%W")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
def _fetch_activity(repo_name: str, since: datetime) -> dict:
    gh = Github(login_or_token=os.environ.get("GITHUB_TOKEN"), per_page=50)
    repo = gh.get_repo(repo_name)

    commits = []
    try:
        for c in repo.get_commits(since=since):
            commits.append(c.commit.message.splitlines()[0])
            if len(commits) >= 30:
                break
    except Exception:
        pass

    releases = []
    try:
        for r in repo.get_releases():
            if r.published_at and r.published_at >= since:
                releases.append({"tag": r.tag_name, "body": (r.body or "")[:400]})
    except Exception:
        pass

    issues_closed = []
    try:
        for i in repo.get_issues(state="closed", since=since):
            issues_closed.append(i.title)
            if len(issues_closed) >= 20:
                break
    except Exception:
        pass

    prs_merged = []
    try:
        for pr in repo.get_pulls(state="closed", sort="updated", direction="desc"):
            if pr.merged_at and pr.merged_at >= since:
                prs_merged.append(pr.title)
            if len(prs_merged) >= 20:
                break
    except Exception:
        pass

    return {
        "full_name": repo_name,
        "description": repo.description or "",
        "commits": commits,
        "releases": releases,
        "issues_closed": issues_closed,
        "prs_merged": prs_merged,
    }


def _summarise(activity: dict) -> dict:
    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=os.environ["GITHUB_TOKEN"],
    )
    user_content = json.dumps(activity, indent=2)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        max_tokens=800,
    )
    return json.loads(response.choices[0].message.content)


def research(repos: list[RepoScore]) -> list[ResearchResult]:
    """Research each repo and return ResearchResult list."""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    week = _week_key()
    results: list[ResearchResult] = []

    for repo in repos:
        log.info("Researching %s", repo.full_name)
        cached = _load_cache(repo.full_name, week)
        if cached:
            summary = cached
        else:
            activity = _fetch_activity(repo.full_name, since)
            summary = _summarise(activity)
            _save_cache(repo.full_name, week, summary)

        results.append(ResearchResult(
            full_name=repo.full_name,
            url=repo.url,
            status=repo.status,
            score_total=repo.score_total,
            key_changes=summary.get("key_changes", []),
            implications=summary.get("implications", []),
            recommendation=summary.get("recommendation", ""),
        ))

    return results
