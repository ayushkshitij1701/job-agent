import re

from job_agent.sources import amazon, fetch_all, greenhouse, microsoft, oracle_hcm, smartrecruiters, workday

SALESFORCE = {
    "name": "Salesforce", "source": "workday",
    "host": "salesforce.wd12.myworkdayjobs.com", "tenant": "salesforce",
    "site": "External_Career_Site", "search_text": "software engineer India",
}
SERVICENOW = {"name": "ServiceNow", "source": "smartrecruiters", "company_id": "ServiceNow", "query": "software engineer"}
MICROSOFT = {"name": "Microsoft", "source": "microsoft", "query": "software engineer"}
AMAZON = {"name": "Amazon", "source": "amazon", "query": "software engineer"}


# ---- Workday -------------------------------------------------------------

def test_workday_parse_listing(fixture):
    jobs = workday.parse_listing(fixture("workday_list.json"), SALESFORCE)
    assert len(jobs) == 3
    job = jobs[1]
    assert job.key == "Salesforce:JR356580"
    assert job.company == "Salesforce"
    assert job.title == "Software Engineering AMTS"
    assert job.locations == ("2 Locations",)
    assert job.url.startswith("https://salesforce.wd12.myworkdayjobs.com/External_Career_Site/job/")
    assert job.posted == "Posted Today"
    assert job.source == "workday"
    assert job.description == ""


def test_workday_parse_detail_fills_description_and_all_locations(fixture):
    job = workday.parse_listing(fixture("workday_list.json"), SALESFORCE)[0]
    enriched = workday.parse_detail(job, fixture("workday_detail.json"))
    assert "<p" not in enriched.description
    assert "candidate experience" in enriched.description
    assert enriched.locations[0] == "New York - New York"
    assert "Maryland - Remote" in enriched.locations
    assert enriched.remote is False                      # remoteType is "Office - Flexible"
    assert enriched.url.startswith("https://salesforce.wd12.myworkdayjobs.com/External_Career_Site/job/")


def test_workday_fetch_paginates_using_first_page_total(fixture, stub_session):
    first = fixture("workday_list.json")          # 3 postings per page here
    first["total"] = 2 * workday.PAGE + 1         # -> exactly three calls
    later = {**fixture("workday_list.json"), "total": 0}   # Workday reports total only on page 1
    session = stub_session([first, later, later])
    jobs = workday.fetch(SALESFORCE, session)
    assert len(jobs) == 9
    assert [c["json"]["offset"] for c in session.calls] == [0, workday.PAGE, 2 * workday.PAGE]
    assert session.calls[0]["json"]["searchText"] == "software engineer India"


def test_workday_fetch_sends_applied_facets(fixture, stub_session):
    company = {**SALESFORCE, "applied_facets": {"Location_Country": ["abc"]}}
    session = stub_session([{"total": 0, "jobPostings": []}])
    workday.fetch(company, session)
    assert session.calls[0]["json"]["appliedFacets"] == {"Location_Country": ["abc"]}


# ---- SmartRecruiters ------------------------------------------------------

def test_smartrecruiters_parse_listing(fixture):
    jobs = smartrecruiters.parse_listing(fixture("smartrecruiters_list.json"), SERVICENOW)
    assert len(jobs) == 3
    job = jobs[0]
    assert job.key == "ServiceNow:744000160184480"
    assert job.title == "Sr Software Engineer"
    assert job.locations == ("Hyderabad, India",)         # fullLocation "Hyderabad, , India" cleaned
    assert job.url == "https://jobs.smartrecruiters.com/ServiceNow/744000160184480"
    assert job.posted == "2026-11-06T12:10:30.762Z"
    assert job.remote is False


def test_smartrecruiters_parse_detail(fixture):
    job = smartrecruiters.parse_listing(fixture("smartrecruiters_list.json"), SERVICENOW)[0]
    enriched = smartrecruiters.parse_detail(job, fixture("smartrecruiters_detail.json"))
    assert "To be successful in this role" in enriched.description
    assert "<p>" not in enriched.description
    assert enriched.url.startswith("https://jobs.smartrecruiters.com/ServiceNow/744000160184480-")


