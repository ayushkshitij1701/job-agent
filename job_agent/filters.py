import re

from job_agent.models import Job

# Spellings the career sites use for the cities in config.yaml
ALIASES = {"bangalore": ("bengaluru",), "gurugram": ("gurgaon",)}

# Title words that mark a level above SDE-1: "SDE II", "Software Engineer 2", "Senior …", "Sr. …"
LEVEL_MARKERS = {"ii": 2, "2": 2, "iii": 3, "3": 3, "iv": 4, "4": 4, "5": 5, "senior": 3, "sr": 3, "lead": 3}


def title_matches(title: str, include: list[str], exclude: list[str]) -> bool:
    t = title.lower()
    return any(i.lower() in t for i in include) and not any(e.lower() in t for e in exclude)


def title_level(title: str) -> int:
    """1 (SDE-1 / new grad) unless the title carries a level marker."""
    tokens = re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", title.lower())      # "2026" and "2.0" stay whole, "Sr." -> "sr"
    return max((LEVEL_MARKERS.get(t, 1) for t in tokens), default=1)


def level_matches(title: str, company: str, roles: dict) -> bool:
    """SDE-1 titles everywhere; SDE-2 titles only at roles.level_2_ok_at; nothing above that."""
    if "max_level" not in roles:
        return True
    limit = 2 if company in roles.get("level_2_ok_at", ()) else roles["max_level"]
    return title_level(title) <= limit


def _in_city(location: str, city: str) -> bool:
    loc = location.lower()
    return any(term in loc for term in (city.lower(), *ALIASES.get(city.lower(), ())))


def location_rank(job: Job, cities: list[str]) -> int | None:
    """Index of the highest-priority city the job is in, or None if it is in none of them."""
    for rank, city in enumerate(cities):
        if any(_in_city(loc, city) for loc in job.locations):
            return rank
    return None


def is_india_remote(job: Job) -> bool:
    india = [loc for loc in job.locations if "india" in loc.lower()]
    return any("remote" in loc.lower() for loc in india) or (job.remote and bool(india))


def location_matches(job: Job, cities: list[str], include_remote: bool) -> bool:
    return location_rank(job, cities) is not None or (include_remote and is_india_remote(job))
