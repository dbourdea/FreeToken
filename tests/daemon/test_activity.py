from __future__ import annotations

import base64
import time

from freetoken.daemon.activity import ActivityStore


def _record(store: ActivityStore, *, model="a", body=b"ok", cancelled=False):
    return store.record(
        model=model,
        route="/v1/chat/completions",
        method="POST",
        status=200,
        started=time.monotonic() - 0.01,
        ttft_s=0.002,
        response_bytes=len(body),
        cancelled=cancelled,
        request_headers={
            "Authorization": "Bearer secret", "X-Auth-Token": "also-secret",
            "X-Trace": "visible",
        },
        request_body=b"\x00prompt",
        response_headers={"Set-Cookie": "private", "Content-Type": "application/octet-stream"},
        response_body=body,
    )


def test_activity_rows_are_bounded_filterable_and_aggregated():
    store = ActivityStore(max_entries=2, capture_budget_bytes=0)
    _record(store, model="a", body=b"1")
    _record(store, model="b", body=b"22")
    latest = _record(store, model="a", body=b"333", cancelled=True)

    page = store.list(limit=1)
    assert [row["id"] for row in page["data"]] == [latest["id"]]
    assert page["nextBeforeId"] == latest["id"]
    assert [row["model"] for row in store.list(limit=10)["data"]] == ["a", "b"]
    assert store.stats(model="a") == {
        "count": 1, "cancelled": 1, "errors": 0,
        "responseBytes": 3, "averageDurationS": latest["durationS"],
    }


def test_capture_is_opt_in_redacted_binary_safe_and_evicted_with_row():
    store = ActivityStore(max_entries=1, capture_budget_bytes=1024)
    first = _record(store, body=b"\xffresult")
    capture = store.capture(first["id"])

    assert first["hasCapture"] is True
    assert capture["requestHeaders"] == {
        "Authorization": "[REDACTED]", "X-Auth-Token": "[REDACTED]",
        "X-Trace": "visible",
    }
    assert capture["responseHeaders"]["Set-Cookie"] == "[REDACTED]"
    assert base64.b64decode(capture["requestBodyBase64"]) == b"\x00prompt"
    assert base64.b64decode(capture["responseBodyBase64"]) == b"\xffresult"

    second = _record(store, body=b"next")
    assert store.capture(first["id"]) is None
    assert store.capture(second["id"]) is not None


def test_capture_skips_cancelled_and_over_budget_items_and_reconfigures():
    store = ActivityStore(max_entries=5, capture_budget_bytes=8)
    assert _record(store, body=b"too-large")["hasCapture"] is False
    assert _record(store, body=b"x", cancelled=True)["hasCapture"] is False
    store.reconfigure(1, 0)
    page = store.list(limit=10)
    assert page["count"] == 1
    assert page["data"][0]["hasCapture"] is False
    assert store.capture_item_limit == 0

    retained = ActivityStore(max_entries=2, capture_budget_bytes=1024)
    row = _record(retained, body=b"captured")
    assert row["hasCapture"] is True
    retained.reconfigure(2, 0)
    assert retained.list(limit=2)["data"][0]["hasCapture"] is False
    assert retained.capture(row["id"]) is None
