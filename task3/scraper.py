from __future__ import annotations

import base64
import json
import os
import sys

import requests
from patchright.sync_api import sync_playwright

URL = "https://egypt.blsspainglobal.com/Global/CaptchaPublic/GenerateCaptcha?data=4CDiA9odF2%2b%2bsWCkAU8htqZkgDyUa5SR6waINtJfg1ThGb6rPIIpxNjefP9UkAaSp%2fGsNNuJJi5Zt1nbVACkDRusgqfb418%2bScFkcoa1F0I%3d"
OUT_ALL = "task3/allimages.json"
OUT_VIS = "task3/visible_images_only.json"
IMG_JS = """()=>[...document.querySelectorAll('img')].map(i=>{const s=i.getAttribute('src')||i.src||'';try{return new URL(s,location.href).href}catch{return s}})"""
VIS_IMG_JS = """()=>{const V=el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'&&parseFloat(s.opacity)!==0};return [...document.querySelectorAll('img')].filter(V).map(i=>{const s=i.getAttribute('src')||i.src||'';try{return new URL(s,location.href).href}catch{return s}})}"""
TEXT_JS = """()=>{const V=el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'&&parseFloat(s.opacity)!==0};const o=[],w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null);let n;while(n=w.nextNode()){const p=n.parentElement;if(!p||!V(p))continue;const t=n.textContent.trim();t&&o.push(t)}return o}"""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs("task3", exist_ok=True)
    all_srcs: list[str] = []
    vis_srcs: list[str] = []
    text_blocks: list[str] = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False)
        ctx = b.new_context()
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(3000)
        for fr in page.frames:
            try:
                all_srcs.extend(fr.evaluate(IMG_JS))
            except Exception:
                pass
            try:
                vis_srcs.extend(fr.evaluate(VIS_IMG_JS))
            except Exception:
                pass
            try:
                text_blocks.extend(fr.evaluate(TEXT_JS))
            except Exception:
                pass
        sess = requests.Session()
        sess.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        sess.headers["Referer"] = URL
        sess.cookies.update({c["name"]: c["value"] for c in ctx.cookies()})
        ctx.close()
        b.close()
    all_b64: list[str] = []
    vis_b64: list[str] = []
    for srcs, bucket in ((all_srcs, all_b64), (vis_srcs, vis_b64)):
        for u in srcs:
            if not u:
                continue
            try:
                if u.startswith("data:"):
                    raw = (
                        base64.b64decode(u.split("base64,", 1)[1].split("#")[0].strip())
                        if "base64," in u
                        else b""
                    )
                else:
                    r = sess.get(u, timeout=60, allow_redirects=True)
                    r.raise_for_status()
                    raw = r.content
                bucket.append(base64.b64encode(raw).decode("ascii"))
            except Exception:
                bucket.append("")
    with open(OUT_ALL, "w", encoding="utf-8") as f:
        json.dump(all_b64, f)
    with open(OUT_VIS, "w", encoding="utf-8") as f:
        json.dump(vis_b64, f)
    for t in text_blocks:
        sys.stdout.buffer.write((t + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(
        f"Total images scraped: {len(all_b64)}\nVisible images count: {len(vis_b64)}\nVisible text blocks found: {len(text_blocks)}\n".encode(
            "utf-8", errors="replace"
        )
    )
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
