"""Progress lines for long runs: wall-clock time first, then the conversation a line is about, if any."""

import time


def log(message: str, conversation: str | None = None) -> None:
    prefix = time.strftime("%H:%M:%S")
    if conversation:
        prefix += f" [conversation {conversation}]"
    print(prefix, message, flush=True)


def duration(seconds: float) -> str:
    """A span of time as it is written in logs and summaries: 42s, 3m05s, 1h02m."""
    minutes, rest = divmod(int(seconds), 60)
    if minutes == 0:
        return f"{rest}s"
    hours, minutes = divmod(minutes, 60)
    return f"{minutes}m{rest:02d}s" if hours == 0 else f"{hours}h{minutes:02d}m"
