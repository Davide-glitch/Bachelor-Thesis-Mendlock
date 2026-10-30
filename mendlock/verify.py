"""Speculative execution, post-condition oracle check, and full state rollback."""
from __future__ import annotations

import json
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

from ._compat import PlaywrightError


@dataclass
class Snapshot:
    url: str
    cookies: list
    local_storage: str
    session_storage: str


def take_snapshot(page) -> Snapshot:
    ls, ss = "{}", "{}"
    try:
        ls = page.evaluate("() => JSON.stringify(Object.entries(window.localStorage))")
        ss = page.evaluate("() => JSON.stringify(Object.entries(window.sessionStorage))")
    except PlaywrightError:
        pass
    return Snapshot(page.url, page.context.cookies(), ls, ss)


def restore(page, snap: Snapshot) -> None:
    ctx = page.context
    ctx.clear_cookies()
    if snap.cookies:
        ctx.add_cookies(snap.cookies)
    page.goto(snap.url, wait_until="load")
    try:
        page.evaluate(
            """([ls, ss]) => {
                window.localStorage.clear();
                for (const [k, v] of JSON.parse(ls)) window.localStorage.setItem(k, v);
                window.sessionStorage.clear();
                for (const [k, v] of JSON.parse(ss)) window.sessionStorage.setItem(k, v);
            }""",
            [snap.local_storage, snap.session_storage],
        )
    except PlaywrightError:
        pass


def check(expect, page) -> bool:
    try:
        r = expect(page)
    except (AssertionError, PlaywrightError):
        return False
    return True if r is None else bool(r)


def wait_for(expect, page, timeout_ms: int, poll_ms: int = 50) -> bool:
    deadline = time.monotonic() + timeout_ms / 1000.0
    while True:
        if check(expect, page):
            return True
        if time.monotonic() >= deadline:
            return False
        page.wait_for_timeout(poll_ms)


@contextmanager
def mutation_guard(context, enabled: bool, blocked: list):
    if not enabled:
        yield
        return

    def handler(route, request):
        if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            blocked.append(f"{request.method} {request.url}")
            route.abort()
        else:
            route.continue_()

    pattern = re.compile(r"^https?://")
    context.route(pattern, handler)
    try:
        yield
    finally:
        context.unroute(pattern, handler)


@dataclass
class AttemptResult:
    clicked: bool
    verified: bool
    error: str = ""
    blocked_requests: list = field(default_factory=list)


def plain_click(page, selector: str, timeout_ms: int):
    try:
        page.locator(selector).click(timeout=timeout_ms)
        return True, ""
    except PlaywrightError as e:
        return False, str(e).splitlines()[0][:200]


def attempt_click(page, selector: str, expect, *, click_timeout_ms: int = 2000,
                  verify_timeout_ms: int = 1500, guard_mutations: bool = False) -> AttemptResult:
    snap = take_snapshot(page)
    blocked: list = []
    with mutation_guard(page.context, guard_mutations, blocked):
        clicked, err = plain_click(page, selector, click_timeout_ms)
        if not clicked:
            return AttemptResult(False, False, err, blocked)
        ok = wait_for(expect, page, verify_timeout_ms)
    if not ok:
        restore(page, snap)
    return AttemptResult(True, ok, "", blocked)