from job_agent.filters import level_matches, location_matches, location_rank, title_level, title_matches
from job_agent.models import Job

INCLUDE = ["software engineer", "sde", "member of technical staff", "full stack"]
EXCLUDE = ["manager", "principal", "intern", "staff software"]
CITIES = ["Hyderabad", "Bangalore", "Noida", "Gurugram", "Pune"]
ROLES = {"max_level": 1, "level_2_ok_at": ["Microsoft", "ServiceNow", "Salesforce"]}


def job(*locations, remote=False):
    return Job(key="X:1", company="X", title="t", locations=locations, url="u", posted="", source="s", remote=remote)


def test_title_include_and_exclude():
    assert title_matches("Senior Software Engineer", INCLUDE, EXCLUDE)
    assert title_matches("Software Engineering AMTS", INCLUDE, EXCLUDE)   # "software engineer" is a prefix
    assert title_matches("Member of Technical Staff", INCLUDE, EXCLUDE)
    assert not title_matches("Enterprise Account Executive", INCLUDE, EXCLUDE)
    assert not title_matches("Software Engineering Manager", INCLUDE, EXCLUDE)
    assert not title_matches("Staff Software Engineer", INCLUDE, EXCLUDE)
    assert not title_matches("SDE Intern", INCLUDE, EXCLUDE)


def test_title_level_reads_roman_arabic_and_seniority_markers():
    assert title_level("Software Development Engineer") == 1
    assert title_level("SDE I") == 1
    assert title_level("Software Engineer - New Grad 2026") == 1       # "2026" is not a level
    assert title_level("SDE II") == 2
    assert title_level("Software Engineer 2") == 2
    assert title_level("SDE-II, Backend") == 2
    assert title_level("Senior Software Engineer") == 3
    assert title_level("Sr. SDE") == 3
    assert title_level("Software Engineer III") == 3
    assert title_level("Lead Software Engineer") == 3
    assert title_level("Software Developer 5") == 5                     # Oracle numbers its levels 1-5


def test_level_matches_allows_sde2_only_at_listed_companies():
    assert level_matches("SDE I", "Amazon", ROLES)
    assert not level_matches("SDE II", "Amazon", ROLES)
    assert level_matches("Software Engineer II", "Microsoft", ROLES)
    assert level_matches("Software Engineer 2", "Salesforce", ROLES)
    assert not level_matches("Senior Software Engineer", "Microsoft", ROLES)
    assert level_matches("SDE II", "Amazon", {})                      # no level config = no level filter


def test_location_rank_follows_city_priority_and_aliases():
    assert location_rank(job("Hyderabad, India"), CITIES) == 0
    assert location_rank(job("India - Bangalore"), CITIES) == 1
    assert location_rank(job("Bengaluru, KA, IN"), CITIES) == 1
    assert location_rank(job("Gurgaon, Haryana"), CITIES) == 3
    assert location_rank(job("New York - New York", "Pune, India"), CITIES) == 4
    assert location_rank(job("New York - New York"), CITIES) is None
    assert location_rank(job("48 Locations"), CITIES) is None


def test_location_matches_cities_and_india_remote_only():
    assert location_matches(job("India - Bangalore"), CITIES, include_remote=True)
    assert location_matches(job("India - Remote"), CITIES, include_remote=True)
    assert location_matches(job("India", remote=True), CITIES, include_remote=True)
    assert not location_matches(job("India - Remote"), CITIES, include_remote=False)
    assert not location_matches(job("Maryland - Remote", remote=True), CITIES, include_remote=True)
    assert not location_matches(job("Chennai, India"), CITIES, include_remote=True)
