"""Discovers and scores fast-rising GitHub repositories by topic."""
import logging
import os
from datetime import datetime, timedelta, timezone

from github import Github, GithubException
from tenacity import retry, stop_after_attempt, wait_exponential

from . import config
from .models import RepoScore, StatusLabel

log = logging.getLogger(__name__)


def _github_client() -> Github:
    token = os.environ.get("GITHUB_TOKEN")
    return Github(login_or_token=token, per_page=100)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_growth(repo, since: datetime) -> float:
    """Star velocity, fork growth, recent commit frequency."""
    stars = repo.stargazers_count or 0
    forks = repo.forks_count or 0
    # Clamp to 0-100 using log-scale heuristics
    star_score = min(100, (stars ** 0.4))
    fork_score = min(100, (forks ** 0.35))
    # Recent push recency bonus
    pushed = repo.pushed_at
    days_since_push = max(0, (datetime.now(timezone.utc) - pushed).days) if pushed else 30
    recency = max(0, 100 - days_since_push * 14)
    return round((star_score * 0.4 + fork_score * 0.2 + recency * 0.4), 1)


def _score_health(repo) -> float:
    """Recent commits, release cadence, open issue ratio."""
    has_issues = repo.has_issues
    open_issues = repo.open_issues_count or 0
    total = max(1, open_issues)
    issue_ratio = min(100, max(0, 100 - (open_issues / total) * 20))
    # Release cadence: penalise repos with no recent release
    latest_release_score = 50.0
    try:
        rel = repo.get_latest_release()
        days = (datetime.now(timezone.utc) - rel.published_at).days
        latest_release_score = max(0, 100 - days * 2)
    except Exception:
        pass
    has_ci = 70.0  # default; we don't fetch workflow files to save API quota
    return round((issue_ratio * 0.3 + latest_release_score * 0.4 + has_ci * 0.3), 1)


def _score_quality(repo) -> float:
    """CI presence inferred from topics/description, modular structure proxy."""
    topics = repo.topics or []
    has_ci_signal = any(t in topics for t in ["ci", "github-actions", "testing", "test"]) or 0
    has_docs = any(t in topics for t in ["documentation", "docs"]) or 0
    base = 50 + has_ci_signal * 20 + has_docs * 10
    # Penalise archived
    if repo.archived:
        base = max(0, base - 40)
    return min(100.0, float(base))


def _score_adoption(repo) -> float:
    """Stars as adoption proxy combined with watcher count."""
    stars = repo.stargazers_count or 0
    watchers = repo.watchers_count or 0
    star_score = min(100, stars ** 0.38)
    watcher_score = min(100, watchers ** 0.35)
    return round(star_score * 0.7 + watcher_score * 0.3, 1)


def _weighted_total(g: float, h: float, q: float, a: float) -> float:
    w = config.all_config()["weights"]
    return round(g * w["growth"] + h * w["health"] + q * w["quality"] + a * w["adoption"], 1)


def _classify(total: float, g: float, h: float, q: float, a: float) -> StatusLabel:
    t = config.all_config()["thresholds"]

    rh = t["rising_healthy"]
    if total >= rh["total_min"] and g >= rh["growth_min"] and h >= rh["health_min"]:
        return "Rising & Healthy"

    ms = t["mature_stable"]
    if ms["total_min"] <= total <= ms["total_max"] and h >= ms["health_min"]:
        return "Mature & Stable"

    hd = t["hype_driven"]
    if total >= hd["total_min"] and g >= hd["growth_min"] and h < hd["health_max"]:
        return "Hype-Driven"

    ns = t["niche_strong"]
    if ns["total_min"] <= total <= ns["total_max"] and q >= ns["quality_min"] and a < ns["adoption_max"]:
        return "Niche but Strong"

    return "At Risk"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
def _search_topic(gh: Github, topic: str, since: datetime) -> list:
    since_str = since.strftime("%Y-%m-%d")
    query = f"topic:{topic.lower().replace(' ', '-')} pushed:>{since_str}"
    results = gh.search_repositories(query, sort="updated", order="desc")
    return list(results[:50])


def discover(top_n: int | None = None) -> list[RepoScore]:
    """Return top_n scored RepoScore objects across all configured topics."""
    cfg = config.all_config()
    topics: list[str] = cfg["topics"]
    n = top_n or cfg["discovery"]["top_n"]
    window = cfg["discovery"]["window_days"]
    since = datetime.now(timezone.utc) - timedelta(days=window)

    gh = _github_client()
    seen: set[str] = set()
    candidates: list = []

    for topic in topics:
        log.info("Searching topic: %s", topic)
        try:
            repos = _search_topic(gh, topic, since)
            for r in repos:
                if r.full_name not in seen:
                    seen.add(r.full_name)
                    candidates.append(r)
        except GithubException as exc:
            log.warning("Topic %s search failed: %s", topic, exc)

    log.info("Scoring %d unique candidates", len(candidates))
    scored: list[RepoScore] = []
    for repo in candidates:
        try:
            g = _score_growth(repo, since)
            h = _score_health(repo)
            q = _score_quality(repo)
            a = _score_adoption(repo)
            total = _weighted_total(g, h, q, a)
            status = _classify(total, g, h, q, a)
            scored.append(RepoScore(
                full_name=repo.full_name,
                url=repo.html_url,
                description=repo.description or "",
                score_growth=g,
                score_health=h,
                score_quality=q,
                score_adoption=a,
                score_total=total,
                status=status,
                stars=repo.stargazers_count,
                forks=repo.forks_count,
                recent_commits=0,  # populated lazily in research phase
            ))
        except Exception as exc:
            log.warning("Failed to score %s: %s", repo.full_name, exc)

    scored.sort(key=lambda r: r.score_total, reverse=True)
    top = scored[:n]
    log.info("Top %d repos selected", len(top))
    for r in top:
        log.info("  [%.1f] %s (%s)", r.score_total, r.full_name, r.status)
    return top
