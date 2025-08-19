from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper


class SmiteItemsScraper(BaseScraper):
    """
    Scrapes Items index and individual item pages.
    Produces a normalized JSON suitable for Q&A.
    """

    def __init__(self, base_url: str = "https://wiki.smite2.com/") -> None:
        super().__init__(base_url)

    def items_index_url(self) -> str:
        # Fallback to hub page path, adjust if a dedicated Items page exists differently
        return urljoin(self.base_url, "w/Items")

    def list_items(self) -> List[Dict[str, str]]:
        soup = self.get_soup(self.items_index_url())

        # Strategy: collect all links inside main content that look like item entries.
        # MediaWiki uses #mw-content-text for content area.
        content = soup.select_one("#mw-content-text") or soup
        results: List[Dict[str, str]] = []

        for a in content.select("a[href][title]"):
            title = (a.get("title") or "").strip()
            href = a.get("href") or ""
            if not title or not href:
                continue
            if not href.startswith("/"):
                continue
            # Heuristic: ignore non-item navigational anchors or files/categories
            if any(prefix in href for prefix in ("/wiki/File:", "/wiki/Category:")):
                continue
            # Items often have their own page; we avoid obvious non-item hubs
            if title.lower() in {"items", "patch notes", "gods", "about the game"}:
                continue

            results.append({
                "name": title,
                "profile_url": urljoin(self.base_url, href),
            })

        # De-duplicate by URL
        seen = set()
        unique: List[Dict[str, str]] = []
        for it in results:
            if it["profile_url"] in seen:
                continue
            seen.add(it["profile_url"])
            unique.append(it)

        return unique

    def parse_item_page(self, url: str) -> Dict[str, any]:  # noqa: ANN401 - mixed types in dict
        soup = self.get_soup(url)

        title_el = soup.select_one("#firstHeading")
        item_name = (title_el.get_text(strip=True) if title_el else "").strip()

        # Infobox extraction (key/value rows)
        infobox = soup.select_one(".infobox, table.infobox")
        stats: Dict[str, str] = {}
        if infobox:
            for row in infobox.select("tr"):
                header = row.select_one("th")
                value = row.select_one("td")
                if not header or not value:
                    continue
                key = header.get_text(separator=" ", strip=True)
                val = value.get_text(separator=" ", strip=True)
                if key:
                    stats[key] = val

        # Passive/description blocks
        description_texts: List[str] = []
        content = soup.select_one("#mw-content-text") or soup
        for strong in content.select("p > b, li > b"):
            # Many item passives are bolded names followed by text
            parent = strong.parent
            text = parent.get_text(separator=" ", strip=True)
            if text and strong.get_text(strip=True):
                description_texts.append(text)

        # Changelog or history section
        changelog: List[str] = []
        for header in content.select("h2, h3"):
            htxt = header.get_text(" ", strip=True).lower()
            if any(key in htxt for key in ("changelog", "patch", "changes", "history")):
                # capture bullet list under this section until next header
                for sib in header.find_all_next():
                    if isinstance(sib, (BeautifulSoup,)):
                        continue
                    if getattr(sib, "name", "").lower() in {"h2", "h3"}:
                        break
                    if getattr(sib, "name", "").lower() in {"ul", "ol"}:
                        for li in sib.select("li"):
                            txt = li.get_text(" ", strip=True)
                            if txt:
                                changelog.append(txt)
                break

        return {
            "name": item_name or None,
            "url": url,
            "stats": stats,
            "descriptions": description_texts,
            "changelog": changelog,
        }

    def scrape(self, *, out_dir: Optional[str] = None) -> str:
        out_dir = out_dir or self.default_outdir()
        items = self.list_items()
        detailed: List[Dict[str, any]] = []  # noqa: ANN401
        for entry in items:
            try:
                detailed.append(self.parse_item_page(entry["profile_url"]))
            except Exception:
                # best-effort; continue on failures
                continue

        out_path = f"{out_dir}/items.json"
        self.save_json({
            "total_items": len(detailed),
            "items": detailed,
        }, out_path)
        return out_path


