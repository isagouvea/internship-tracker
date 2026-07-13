from datetime import date


def status_after_verification(current: str, *, explicitly_closed: bool = False,
                              deadline: date | None = None, seen: bool = True,
                              consecutive_failures: int = 0, reliable_closure: bool = False,
                              today: date | None = None) -> tuple[str, int]:
    today = today or date.today()
    if explicitly_closed or reliable_closure or (deadline and deadline < today):
        return "closed", 0
    if seen:
        return "open", 0
    failures = consecutive_failures + 1
    if failures >= 2:
        return "closed", failures
    return "may_have_closed", failures
