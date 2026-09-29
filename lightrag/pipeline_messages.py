"""Timestamp pipeline history without changing its existing message contract."""

import time
from datetime import datetime, timezone


def append_pipeline_message(status: dict, message: str) -> None:
    history = status["history_messages"]
    timings = status.get("history_message_timings")
    if timings is not None:
        # Other callers may reset or trim the history directly. Keep the
        # parallel list aligned and leave unknown older timestamps empty.
        if len(timings) != len(history):
            timings[:] = [None] * len(history)
            status["last_pipeline_message_time"] = None
        now = time.time()
        previous = status.get("last_pipeline_message_time")
        timings.append(
            {
                "time": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                "elapsed_seconds": round(now - previous, 3) if previous else None,
            }
        )
        status["last_pipeline_message_time"] = now
    history.append(message)
