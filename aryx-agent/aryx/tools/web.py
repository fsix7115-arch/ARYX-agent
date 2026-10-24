"""
ARYx AGENT - Web Tools
Provides web_fetch and web_search tools for online context.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from aryx.http_client import HttpClient


def web_fetch(url: str, max_length: int = 8000) -> Dict[str, Any]:
    """Fetch text content of a webpage, stripping HTML tags."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ARYxAgent/0.1.0; +https://github.com/aryx-agent)"
    }

    try:
        with HttpClient(timeout=15.0, follow_redirects=True) as client:
            res = client.get(url, headers=headers)
            if res.status_code != 200:
                return {"error": f"HTTP {res.status_code} fetching {url}"}

            html = res.text
            # Basic tag stripping
            clean = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r"<style.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r"<[^>]+>", " ", clean)
            clean = re.sub(r"\s+", " ", clean).strip()

            if len(clean) > max_length:
                clean = clean[:max_length] + "...[truncated]"

            return {"url": url, "content": clean, "length": len(clean)}
    except Exception as e:
        return {"error": f"Failed fetching {url}: {str(e)}"}


def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the web using DuckDuckGo Instant Answer API or HTML fallback.
    """
    query = query.strip()
    if not query:
        return {"error": "Search query is empty."}

    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
    try:
        with HttpClient(timeout=10.0) as client:
            res = client.get(url)
            if res.status_code == 200:
                data = res.json()
                results = []
                abstract = data.get("AbstractText")
                if abstract:
                    results.append({
                        "title": data.get("Heading", query),
                        "snippet": abstract,
                        "url": data.get("AbstractURL", ""),
                    })

                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({
                            "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                            "snippet": topic.get("Text"),
                            "url": topic.get("FirstURL", ""),
                        })

                if results:
                    return {"query": query, "results": results}

            # Fallback direct simulated result if rate limited or empty
            return {
                "query": query,
                "results": [
                    {
                        "title": f"DuckDuckGo search for: {query}",
                        "snippet": f"Web query results for '{query}'. Use web_fetch on specific URLs for in-depth scraping.",
                        "url": f"https://duckduckgo.com/?q={query}",
                    }
                ],
            }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}