def test_smartrecruiters_fetch_paginates(fixture, stub_session):
    page = fixture("smartrecruiters_list.json")   # 3 postings per page here
    page["totalFound"] = smartrecruiters.PAGE + 1
    session = stub_session([page, page])
    jobs = smartrecruiters.fetch(SERVICENOW, session)
    assert len(jobs) == 6
    assert [c["params"]["offset"] for c in session.calls] == [0, smartrecruiters.PAGE]
    assert session.calls[0]["params"]["country"] == "in"


# ---- Microsoft ------------------------------------------------------------

def test_microsoft_parse_listing(fixture):
    jobs = microsoft.parse_listing(fixture("microsoft_list.json"), MICROSOFT)
    assert len(jobs) == 10
    job = jobs[0]
    assert job.key == "Microsoft:200063310"
    assert job.title == "Senior Software Engineer"
    assert job.locations == ("India, Karnataka, Bangalore",)
    assert job.url == "https://apply.careers.microsoft.com/careers/job/1970393557045291"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", job.posted)   # postedTs epoch -> ISO date
    assert job.remote is False


def test_microsoft_parse_detail_fills_description(fixture):
    job = microsoft.parse_listing(fixture("microsoft_list.json"), MICROSOFT)[0]
    enriched = microsoft.parse_detail(job, fixture("microsoft_detail.json"))
    assert "What happens when AI agents" in enriched.description
    assert "<div>" not in enriched.description
    assert enriched.locations == ("India, Karnataka, Bangalore",)


def test_microsoft_enrich_calls_v2_jobs_endpoint_with_position_id(fixture, stub_session):
    job = microsoft.parse_listing(fixture("microsoft_list.json"), MICROSOFT)[0]
    session = stub_session([fixture("microsoft_detail.json")])
    microsoft.enrich(job, MICROSOFT, session)
    assert session.calls[0]["url"] == "https://apply.careers.microsoft.com/api/apply/v2/jobs/1970393557045291"
    assert session.calls[0]["params"] == {"domain": "microsoft.com"}


def test_microsoft_fetch_paginates(fixture, stub_session):
    page = fixture("microsoft_list.json")         # 10 positions per page here
    page["data"]["count"] = microsoft.PAGE + 1
    session = stub_session([page, page])
    jobs = microsoft.fetch(MICROSOFT, session)
    assert len(jobs) == 20
    assert [c["params"]["start"] for c in session.calls] == [0, microsoft.PAGE]
    assert "User-Agent" in session.calls[0]["headers"]


# ---- Amazon ---------------------------------------------------------------

def test_amazon_parse_listing_includes_description(fixture):
    jobs = amazon.parse_listing(fixture("amazon_list.json"), AMAZON)
    assert len(jobs) == 3
    job = jobs[0]
    assert job.key == "Amazon:10585206"
    assert job.title == "Software Engineer II"
    assert job.locations == ("Hyderabad, Telangana, IND",)
    assert job.url == "https://www.amazon.jobs/en/jobs/10585206/software-engineer-ii"
    assert job.posted == "October 21, 2026"
    assert "non-internship professional software development" in job.description
    assert "<br" not in job.description


def test_amazon_fetch_paginates(fixture, stub_session):
    page = fixture("amazon_list.json")            # 3 jobs per page here
    page["hits"] = amazon.PAGE + 1
    session = stub_session([page, page])
    jobs = amazon.fetch(AMAZON, session)
    assert len(jobs) == 6
    assert [c["params"]["offset"] for c in session.calls] == [0, amazon.PAGE]


# ---- Greenhouse -------------------------------------------------------------

STRIPE = {"name": "Stripe", "source": "greenhouse", "board": "stripe"}


def test_greenhouse_parse_listing(fixture):
    jobs = greenhouse.parse_listing(fixture("greenhouse_list.json"), STRIPE)
    assert len(jobs) == 4
    job = jobs[1]
    assert job.key == "Stripe:7543868"
    assert job.title == "Software Engineer, Financial Business Insights"
    assert job.locations == ("Bengaluru, India",)
    assert job.url == "https://stripe.com/jobs/search?gh_jid=7543868"
    assert job.source == "greenhouse" and not job.remote


