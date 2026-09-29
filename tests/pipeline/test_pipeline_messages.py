from lightrag.pipeline_messages import append_pipeline_message


def test_pipeline_message_timings_follow_history_resets(monkeypatch):
    times = iter([100.0, 102.5, 105.0])
    monkeypatch.setattr("lightrag.pipeline_messages.time.time", lambda: next(times))
    state = {"history_messages": [], "history_message_timings": []}

    append_pipeline_message(state, "started")
    append_pipeline_message(state, "parsed")
    assert state["history_messages"] == ["started", "parsed"]
    assert state["history_message_timings"][0]["elapsed_seconds"] is None
    assert state["history_message_timings"][1]["elapsed_seconds"] == 2.5

    state["history_messages"][:] = ["new job"]
    append_pipeline_message(state, "next")
    assert state["history_message_timings"] == [None, {
        "time": "1970-01-01T00:01:45+00:00", "elapsed_seconds": None,
    }]
