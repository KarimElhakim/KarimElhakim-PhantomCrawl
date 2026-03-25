from __future__ import annotations

import glob
import os
import sys
import traceback
import zipfile

from patchright.sync_api import sync_playwright

PAGE_URL = "https://cd.captchaaiplus.com/turnstile.html"
TURNSTILE_RESPONSE = '[name="cf-turnstile-response"]'
RESULT_SELECTOR = "#result"
SUBMIT_SELECTOR = 'form#turnstile-form input[type="submit"]'

RESULT_TIMEOUT_MS = 8_000


def _result_indicates_success(text: str) -> bool:
    stripped = text.strip() if text else ""
    if not stripped:
        return False
    if "\u274c" in text or stripped.lower().startswith("error:"):
        return False
    lower = stripped.lower()
    if "failed" in lower or "missing-input" in lower:
        return False
    return True


def wait_for_token(page, timeout_ms: int) -> str:
    page.wait_for_function(
        """() => {
            const el = document.querySelector('[name="cf-turnstile-response"]');
            return el && typeof el.value === 'string' && el.value.length > 20;
        }""",
        timeout=timeout_ms,
    )
    token = page.locator(TURNSTILE_RESPONSE).input_value()
    sys.stdout.buffer.write(f"  Token: {token}\n".encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()
    return token


def submit_and_read_result(page, timeout_ms: int) -> str:
    page.locator(SUBMIT_SELECTOR).click()
    page.wait_for_function(
        """() => {
            const el = document.getElementById('result');
            return el && el.innerText && el.innerText.trim().length > 0;
        }""",
        timeout=timeout_ms,
    )
    result_text = page.locator(RESULT_SELECTOR).inner_text()
    sys.stdout.buffer.write(f"  Result: {result_text}\n".encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()
    if not _result_indicates_success(result_text):
        raise RuntimeError(f"Unexpected or error result text: {result_text!r}")
    return result_text


def run_single_flow(page, turnstile_solve_timeout_ms: int) -> tuple[str, str]:
    page.goto(PAGE_URL, wait_until="networkidle", timeout=30_000)
    token = wait_for_token(page, turnstile_solve_timeout_ms)
    result_text = submit_and_read_result(page, RESULT_TIMEOUT_MS)
    return token, result_text


def run_batch(headless: bool, label: str) -> int:
    successes = 0
    print(f"\n=== {label} (headless={headless}) ===", flush=True)

    if not headless:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            for i in range(10):
                run_no = i + 1
                print(f"\nRun {run_no}/10:", flush=True)
                try:
                    context = browser.new_context(
                        record_video_dir="task1/videos/",
                        record_video_size={"width": 1280, "height": 720},
                        viewport={"width": 1280, "height": 720},
                    )
                    page = context.new_page()
                    video_path = None
                    try:
                        run_single_flow(page, 15_000)
                        video_path = page.video.path()
                    finally:
                        context.close()
                    if video_path is not None:
                        os.rename(
                            video_path,
                            f"task1/videos/headed_run_{run_no}.webm",
                        )
                    successes += 1
                    print(f"  OK (run {run_no})", flush=True)
                except Exception as e:
                    reason = f"{type(e).__name__}: {e}"
                    print(f"  FAIL: {reason}", flush=True)
                    print(traceback.format_exc(), flush=True)
            browser.close()
    else:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for i in range(10):
                run_no = i + 1
                print(f"\nRun {run_no}/10:", flush=True)
                try:
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 720},
                    )
                    page = context.new_page()
                    try:
                        run_single_flow(page, 15_000)
                    finally:
                        context.close()
                    successes += 1
                    print(f"  OK (run {run_no})", flush=True)
                except Exception as e:
                    print(f"  FAIL: {type(e).__name__}: {e}", flush=True)
            browser.close()

    return successes


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    headed_ok = run_batch(headless=False, label="Headed")
    headless_ok = run_batch(headless=True, label="Headless")

    print("\n--- Summary ---", flush=True)
    print(f"Headed success rate ({headed_ok}/10)", flush=True)
    print(f"Headless success rate ({headless_ok}/10)", flush=True)

    with zipfile.ZipFile("task1/videos/runs.zip", "w") as zf:
        for f in sorted(glob.glob("task1/videos/*.webm")):
            zf.write(f, os.path.basename(f))
    print("Videos zipped to task1/videos/runs.zip", flush=True)


if __name__ == "__main__":
    main()
