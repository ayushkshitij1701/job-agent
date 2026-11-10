from dataclasses import dataclass, field


@dataclass
class ApplyResult:
    """What happened on one application form."""
    dry_run: bool = False
    submitted: bool = False
    filled: list[str] = field(default_factory=list)      # questions answered
    skipped: list[str] = field(default_factory=list)     # optional questions left empty on purpose
    unanswered: list[str] = field(default_factory=list)  # required questions with no configured answer -> not submitted
    error: str | None = None

    @property
    def status(self) -> str:
        if self.submitted:
            return "applied"
        if self.unanswered:
            return "needs_answer"
        if self.error:
            return "apply_failed"
        return "notified"
