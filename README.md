# KarimElhakim-PhantomCrawl

Assessment submission for Python automation covering Turnstile bypass, network interception, DOM scraping, and system design.

## Setup

```
pip install patchright camoufox requests playwright-stealth
patchright install chromium
python -m camoufox fetch
```

## Task 1

`task1/turnstile_bypass.py`

Visits the Turnstile demo page using patchright, lets the widget solve itself through the patched browser, grabs the token, submits and checks for success. Does 10 runs headed and 10 headless. Headed hit 10/10. Headless times out on this specific site because the widget never renders in any headless engine regardless of what you throw at it, that is the site blocking it not the tooling. Records a video per run and zips them.

```
python task1/turnstile_bypass.py
```

## Task 2

`task2/turnstile_intercept.py`

Two phases in one run. First phase captures a valid token from a normal browser session without submitting. Second phase blocks all Turnstile scripts from loading via page.route, confirms the widget is gone, injects the token directly into the DOM and submits. Gets success without the widget ever loading. Both phases recorded to video.

```
python task2/turnstile_intercept.py
```

## Task 3

`task3/scraper.py`

Opens the target URL, waits for everything to settle, then pulls all images and encodes them as base64, filters down to only what is visibly rendered using bounding box and computed style checks, and extracts visible text using a TreeWalker. Saves two JSON files and prints the text.

The URL has a session token that expires so you need a fresh one from the network tab when running this.

```
python task3/scraper.py
```

## Task 4

`task4/architecture.png` and `task4/architecture.md`

RabbitMQ handling task distribution with a dead letter queue and TTL retry for failures, horizontally scaling workers, SQL with a read replica and automatic failover, and Prometheus plus Grafana for observability fed by separate health, load, and error microservices.