def test_greenhouse_parse_detail_unescapes_content_and_adds_offices(fixture):
    job = greenhouse.parse_listing(fixture("greenhouse_list.json"), STRIPE)[3]
    enriched = greenhouse.parse_detail(job, fixture("greenhouse_detail.json"))
    assert "About the role" in enriched.description and "Python, Go" in enriched.description
    assert "&lt;" not in enriched.description and "<" not in enriched.description
    assert enriched.locations == ("Mexico City, Mexico", "Mexico City, Mexico City, Mexico")


def test_greenhouse_fetch_and_enrich_urls(fixture, stub_session):
    session = stub_session([fixture("greenhouse_list.json"), fixture("greenhouse_detail.json")])
    jobs = greenhouse.fetch(STRIPE, session)
    greenhouse.enrich(jobs[3], STRIPE, session)
    assert [c["url"] for c in session.calls] == [
        "https://boards-api.greenhouse.io/v1/boards/stripe/jobs",
        "https://boards-api.greenhouse.io/v1/boards/stripe/jobs/7544547",
    ]


# ---- fetch_all --------------------------------------------------------------

def test_fetch_all_skips_backends_without_a_fetcher(caplog):
    jobs = fetch_all([{"name": "Siemens", "source": "avature"}], session=None, sources={})
    assert jobs == []
    assert "no fetcher for Siemens (avature)" in caplog.text


# ---- Oracle HCM -------------------------------------------------------------

JPMC = {"name": "JPMorgan Chase", "source": "oracle_hcm", "host": "jpmc.fa.oraclecloud.com", "site": "CX_1001",
        "location_facet": "300000000289360", "keyword": "software engineer"}


def test_oracle_hcm_parse_listing(fixture):
    jobs = oracle_hcm.parse_listing(fixture("oracle_hcm_list.json"), JPMC)
    assert len(jobs) == 3
    job = jobs[0]
    assert job.key == "JPMorgan Chase:210804197"
    assert job.title == "Lead Software Engineer- AI Agent Developer"
    assert job.locations == ("Bengaluru, Karnataka, India",)
    assert job.url == "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210804197"
    assert job.posted == "2026-11-03" and job.source == "oracle_hcm"


def test_oracle_hcm_parse_detail_joins_sections_and_secondary_locations(fixture):
    job = oracle_hcm.parse_listing(fixture("oracle_hcm_list.json"), JPMC)[0]
    enriched = oracle_hcm.parse_detail(job, fixture("oracle_hcm_detail.json"))
    assert "Python, LangChain" in enriched.description and "Required: Java" in enriched.description
    assert "<" not in enriched.description
    assert enriched.locations == ("Bengaluru, Karnataka, India", "Hyderabad, Telangana, India")


def test_oracle_hcm_finder_keeps_separators_unencoded(fixture, stub_session):
    page = fixture("oracle_hcm_list.json")
    page["items"][0]["TotalJobsCount"] = 3                    # one page only
    session = stub_session([page, fixture("oracle_hcm_detail.json")])
    jobs = oracle_hcm.fetch(JPMC, session)
    oracle_hcm.enrich(jobs[0], JPMC, session)
    list_url, detail_url = (c["url"] for c in session.calls)
    assert list_url == ("https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
                        "?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber=CX_1001,"
                        "keyword=%22software%20engineer%22,limit=25,offset=0,selectedLocationsFacet=300000000289360")
    assert detail_url == ("https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"
                          "?onlyData=true&expand=all&finder=ById;Id=%22210804197%22,siteNumber=CX_1001")


def test_oracle_hcm_fetch_paginates_to_total(fixture, stub_session):
    page = fixture("oracle_hcm_list.json")            # 3 rows per page here
    page["items"][0]["TotalJobsCount"] = oracle_hcm.PAGE + 1
    session = stub_session([page, page, page])
    jobs = oracle_hcm.fetch(JPMC, session)
    assert len(jobs) == 6 and len(session.calls) == 2
    assert "offset=25" in session.calls[1]["url"]
