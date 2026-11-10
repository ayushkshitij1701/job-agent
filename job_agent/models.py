from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Job:
    key: str                    # "<company>:<id the source uses>", unique across runs
    company: str
    title: str
    locations: tuple[str, ...]  # as the source words them, e.g. ("Hyderabad, India",)
    url: str                    # page a human opens to read/apply
    posted: str                 # as the source gives it: ISO date or "Posted Today"
    source: str                 # workday | smartrecruiters | microsoft | amazon
    description: str = ""       # plain-text JD; empty until enriched
    remote: bool = False

    def with_(self, **changes) -> "Job":
        return replace(self, **changes)
