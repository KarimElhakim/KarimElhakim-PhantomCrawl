from __future__ import annotations

import glob
import os
import sys
import zipfile

from patchright.sync_api import sync_playwright

PAGE = "https://cd.captchaaiplus.com/turnstile.html"
RESP = '[name="cf-turnstile-response"]'
SUBMIT = 'form#turnstile-form input[type="submit"]'
RESULT = "#result"
VID = "task2/videos"
CTX = dict(
    record_video_dir=f"{VID}/",
    record_video_size={"width": 1280, "height": 720},
    viewport={"width": 1280, "height": 720},
)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    token = None
    sys.stdout.buffer.write(b"Phase 1: capture token\n")
    sys.stdout.buffer.flush()
    p1 = None
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False)
        ctx = b.new_context(**CTX)
        page = ctx.new_page()
        try:
            page.goto(PAGE, wait_until="networkidle", timeout=90_000)
            page.wait_for_function(
                """() => {
                    const el = document.querySelector('[name="cf-turnstile-response"]');
                    return el && typeof el.value === 'string' && el.value.length > 20;
                }""",
                timeout=120_000,
            )
            token = page.locator(RESP).input_value()
            sys.stdout.buffer.write(
                f"Captured token length: {len(token)}\n".encode("utf-8", errors="replace")
            )
            sys.stdout.buffer.flush()
            p1 = page.video.path()
        finally:
            ctx.close()
            b.close()
    if p1:
        os.rename(p1, f"{VID}/phase1_token_capture.webm")

    sitekey = None

    def route_fn(route):
        nonlocal sitekey
        url = route.request.url
        if not (
            "challenges.cloudflare.com" in url
            or (
                "turnstile" in url.lower() and "captchaaiplus.com" not in url
            )
        ):
            route.continue_()
            return
        if sitekey is None and "?" in url:
            for part in url.split("?", 1)[1].split("&"):
                if part.startswith("sitekey="):
                    sitekey = part.split("=", 1)[1]
                    break
                if part.startswith("k="):
                    sitekey = part.split("=", 1)[1]
                    break
        route.abort()

    sys.stdout.buffer.write(b"Phase 2: block Turnstile and inject\n")
    sys.stdout.buffer.flush()
    p2 = None
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False)
        ctx = b.new_context(**CTX)
        page = ctx.new_page()
        page.route("**/*", route_fn)
        try:
            page.goto(PAGE, wait_until="networkidle", timeout=90_000)
            w = page.locator(".cf-turnstile").first
            if sitekey is None and w.count():
                sitekey = w.get_attribute("data-sitekey")
            sys.stdout.buffer.write(
                f"Sitekey: {sitekey or '(none)'}\n".encode("utf-8", errors="replace")
            )
            sys.stdout.buffer.flush()
            iframe_n = page.locator(
                'iframe[src*="challenges.cloudflare.com"], iframe[src*="turnstile"]'
            ).count()
            val = page.evaluate(
                """() => {
                    const el = document.querySelector('[name="cf-turnstile-response"]');
                    return el ? el.value : '';
                }"""
            )
            sys.stdout.buffer.write(
                f"Widget check: iframes={iframe_n} response_len={len(val)}\n".encode(
                    "utf-8", errors="replace"
                )
            )
            sys.stdout.buffer.flush()
            assert iframe_n == 0 or len(val) < 21
            page.evaluate(
                """(t) => {
                    let el = document.querySelector('[name="cf-turnstile-response"]');
                    if (!el) {
                        el = document.createElement('input');
                        el.type = 'hidden';
                        el.name = 'cf-turnstile-response';
                        document.getElementById('turnstile-form').appendChild(el);
                    }
                    el.value = t;
                }""",
                token,
            )
            page.locator(SUBMIT).click()
            page.wait_for_function(
                """() => {
                    const el = document.getElementById('result');
                    return el && el.innerText && el.innerText.trim().length > 0;
                }""",
                timeout=30_000,
            )
            text = page.locator(RESULT).inner_text()
            sys.stdout.buffer.write(f"Result: {text}\n".encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()
            assert "success" in text.lower() or "verified" in text.lower()
            p2 = page.video.path()
        finally:
            ctx.close()
            b.close()
    if p2:
        os.rename(p2, f"{VID}/phase2_intercept_inject.webm")

    with zipfile.ZipFile(f"{VID}/runs.zip", "w") as zf:
        for f in sorted(glob.glob(f"{VID}/*.webm")):
            zf.write(f, os.path.basename(f))
    sys.stdout.buffer.write(b"Done.\n")
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
