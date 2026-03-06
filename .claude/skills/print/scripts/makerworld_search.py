#!/usr/bin/env python3
"""MakerWorld search and download script for the /print skill.

Standalone CLI with two subcommands:
  search   - Search MakerWorld for 3D models by keyword
  download - Download model files from MakerWorld by model ID

All output is JSON to stdout (for skill parsing). Debug/errors go to stderr.
Uses Playwright with persistent browser context to bypass Cloudflare.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

BROWSER_DATA_DIR = os.path.expanduser("~/.cache/makerworld-browser")
MAKERWORLD_BASE = "https://makerworld.com"


def eprint(*args, **kwargs):
    """Print to stderr for debug/error messages."""
    print(*args, file=sys.stderr, **kwargs)


def output_json(data: dict):
    """Print JSON to stdout and exit."""
    print(json.dumps(data, indent=2))


def output_error(error: str, **extra):
    """Print error JSON to stdout."""
    result = {"status": "error", "error": error}
    result.update(extra)
    output_json(result)


def get_browser_context(playwright):
    """Create a persistent browser context for Cloudflare bypass."""
    os.makedirs(BROWSER_DATA_DIR, exist_ok=True)
    browser = playwright.chromium.launch_persistent_context(
        BROWSER_DATA_DIR,
        headless=True,
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 720},
    )
    return browser


def extract_next_data(page) -> dict | None:
    """Extract __NEXT_DATA__ JSON from a loaded page."""
    try:
        script = page.query_selector("script#__NEXT_DATA__")
        if script:
            text = script.inner_text()
            return json.loads(text)
    except Exception as e:
        eprint(f"[extract_next_data] Error: {e}")
    return None


def wait_for_content(page, timeout_ms: int = 30000):
    """Wait for page to load past Cloudflare challenge.

    Tries model-card selector first, falls back to __NEXT_DATA__ script tag.
    """
    try:
        page.wait_for_selector("[data-testid='model-card']", timeout=timeout_ms)
        return True
    except Exception:
        eprint("[wait_for_content] model-card selector not found, trying __NEXT_DATA__")
    try:
        page.wait_for_selector("script#__NEXT_DATA__", timeout=timeout_ms)
        return True
    except Exception:
        eprint("[wait_for_content] __NEXT_DATA__ not found either")
    return False


def parse_search_results(next_data: dict | None, limit: int) -> list[dict]:
    """Parse search results from __NEXT_DATA__ JSON.

    The exact data path needs runtime discovery -- this function tries multiple
    known patterns and logs the structure if parsing fails.
    """
    if not next_data:
        return []

    results = []

    try:
        page_props = next_data.get("props", {}).get("pageProps", {})

        # Try common Next.js patterns for search results
        search_data = None

        # Pattern 1: pageProps.searchResult or pageProps.searchResults
        for key in ["searchResult", "searchResults", "result", "results",
                     "data", "models", "items", "designs"]:
            if key in page_props:
                search_data = page_props[key]
                eprint(f"[parse_search_results] Found data at pageProps.{key}")
                break

        # Pattern 2: pageProps.dehydratedState (React Query)
        if not search_data and "dehydratedState" in page_props:
            dehydrated = page_props["dehydratedState"]
            queries = dehydrated.get("queries", [])
            if queries:
                # Take the first query's data
                query_data = queries[0].get("state", {}).get("data", {})
                if isinstance(query_data, dict):
                    # Could be paginated: { items: [...] } or { hits: [...] }
                    for key in ["items", "hits", "rows", "designs", "models",
                                "results", "data", "list"]:
                        if key in query_data:
                            search_data = query_data[key]
                            eprint(f"[parse_search_results] Found data at dehydratedState.queries[0].state.data.{key}")
                            break
                    if not search_data:
                        search_data = query_data
                elif isinstance(query_data, list):
                    search_data = query_data
                    eprint("[parse_search_results] Found data at dehydratedState.queries[0].state.data (list)")

        # Pattern 3: Nested deeper
        if not search_data:
            # Log structure for debugging
            eprint(f"[parse_search_results] pageProps keys: {list(page_props.keys())}")
            if "dehydratedState" in page_props:
                dehydrated = page_props["dehydratedState"]
                queries = dehydrated.get("queries", [])
                for i, q in enumerate(queries[:3]):
                    state_data = q.get("state", {}).get("data", {})
                    if isinstance(state_data, dict):
                        eprint(f"[parse_search_results] queries[{i}].state.data keys: {list(state_data.keys())}")
                    else:
                        eprint(f"[parse_search_results] queries[{i}].state.data type: {type(state_data).__name__}")
            return []

        # Normalize: ensure we have a list of items
        items = []
        if isinstance(search_data, list):
            items = search_data
        elif isinstance(search_data, dict):
            # Might be a paginated response with a nested list
            for key in ["items", "hits", "rows", "designs", "models",
                        "results", "data", "list"]:
                if key in search_data and isinstance(search_data[key], list):
                    items = search_data[key]
                    break
            if not items:
                items = [search_data]  # Single result

        # Extract fields from each item
        for item in items[:limit]:
            model = extract_model_fields(item)
            if model:
                results.append(model)

    except Exception as e:
        eprint(f"[parse_search_results] Parse error: {e}")
        if next_data:
            # Dump structure for debugging
            eprint(f"[parse_search_results] Top-level keys: {list(next_data.keys())}")
            props = next_data.get("props", {})
            eprint(f"[parse_search_results] props keys: {list(props.keys())}")
            pp = props.get("pageProps", {})
            eprint(f"[parse_search_results] pageProps keys: {list(pp.keys())}")

    return results


def extract_model_fields(item: dict) -> dict | None:
    """Extract standardized model fields from a raw search result item.

    Handles multiple possible field naming conventions.
    """
    if not isinstance(item, dict):
        return None

    model = {}

    # ID
    model_id = item.get("id") or item.get("designId") or item.get("modelId") or item.get("design_id")
    if not model_id:
        return None
    model["id"] = str(model_id)

    # Name / title
    model["name"] = (
        item.get("title") or item.get("name") or
        item.get("designTitle") or item.get("model_name") or
        "Untitled"
    )

    # URL
    model["url"] = f"{MAKERWORLD_BASE}/en/models/{model['id']}"

    # Thumbnail
    model["thumbnail"] = (
        item.get("cover") or item.get("thumbnail") or
        item.get("coverUrl") or item.get("image") or
        item.get("cover_url") or ""
    )

    # Rating
    rating = item.get("rating") or item.get("ratingAvg") or item.get("rating_avg") or 0
    try:
        model["rating"] = round(float(rating), 1)
    except (ValueError, TypeError):
        model["rating"] = 0.0

    # Download count
    dl = item.get("downloadCount") or item.get("download_count") or item.get("downloads") or 0
    try:
        model["download_count"] = int(dl)
    except (ValueError, TypeError):
        model["download_count"] = 0

    # Like count
    likes = item.get("likeCount") or item.get("like_count") or item.get("likes") or 0
    try:
        model["like_count"] = int(likes)
    except (ValueError, TypeError):
        model["like_count"] = 0

    # License
    model["license"] = (
        item.get("license") or item.get("licenseName") or
        item.get("license_name") or ""
    )

    # File formats (if available)
    formats = item.get("fileFormats") or item.get("file_formats") or []
    if isinstance(formats, list):
        model["file_formats"] = formats

    # Score and recommendation will be set later
    model["score"] = 0.0
    model["recommended"] = False

    return model


def calculate_score(rating: float, download_count: int, max_downloads: int) -> float:
    """Combined score: 60% normalized rating + 40% normalized downloads."""
    norm_rating = rating / 5.0 if rating > 0 else 0
    norm_downloads = download_count / max_downloads if max_downloads > 0 else 0
    return round(0.6 * norm_rating + 0.4 * norm_downloads, 4)


def build_recommendation_reason(model: dict) -> str:
    """Build a human-readable recommendation reason."""
    rating = model.get("rating", 0)
    dl = model.get("download_count", 0)

    if dl >= 10000:
        dl_str = f"{dl // 1000}k+"
    elif dl >= 1000:
        dl_str = f"{dl / 1000:.1f}k"
    else:
        dl_str = str(dl)

    if rating >= 4.5 and dl >= 1000:
        return f"Highest rated ({rating}) with {dl_str} downloads"
    elif rating >= 4.5:
        return f"Top rated at {rating} stars"
    elif dl >= 5000:
        return f"Most popular with {dl_str} downloads"
    else:
        return f"Best match (rating: {rating}, downloads: {dl_str})"


def try_api_search(page, query: str, limit: int) -> list[dict]:
    """Fallback: try internal API search from browser context."""
    try:
        eprint("[try_api_search] Attempting internal API search...")
        api_url = f"{MAKERWORLD_BASE}/api/v1/design-service/search/design?keyword={quote_plus(query)}&limit={limit}"
        response = page.evaluate(f"""
            async () => {{
                try {{
                    const resp = await fetch('{api_url}');
                    if (!resp.ok) return {{ error: resp.status }};
                    return await resp.json();
                }} catch(e) {{
                    return {{ error: e.message }};
                }}
            }}
        """)

        if isinstance(response, dict) and "error" in response:
            eprint(f"[try_api_search] API returned error: {response['error']}")
            return []

        # Try to find results in the response
        items = []
        if isinstance(response, list):
            items = response
        elif isinstance(response, dict):
            for key in ["items", "hits", "data", "designs", "results", "list"]:
                if key in response and isinstance(response[key], list):
                    items = response[key]
                    break

        results = []
        for item in items[:limit]:
            model = extract_model_fields(item)
            if model:
                results.append(model)

        if results:
            eprint(f"[try_api_search] Found {len(results)} results via API")
        return results

    except Exception as e:
        eprint(f"[try_api_search] Error: {e}")
        return []


def search_makerworld(query: str, limit: int = 3) -> dict:
    """Search MakerWorld and return structured results."""
    from playwright.sync_api import sync_playwright

    playwright = None
    browser = None
    try:
        playwright = sync_playwright().start()
        browser = get_browser_context(playwright)
        page = browser.new_page()

        # Navigate to search page
        search_url = f"{MAKERWORLD_BASE}/en/search/models?keyword={quote_plus(query)}"
        eprint(f"[search] Navigating to: {search_url}")

        page.goto(search_url, wait_until="networkidle", timeout=60000)

        # Wait for content past Cloudflare
        content_loaded = wait_for_content(page)
        if not content_loaded:
            eprint("[search] Content did not load -- may be stuck on Cloudflare challenge")

        # Extract __NEXT_DATA__
        next_data = extract_next_data(page)
        results = parse_search_results(next_data, limit)

        # Fallback: try API search if __NEXT_DATA__ parsing returned nothing
        if not results:
            eprint("[search] No results from __NEXT_DATA__, trying API fallback...")
            results = try_api_search(page, query, limit)

        # Calculate scores and rank
        if results:
            max_dl = max(r["download_count"] for r in results) or 1
            for r in results:
                r["score"] = calculate_score(r["rating"], r["download_count"], max_dl)
            results.sort(key=lambda r: r["score"], reverse=True)
            results[0]["recommended"] = True
            results[0]["recommendation_reason"] = build_recommendation_reason(results[0])
            for r in results[1:]:
                r["recommended"] = False

        page.close()

        return {
            "status": "ok",
            "results": results,
            "query": query,
            "total_found": len(results),
        }

    except Exception as e:
        eprint(f"[search] Error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "query": query,
        }
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if playwright:
            try:
                playwright.stop()
            except Exception:
                pass


def parse_model_details(next_data: dict | None) -> dict:
    """Parse model details from __NEXT_DATA__ on a model page.

    Returns dict with instance IDs, file info, and metadata.
    """
    details = {"instances": [], "name": "", "id": ""}

    if not next_data:
        return details

    try:
        page_props = next_data.get("props", {}).get("pageProps", {})

        # Try common patterns for model detail data
        design = None
        for key in ["design", "model", "designDetail", "modelDetail", "data"]:
            if key in page_props:
                design = page_props[key]
                eprint(f"[parse_model_details] Found design at pageProps.{key}")
                break

        # Also check dehydratedState
        if not design and "dehydratedState" in page_props:
            queries = page_props["dehydratedState"].get("queries", [])
            for q in queries:
                state_data = q.get("state", {}).get("data", {})
                if isinstance(state_data, dict):
                    # Look for design-like data (has instances or files)
                    if any(k in state_data for k in ["instances", "files", "designId", "title"]):
                        design = state_data
                        eprint("[parse_model_details] Found design in dehydratedState")
                        break

        if not design:
            eprint(f"[parse_model_details] Could not find design data. pageProps keys: {list(page_props.keys())}")
            return details

        details["name"] = design.get("title") or design.get("name") or ""
        details["id"] = str(design.get("id") or design.get("designId") or "")

        # Extract instances (each instance can have downloadable files)
        instances = design.get("instances") or design.get("files") or []
        if isinstance(instances, list):
            for inst in instances:
                if isinstance(inst, dict):
                    inst_info = {
                        "id": str(inst.get("id") or inst.get("instanceId") or ""),
                        "name": inst.get("name") or inst.get("fileName") or inst.get("title") or "",
                        "format": "",
                    }
                    # Detect format from name or type
                    name_lower = inst_info["name"].lower()
                    if ".3mf" in name_lower:
                        inst_info["format"] = "3mf"
                    elif ".stl" in name_lower:
                        inst_info["format"] = "stl"
                    else:
                        inst_info["format"] = inst.get("format") or inst.get("fileType") or "unknown"

                    if inst_info["id"]:
                        details["instances"].append(inst_info)

        eprint(f"[parse_model_details] Found {len(details['instances'])} instances")

    except Exception as e:
        eprint(f"[parse_model_details] Error: {e}")

    return details


def download_file_from_url(page, url: str, output_path: Path) -> bool:
    """Download a file from a URL using the browser context."""
    try:
        eprint(f"[download] Fetching: {url}")
        # Use page.evaluate to fetch with browser cookies
        file_data = page.evaluate(f"""
            async () => {{
                try {{
                    const resp = await fetch('{url}');
                    if (!resp.ok) return {{ error: resp.status }};
                    const buffer = await resp.arrayBuffer();
                    const bytes = Array.from(new Uint8Array(buffer));
                    return {{ bytes: bytes, size: bytes.length }};
                }} catch(e) {{
                    return {{ error: e.message }};
                }}
            }}
        """)

        if isinstance(file_data, dict) and "error" in file_data:
            eprint(f"[download] Fetch error: {file_data['error']}")
            return False

        if isinstance(file_data, dict) and "bytes" in file_data:
            data = bytes(file_data["bytes"])
            output_path.write_bytes(data)
            eprint(f"[download] Saved: {output_path} ({len(data)} bytes)")
            return True

        return False

    except Exception as e:
        eprint(f"[download] Error downloading: {e}")
        return False


def download_model(model_id: str, model_name: str, output_dir: str) -> dict:
    """Download model files from MakerWorld."""
    from playwright.sync_api import sync_playwright

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    playwright = None
    browser = None
    try:
        playwright = sync_playwright().start()
        browser = get_browser_context(playwright)
        page = browser.new_page()

        # Navigate to model page
        model_url = f"{MAKERWORLD_BASE}/en/models/{model_id}"
        eprint(f"[download] Navigating to: {model_url}")
        page.goto(model_url, wait_until="networkidle", timeout=60000)

        # Wait for content
        wait_for_content(page)

        # Extract model details
        next_data = extract_next_data(page)
        details = parse_model_details(next_data)

        downloaded_files = []

        if not details["instances"]:
            eprint("[download] No instances found, trying direct API approach...")

        # Sort instances: 3MF first, then STL, then others
        format_priority = {"3mf": 0, "stl": 1}
        sorted_instances = sorted(
            details["instances"],
            key=lambda x: format_priority.get(x["format"], 2),
        )

        # Download all files (per locked decision)
        for inst in sorted_instances:
            instance_id = inst["id"]

            # Try 3MF download API first
            api_url = f"{MAKERWORLD_BASE}/api/v1/design-service/instance/{instance_id}/f3mf?type=download"
            eprint(f"[download] Trying API for instance {instance_id}: {api_url}")

            response = page.evaluate(f"""
                async () => {{
                    try {{
                        const resp = await fetch('{api_url}');
                        if (!resp.ok) return {{ error: resp.status }};
                        const data = await resp.json();
                        return data;
                    }} catch(e) {{
                        return {{ error: e.message }};
                    }}
                }}
            """)

            time.sleep(1)  # Rate limiting

            if isinstance(response, dict) and "error" not in response:
                # Response should contain a download URL
                download_url = response.get("url") or response.get("downloadUrl") or response.get("download_url")

                if download_url:
                    # Determine filename
                    fname = inst["name"] if inst["name"] else f"model_{instance_id}"
                    if not any(fname.lower().endswith(ext) for ext in [".3mf", ".stl", ".obj"]):
                        fname += ".3mf"

                    # Sanitize filename
                    fname = fname.replace("/", "-").replace("\\", "-")
                    file_path = output_path / fname

                    if download_file_from_url(page, download_url, file_path):
                        fmt = "3mf" if fname.lower().endswith(".3mf") else (
                            "stl" if fname.lower().endswith(".stl") else "other"
                        )
                        downloaded_files.append({
                            "name": fname,
                            "path": str(file_path),
                            "format": fmt,
                        })
                else:
                    eprint(f"[download] No download URL in API response for instance {instance_id}")
                    eprint(f"[download] Response keys: {list(response.keys()) if isinstance(response, dict) else 'not a dict'}")
            else:
                eprint(f"[download] API error for instance {instance_id}: {response}")

        page.close()

        if not downloaded_files:
            return {
                "status": "error",
                "error": "No files could be downloaded. The model may require authentication or have restricted downloads.",
                "model_id": model_id,
                "model_name": model_name,
                "output_dir": str(output_path),
            }

        return {
            "status": "ok",
            "model_id": model_id,
            "model_name": model_name,
            "output_dir": str(output_path),
            "files": downloaded_files,
        }

    except Exception as e:
        eprint(f"[download] Error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "model_id": model_id,
            "model_name": model_name,
        }
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if playwright:
            try:
                playwright.stop()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="MakerWorld search and download CLI for the /print skill",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Search subcommand
    search_parser = subparsers.add_parser("search", help="Search MakerWorld for 3D models")
    search_parser.add_argument("query", help="Search query (e.g., 'phone stand')")
    search_parser.add_argument(
        "--limit", type=int, default=3,
        help="Maximum number of results (default: 3)",
    )

    # Download subcommand
    download_parser = subparsers.add_parser("download", help="Download model files from MakerWorld")
    download_parser.add_argument("model_id", help="MakerWorld model ID")
    download_parser.add_argument("--name", required=True, help="Model name (for folder naming)")
    download_parser.add_argument("--output-dir", required=True, help="Output directory path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "search":
        result = search_makerworld(args.query, args.limit)
        output_json(result)

    elif args.command == "download":
        result = download_model(args.model_id, args.name, args.output_dir)
        output_json(result)


if __name__ == "__main__":
    # Only check Playwright when actually running a command (not --help)
    has_command = len(sys.argv) > 1 and sys.argv[1] in ("search", "download")
    has_help = "--help" in sys.argv or "-h" in sys.argv
    if has_command and not has_help:
        try:
            import importlib
            importlib.import_module("playwright")
        except ImportError:
            output_error(
                "playwright_not_installed",
                fix="Run: pip install playwright && playwright install chromium",
            )
            sys.exit(1)

    main()
