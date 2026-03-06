# Phase 3: MakerWorld Search + Download - Research

**Researched:** 2026-03-06
**Domain:** MakerWorld web scraping, model search/download, Cloudflare bypass, Playwright browser automation
**Confidence:** MEDIUM

## Summary

This phase adds natural language search and download of existing 3D models from MakerWorld (makerworld.com) to the existing `/print` skill. The core technical challenge is that MakerWorld has **no public API** and is protected by **Cloudflare managed challenges** that block all direct HTTP requests (curl, requests, cloudscraper all fail). The site is a Next.js single-page application where model data lives in `__NEXT_DATA__` JSON embedded in server-rendered HTML and in internal REST API endpoints under `/api/v1/design-service/`.

The recommended approach is **Playwright (Python)** running a real Chromium browser to bypass Cloudflare, navigate search pages, extract `__NEXT_DATA__` JSON from the DOM, and download model files. This is the same approach used by the community (Apify scrapers, MMP companion extension, browser extensions). The internal API endpoints discovered from the maker-world-extension project (`/api/v1/design-service/`) can be called from within the Playwright browser context using cookies established after Cloudflare challenge resolution, providing structured JSON responses for model details and download URLs.

The skill will detect search intent ("find me a phone stand") vs generation intent ("make me a phone stand"), perform a MakerWorld search via Playwright, extract and rank results by combined rating + download count, present 3 results to the user, and download the selected model's files to `~/3d-prints/<model-name>/`. Downloaded files then integrate with the existing Phase 1/2 pipeline (BambuStudio opening, print settings).

**Primary recommendation:** Use Playwright (Python) with a persistent browser context to handle Cloudflare challenges. Extract data from `__NEXT_DATA__` and internal API endpoints. Keep the scraping logic in a standalone Python script that the skill invokes via bash, outputting JSON for the skill to parse.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Search Results Display:**
- Show 3 results per search query
- Each result displays: name, rating, image URL (thumbnail), and link to MakerWorld page
- Numbered list format (1. Model Name ...)
- Text-focused output with image URL included for optional browser preview

**Model Recommendation:**
- Rank results using a combined score of rating + download count
- Highlight the recommended model with a brief reason (e.g. "Recommended: highest rated with 2k+ downloads")
- Always ask the user to confirm selection -- no auto-selecting
- If no good results match the query, offer to generate the model from scratch using Phase 1 pipeline instead

