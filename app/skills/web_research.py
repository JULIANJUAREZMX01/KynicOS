"""
KynicOS — Skill: Web Research
Investigación web autárquica. Sin API keys.
Usa DuckDuckGo HTML (sin JS, sin rate limit agresivo) como fuente primaria.
Fallback: búsqueda directa en GitHub, Wikipedia, PyPI.

El skill puede ser usado por el LLM para:
  - Investigar tecnologías antes de construir un nuevo skill
  - Consultar documentación técnica
  - Buscar repositorios GitHub de referencia
  - Obtener noticias técnicas recientes
"""

import asyncio
import re
from typing import List, Dict, Optional
import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; KynicOS/2.0; +https://kynicos.dev)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es,en;q=0.9",
}

TIMEOUT = 10


async def search_ddg(query: str, max_results: int = 5) -> List[Dict]:
    """Búsqueda DuckDuckGo sin API key (HTML scraping ligero)."""
    results = []
    try:
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []
            html = resp.text
            # Extraer resultados: título + snippet + url
            titles = re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', html, re.S)
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</span>', html, re.S)
            urls = re.findall(r'result__url[^>]*>(.*?)</a>', html, re.S)
            for i in range(min(max_results, len(titles))):
                results.append({
                    "title": re.sub(r"<[^>]+>", "", titles[i]).strip(),
                    "snippet": re.sub(r"<[^>]+>", "", snippets[i] if i < len(snippets) else "").strip(),
                    "url": urls[i].strip() if i < len(urls) else "",
                })
    except Exception as e:
        results.append({"title": "Error", "snippet": str(e), "url": ""})
    return results


async def fetch_url(url: str, max_chars: int = 2000) -> str:
    """Fetch simple de una URL, devuelve texto plano."""
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            text = re.sub(r"<[^>]+>", " ", resp.text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:max_chars]
    except Exception as e:
        return f"Error: {e}"


async def search_github(query: str, max_results: int = 5) -> List[Dict]:
    """Búsqueda de repos en GitHub sin API key (rate limit generoso para GET)."""
    results = []
    try:
        url = f"https://api.github.com/search/repositories?q={query.replace(' ', '+')}&sort=stars&per_page={max_results}"
        async with httpx.AsyncClient(headers={"Accept": "application/vnd.github.v3+json"}, timeout=TIMEOUT) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for repo in data.get("items", []):
                    results.append({
                        "title": repo["full_name"],
                        "snippet": (repo.get("description") or "")[:200],
                        "url": repo["html_url"],
                        "stars": repo.get("stargazers_count", 0),
                    })
    except Exception as e:
        results.append({"title": "Error GitHub", "snippet": str(e), "url": ""})
    return results


async def run(
    query: str,
    source: str = "web",  # web | github | url
    url: Optional[str] = None,
    max_results: int = 5,
) -> str:
    """
    Función principal del skill.
    - source='web'    → DuckDuckGo
    - source='github' → GitHub repos
    - source='url'    → fetch directo de URL
    """
    if source == "url" and url:
        content = await fetch_url(url)
        return f"📄 Contenido de {url}:\n\n{content}"

    if source == "github":
        results = await search_github(query, max_results)
    else:
        results = await search_ddg(query, max_results)

    if not results:
        return f"Sin resultados para: {query}"

    lines = [f"🔍 Resultados para: **{query}**\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        if r.get("snippet"):
            lines.append(f"   {r['snippet'][:150]}")
        if r.get("url"):
            lines.append(f"   🔗 {r['url']}")
        if r.get("stars"):
            lines.append(f"   ⭐ {r['stars']}")
    return "\n".join(lines)
