"""
KynicOS — Skill: Last30Days Research
Investiga tendencias tecnológicas de los últimos 30 días.
Sin API keys. Fuentes: GitHub trending, HackerNews API (pública), Dev.to API (pública).

Uso por el LLM:
  run(topic="rust wasm")
  run(topic="llm agents", source="hackernews")
  run(topic="fastapi", source="github_trending")
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import httpx

HEADERS = {"User-Agent": "KynicOS/2.0 research-skill"}
TIMEOUT = 12


async def _github_trending(language: Optional[str] = None) -> List[Dict]:
    """GitHub trending repos (últimos 7 días). Sin API key."""
    results = []
    try:
        since = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        url = f"https://api.github.com/search/repositories?q=created:>{since}&sort=stars&order=desc&per_page=10"
        if language:
            url += f"+language:{language}"
        async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT) as c:
            r = await c.get(url)
            if r.status_code == 200:
                for repo in r.json().get("items", [])[:8]:
                    results.append({
                        "title": repo["full_name"],
                        "desc": (repo.get("description") or "")[:150],
                        "stars": repo.get("stargazers_count", 0),
                        "url": repo["html_url"],
                        "lang": repo.get("language", ""),
                    })
    except Exception as e:
        results.append({"title": "Error", "desc": str(e)})
    return results


async def _hackernews_top(keyword: Optional[str] = None) -> List[Dict]:
    """HackerNews API pública — top stories + filtro por keyword."""
    results = []
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT) as c:
            # Top 50 IDs
            r = await c.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            ids = r.json()[:30]

            # Fetch concurrente de los primeros 30
            async def fetch_item(item_id):
                try:
                    ir = await c.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json")
                    return ir.json()
                except Exception:
                    return {}

            items = await asyncio.gather(*[fetch_item(i) for i in ids])
            for item in items:
                if not item or item.get("type") != "story":
                    continue
                title = item.get("title", "")
                if keyword and keyword.lower() not in title.lower():
                    continue
                results.append({
                    "title": title,
                    "url": item.get("url", f"https://news.ycombinator.com/item?id={item.get('id')}"),
                    "score": item.get("score", 0),
                })
                if len(results) >= 8:
                    break
    except Exception as e:
        results.append({"title": "Error HN", "desc": str(e)})
    return results


async def _devto_articles(tag: Optional[str] = None) -> List[Dict]:
    """Dev.to API pública (sin key) — artículos recientes."""
    results = []
    try:
        url = "https://dev.to/api/articles?per_page=10&top=7"
        if tag:
            url += f"&tag={tag.replace(' ', '')}"
        async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT) as c:
            r = await c.get(url)
            if r.status_code == 200:
                for article in r.json()[:8]:
                    results.append({
                        "title": article.get("title", ""),
                        "desc": (article.get("description") or "")[:120],
                        "url": article.get("url", ""),
                        "reactions": article.get("positive_reactions_count", 0),
                    })
    except Exception as e:
        results.append({"title": "Error Dev.to", "desc": str(e)})
    return results


async def run(
    topic: str = "ai agents",
    source: str = "all",  # all | github_trending | hackernews | devto
) -> str:
    """
    Investiga un tema en las últimas tendencias.
    source: all | github_trending | hackernews | devto
    """
    # Extraer posible lenguaje de programación del topic
    lang_map = {"python": "Python", "rust": "Rust", "typescript": "TypeScript", "js": "JavaScript"}
    lang = next((v for k, v in lang_map.items() if k in topic.lower()), None)

    lines = [f"📊 **Tendencias: {topic}** (últimos 30 días)\n"]
    tasks = []

    if source in ("all", "github_trending"):
        tasks.append(("GitHub Trending", _github_trending(lang)))
    if source in ("all", "hackernews"):
        tasks.append(("HackerNews Top", _hackernews_top(topic.split()[0] if topic else None)))
    if source in ("all", "devto"):
        tasks.append(("Dev.to", _devto_articles(topic.replace(" ", ""))))

    results = await asyncio.gather(*[t[1] for t in tasks])

    for (label, _), items in zip(tasks, results):
        if not items:
            continue
        lines.append(f"\n**{label}:**")
        for item in items[:5]:
            title = item.get("title", "")
            url = item.get("url", "")
            extra = item.get("stars") or item.get("score") or item.get("reactions") or ""
            desc = item.get("desc") or item.get("snippet") or ""
            line = f"• {title}"
            if extra:
                line += f" ({extra}⭐)" if isinstance(extra, int) else f" ({extra})"
            lines.append(line)
            if desc:
                lines.append(f"  _{desc[:100]}_")
            if url:
                lines.append(f"  {url}")

    return "\n".join(lines) if len(lines) > 1 else f"Sin resultados para '{topic}'"