**Download & File Handling:**
- Save downloaded files to `~/3d-prints/<makerworld-model-name>/` -- same root folder as generated models
- Folder named after the MakerWorld model name (not the user's search query)
- Download all files when a model has multiple files (plates, variants, parts)
- Prefer 3MF format when available, fall back to STL

**Pipeline Integration:**
- Same skill, detect intent: "find me X" triggers search, "make me X" triggers generation
- After download, offer to open in BambuStudio (same flow as Phase 1)
- Downloaded models support full Phase 2 features (scaling, print settings)
- For scaling downloaded models (no .scad source), suggest BambuStudio for resizing rather than OpenSCAD import

### Claude's Discretion
- Technical approach to MakerWorld search (API discovery, web scraping, or other)
- Intent detection heuristics for search vs generate
- Combined score weighting formula for recommendations
- Error handling for network/scraping failures

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SRCH-01 | User can describe desired object in natural language and get matching MakerWorld results | Playwright-based scraping of MakerWorld search pages; `__NEXT_DATA__` extraction provides structured search results with model metadata |
| SRCH-02 | User can see model preview info (name, image URL, dimensions, license, ratings) | `__NEXT_DATA__` on model pages contains full metadata; image URLs follow pattern `https://makerworld.bblmw.com/makerworld/model/{modelId}/design/{timestamp}.png` |
| SRCH-03 | System selects most durable/recommended model from results | Combined score formula using rating + normalized download count; highlight recommended with reasoning |
| SRCH-04 | User can download selected model file from MakerWorld | Internal API endpoint `/api/v1/design-service/instance/{instanceId}/f3mf?type=download` returns download URL; Playwright browser context handles auth cookies |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Playwright (Python) | 1.49+ | Browser automation for Cloudflare bypass + scraping | Only reliable way to access MakerWorld behind Cloudflare; community-validated approach |
| Python 3.10+ | System | Scraper script runtime | Playwright has first-class Python support; skill already uses bash which can invoke Python |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | Built-in | Parse `__NEXT_DATA__` and API responses | Always -- all data exchange is JSON |
| pathlib (stdlib) | Built-in | File path handling for downloads | Always -- cross-platform path management |
| re (stdlib) | Built-in | Model ID extraction from URLs | Parsing model URLs with pattern `/models/(\d+)` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Playwright | cloudscraper (Python) | cloudscraper fails on Cloudflare managed challenges (verified: MakerWorld returns "Just a moment..." challenge page). Does NOT work. |
| Playwright | Selenium + undetected-chromedriver | Heavier, slower, less maintained than Playwright. Playwright is the 2025/2026 community recommendation. |
| Playwright | curl + HTTP requests | Completely blocked by Cloudflare. Verified empirically -- returns challenge HTML, no `__NEXT_DATA__`. |
| Standalone Python script | Node.js Playwright | Python aligns with project's primary language; pip install is simpler for the user |

**Installation:**
```bash
pip install playwright
playwright install chromium
```

## Architecture Patterns

### Recommended Script Structure
```
.claude/skills/print/
  SKILL.md                    # Extended with search steps
  scripts/
    makerworld_search.py      # Standalone search + download script
  reference/
    openscad-guide.md         # (existing)
    materials.md              # (existing)
    print-settings.md         # (existing)
    printability-checklist.md  # (existing)
```

### Pattern 1: Standalone Python Script Invoked by Skill
**What:** A self-contained Python script that the SKILL.md invokes via bash, taking a search query as input and outputting structured JSON to stdout.
**When to use:** Always -- keeps scraping complexity isolated from the skill logic.

```bash
# Skill invokes the script
python3 ~/.claude/skills/print/scripts/makerworld_search.py search "phone stand" --limit 3
```

Output format (JSON to stdout):
```json
{
  "results": [
    {
      "id": "2461740",
      "name": "Phone Stand - Adjustable",
      "url": "https://makerworld.com/en/models/2461740",
      "thumbnail": "https://makerworld.bblmw.com/makerworld/model/2461740/design/...",
      "rating": 4.8,
      "download_count": 12500,
      "like_count": 3200,
      "score": 0.95,
      "recommended": true,
      "recommendation_reason": "Highest rated with 12k+ downloads",
      "license": "CC BY-SA 4.0",
      "file_formats": ["3mf", "stl"]
    }
  ],
  "query": "phone stand",
  "total_found": 3
}
```

### Pattern 2: Persistent Browser Context for Session Reuse
**What:** Use Playwright's persistent context to save cookies/state between invocations, avoiding repeated Cloudflare challenges.
**When to use:** Always -- dramatically reduces wait time for subsequent searches.

```python
from playwright.sync_api import sync_playwright
import json

BROWSER_DATA_DIR = os.path.expanduser("~/.cache/makerworld-browser")

def get_browser_context():
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch_persistent_context(
        BROWSER_DATA_DIR,
        headless=True,
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
    )
    return playwright, browser
```

### Pattern 3: __NEXT_DATA__ Extraction
**What:** Parse the embedded JSON from the Next.js `__NEXT_DATA__` script tag after page load.
**When to use:** For search result pages and model detail pages.

```python
def extract_next_data(page):
    """Extract __NEXT_DATA__ JSON from a loaded page."""
    script = page.query_selector("script#__NEXT_DATA__")
    if script:
        return json.loads(script.inner_text())
    return None
```

### Pattern 4: Internal API for File Downloads
**What:** Use the browser context's established cookies to call MakerWorld's internal API for download URLs.
**When to use:** After user selects a model, to get the actual file download link.

```python
def get_download_url(page, instance_id):
    """Get download URL via internal API (uses browser cookies)."""
    api_url = f"https://makerworld.com/api/v1/design-service/instance/{instance_id}/f3mf?type=download"
    response = page.evaluate(f"""
        async () => {{
            const resp = await fetch('{api_url}');
            return await resp.json();
        }}
    """)
    return response.get("url")
```

### Pattern 5: Intent Detection in SKILL.md
**What:** Heuristic-based detection of search vs generation intent.
**When to use:** At the start of every user interaction with the skill.

Search indicators: "find", "search", "look for", "download", "get me", "existing", "browse", "MakerWorld"
Generate indicators: "make", "create", "generate", "design", "build", "print me"
Ambiguous (ask): "I need a phone stand" -- could be either

### Pattern 6: Combined Score for Ranking
**What:** Weighted formula combining rating and download count for model recommendation.

```python
def calculate_score(rating, download_count, max_downloads):
    """
    Combined score: 60% normalized rating + 40% normalized downloads.
    Rating is on 0-5 scale, downloads normalized to 0-1 by max in result set.
    """
    norm_rating = rating / 5.0
    norm_downloads = download_count / max_downloads if max_downloads > 0 else 0
    return 0.6 * norm_rating + 0.4 * norm_downloads
```

### Anti-Patterns to Avoid
- **Direct HTTP requests to MakerWorld:** All blocked by Cloudflare. Always use Playwright browser context.
- **Headless=False in production:** Running visible browser is slow and intrusive. Use headless=True with stealth settings.
- **New browser instance per search:** Launches are slow (~3-5 seconds) and trigger new Cloudflare challenges. Use persistent context.
- **Parsing HTML with regex:** Use `__NEXT_DATA__` JSON or Playwright's DOM query selectors. Never regex parse HTML.
- **Hardcoding CSS selectors:** MakerWorld uses dynamic Material UI classes. Use `data-testid` attributes or `__NEXT_DATA__` JSON.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cloudflare bypass | Custom cookie/challenge solver | Playwright with persistent context | Cloudflare updates challenges frequently; browser automation is the only stable approach |
| HTML parsing | Regex-based extractor | `__NEXT_DATA__` JSON extraction | Next.js embeds all page data as structured JSON; parsing HTML is fragile |
| File download | Custom HTTP download handler | Playwright's `page.evaluate(fetch(...))` + Python file write | Browser context has valid cookies; manual cookie extraction is fragile |
| Browser fingerprint | Custom stealth config | Playwright defaults + persistent context | Playwright's Chromium already has reasonable fingerprinting defaults |

**Key insight:** MakerWorld is a Next.js app behind Cloudflare. The entire scraping strategy hinges on running a real browser (Playwright) to pass Cloudflare, then extracting structured data from `__NEXT_DATA__` and internal APIs. Fighting Cloudflare with HTTP-level tricks is a losing battle.

## Common Pitfalls

### Pitfall 1: Cloudflare Challenge Timeout
**What goes wrong:** First-time browser launch hits Cloudflare "Just a moment..." page and the script doesn't wait long enough.
**Why it happens:** Cloudflare challenge takes 3-8 seconds to resolve. Default page.goto timeout may be too short or script checks for content too early.
**How to avoid:** After `page.goto()`, wait for a known element on the actual page (e.g., `page.wait_for_selector("[data-testid='model-card']", timeout=30000)`). Use persistent context to avoid repeated challenges.
**Warning signs:** Script returns empty results or HTML containing "Just a moment..."

### Pitfall 2: MakerWorld Rate Limiting / IP Bans
**What goes wrong:** Too many rapid searches trigger temporary blocks or CAPTCHAs.
**Why it happens:** MakerWorld has rate limiting per IP/session.
**How to avoid:** Add 2-3 second delays between page navigations. Limit to 3 results per search (already a locked decision). Use persistent context to maintain session. This is a personal-use tool, not a scraper farm -- normal usage patterns should be fine.
**Warning signs:** Cloudflare challenge appears on every request even with persistent context.

### Pitfall 3: Download URL Expiration
**What goes wrong:** Download URLs from the internal API are time-limited signed URLs that expire.
**Why it happens:** MakerWorld uses CDN with signed URLs for file access.
**How to avoid:** Download files immediately after getting the URL. Don't cache download URLs across sessions.
**Warning signs:** HTTP 403 or expired signature errors during download.

### Pitfall 4: Model with No Downloadable Files
**What goes wrong:** Some models are "print profiles only" or have restricted downloads.
**Why it happens:** MakerWorld allows designers to restrict download access or require "boosting" (engagement).
**How to avoid:** Check file availability before presenting to user. Filter out models with no downloadable files from results. Gracefully handle "download not available" with a message.
**Warning signs:** Empty file list in model metadata or 403 on download API.

### Pitfall 5: __NEXT_DATA__ Structure Changes
**What goes wrong:** MakerWorld updates their frontend and the JSON structure in `__NEXT_DATA__` changes.
**Why it happens:** Normal web application updates -- internal data format is not a stable API contract.
**How to avoid:** Wrap all `__NEXT_DATA__` access in try/except with clear error messages. Log the actual data structure on failure for debugging. Keep extraction logic isolated in one function for easy updates.
**Warning signs:** KeyError or None values where data was expected.

### Pitfall 6: Playwright Not Installed
**What goes wrong:** User runs the search skill but Playwright/Chromium is not installed.
**Why it happens:** Playwright requires both pip install AND browser binary install (`playwright install chromium`).
**How to avoid:** Check for Playwright at skill start, similar to OpenSCAD check. Guide user through installation:
```
pip install playwright && playwright install chromium
```
**Warning signs:** ImportError or "browser not found" error.

## Code Examples

### Full Search Flow
```python
#!/usr/bin/env python3
"""MakerWorld search and download script for the /print skill."""
import json
import os
import sys
import time
from pathlib import Path

BROWSER_DATA_DIR = os.path.expanduser("~/.cache/makerworld-browser")
DOWNLOAD_DIR = os.path.expanduser("~/3d-prints")

def search_makerworld(query: str, limit: int = 3) -> dict:
    """Search MakerWorld and return structured results."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            BROWSER_DATA_DIR,
            headless=True,
        )
        page = browser.new_page()

        # Navigate to search page
        search_url = f"https://makerworld.com/en/search/models?keyword={query}"
        page.goto(search_url, wait_until="networkidle")

        # Wait for content to load (past Cloudflare)
        page.wait_for_selector("[data-testid='model-card']", timeout=30000)

        # Extract __NEXT_DATA__
        next_data = extract_next_data(page)

        # Parse search results from __NEXT_DATA__
        results = parse_search_results(next_data, limit)

        # Calculate scores and rank
        if results:
            max_dl = max(r["download_count"] for r in results)
            for r in results:
                r["score"] = calculate_score(r["rating"], r["download_count"], max_dl)
            results.sort(key=lambda r: r["score"], reverse=True)
            results[0]["recommended"] = True
            results[0]["recommendation_reason"] = build_recommendation_reason(results[0])

        page.close()
        browser.close()

    return {"results": results, "query": query, "total_found": len(results)}


def download_model(model_id: str, model_name: str) -> dict:
    """Download model files from MakerWorld."""
    from playwright.sync_api import sync_playwright

    folder_name = model_name.lower().replace(" ", "-").replace("/", "-")
    output_dir = Path(DOWNLOAD_DIR) / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            BROWSER_DATA_DIR,
            headless=True,
        )
        page = browser.new_page()

        # Navigate to model page to get instance IDs
        page.goto(f"https://makerworld.com/en/models/{model_id}", wait_until="networkidle")
        page.wait_for_selector("body", timeout=30000)

        next_data = extract_next_data(page)
        # Extract instance IDs and download files
        files = download_model_files(page, next_data, output_dir)

        page.close()
        browser.close()

    return {
        "output_dir": str(output_dir),
        "files": files,
        "model_name": model_name,
    }
```

### MakerWorld Search URL Parameters
```
Base URL: https://makerworld.com/en/search/models

Query parameters:
  keyword=<search terms>         # Space-separated keywords
  keyword=tag:+<tag>             # Tag-specific search
  orderBy=downloadCount          # Sort by downloads
  orderBy=likes                  # Sort by likes
  orderBy=collects               # Sort by collections
  (default: relevance)
```

### Playwright Installation Check (for SKILL.md)
```bash
# Check if Playwright Python is installed
python3 -c "from playwright.sync_api import sync_playwright; print('OK')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "PLAYWRIGHT_NOT_FOUND"
else
    # Check if Chromium browser is installed
    python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    try:
        b = p.chromium.launch(headless=True)
        b.close()
        print('OK')
    except Exception:
        print('CHROMIUM_NOT_FOUND')
" 2>/dev/null
fi
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| cloudscraper for Cloudflare bypass | Playwright headless browser | 2024-2025 | cloudscraper fails on managed challenges; browser automation is the only reliable method |
| Selenium for browser automation | Playwright | 2023-2024 | Playwright is faster, lighter, better API, actively maintained |
| puppeteer-extra-stealth | Playwright stealth / nodriver | Feb 2025 | puppeteer-extra-stealth no longer maintained |
| HTTP-based scraping | `__NEXT_DATA__` extraction from browser | 2024+ | Next.js apps embed all data as JSON; no HTML parsing needed |

**Deprecated/outdated:**
- cloudscraper: Cannot handle Cloudflare managed challenges (the type MakerWorld uses). Works only for basic JS challenges.
- puppeteer-extra-stealth: Announced end-of-maintenance Feb 2025.
- Direct HTTP scraping of MakerWorld: Blocked entirely by Cloudflare as of 2025/2026.

## Open Questions

1. **Exact `__NEXT_DATA__` structure for search results pages**
   - What we know: Model detail pages contain design data at `pageProps.design`. Search pages likely have results in `pageProps` but the exact path is unverified.
   - What's unclear: The precise JSON path for search result items and their field names.
   - Recommendation: During implementation, log the full `__NEXT_DATA__` from a search page to discover the exact structure. Build extraction logic based on actual data. This is LOW risk -- the data is there, we just need to map the paths.

2. **Download authentication requirements**
   - What we know: The maker-world-extension uses `/api/v1/design-service/instance/{id}/f3mf?type=download` without explicit auth headers, relying on browser cookies. Some models may require a MakerWorld account.
   - What's unclear: Whether anonymous (non-logged-in) downloads work for all models, or if some require authentication.
   - Recommendation: Test anonymous download first. If some models require auth, add a note in the skill telling the user to log in via the browser. The persistent browser context will retain login state.

3. **Headless Playwright vs Cloudflare detection**
   - What we know: Playwright headless with default settings can sometimes be detected by sophisticated Cloudflare configurations. However, MakerWorld uses standard managed challenges, not advanced bot management.
   - What's unclear: Whether headless=True works reliably or if headed mode is needed.
   - Recommendation: Start with headless=True. If Cloudflare blocks persist, switch to headed mode (visible browser) as fallback. For a personal-use tool, headed mode is acceptable -- it just pops up a browser briefly.

4. **3MF vs STL availability on MakerWorld**
   - What we know: MakerWorld supports both 3MF and STL uploads. The platform was designed for Bambu Lab printers, so 3MF (with print profiles) is common. The API endpoint uses `f3mf` suggesting 3MF is the primary format.
   - What's unclear: What percentage of models have 3MF vs STL only.
   - Recommendation: Prefer 3MF downloads. Fall back to STL if 3MF not available. This aligns with the locked decision.

## Sources

### Primary (HIGH confidence)
- [maker-world-extension content.js](https://github.com/huddleboards/maker-world-extension/blob/main/content.js) -- Revealed internal API endpoints: `/api/v1/design-service/published/{userId}/design`, `/api/v1/design-service/instance/{id}/f3mf?type=download`, `/api/v1/design-service/my/design/like`; confirmed `__NEXT_DATA__` extraction pattern and model ID regex
- [OpenBambuAPI cloud-http.md](https://github.com/Doridian/OpenBambuAPI/blob/main/cloud-http.md) -- Confirmed MakerWorld API base path `/api/v1/design-service/` and API mirror pattern
- Empirical testing (curl) -- Verified Cloudflare managed challenge blocks all direct HTTP access to makerworld.com (search pages AND model pages return "Just a moment..." challenge HTML)
- [Playwright Python installation docs](https://playwright.dev/python/docs/intro) -- Installation and basic usage verified

### Secondary (MEDIUM confidence)
- [Automatio.ai MakerWorld scraping guide](https://automatio.ai/how-to-scrape/makerworld) -- Confirmed: SPA with no initial HTML data, Cloudflare WAF with JS challenges, `data-testid='model-card'` selectors, rate limiting per IP/session
- [MakerWorld search URL](https://makerworld.com/en/search/models?orderBy=downloadCount) -- Confirmed URL parameter patterns for sorting
- [makerworld-com-scraper](https://github.com/eadehekeedyxv7/makerworld-com-scraper) -- Confirmed image URL pattern: `https://makerworld.bblmw.com/makerworld/model/{modelId}/design/{timestamp}.png`
- [Bambu Lab Community Forum](https://forum.bambulab.com/t/public-api-for-makerworld/52699) -- Confirmed no official public API exists

### Tertiary (LOW confidence)
- `__NEXT_DATA__` exact structure for search result pages -- not directly verified, inferred from model page patterns and Next.js conventions
- Download authentication requirements for anonymous users -- not tested
- Cloudflare headless detection behavior on MakerWorld specifically -- community reports suggest standard managed challenges pass with Playwright defaults, but unverified for this specific site

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Playwright is the established tool for Cloudflare-protected SPA scraping; verified by multiple community projects
- Architecture (scraping approach): MEDIUM -- API endpoints verified from extension source code; `__NEXT_DATA__` extraction confirmed; exact search page data structure needs runtime discovery
- Architecture (skill integration): HIGH -- follows same pattern as Phase 1/2 (SKILL.md with bash invocations)
- Pitfalls: MEDIUM -- based on community reports and general Cloudflare/scraping experience; MakerWorld-specific edge cases need runtime validation
- Download flow: MEDIUM -- API endpoint known from extension source; authentication requirements unclear for anonymous users

**Discretion decisions made:**
- **Technical approach:** Playwright (Python) with persistent browser context. This is the only viable approach given Cloudflare blocking. Community-validated by multiple projects.
- **Intent detection:** Keyword-based heuristics in SKILL.md (search words vs generation words). Simple, no ML needed for a CLI tool.
- **Score weighting:** 60% normalized rating + 40% normalized download count. Rating weighted higher because a highly-rated model with fewer downloads is better than a mediocre model with many downloads.
- **Error handling:** Graceful degradation -- if search fails (network, Cloudflare, timeout), inform user and offer to generate instead. Never silently fail.

**Research date:** 2026-03-06
**Valid until:** 2026-03-20 (fast-moving domain -- Cloudflare and MakerWorld can change protection/structure at any time; 14-day validity)
