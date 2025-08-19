from typing import Dict, List, Optional
from urllib.parse import urljoin

from .base import BaseScraper


class PatchNotesScraper(BaseScraper):
    """
    Scrapes the Patch Notes hub and individual patch notes pages.
    Output is normalized to help a chatbot answer questions by release.
    """

    def __init__(self, base_url: str = "https://wiki.smite2.com/") -> None:
        super().__init__(base_url)

    def hub_url(self) -> str:
        """
        Determine the patch notes hub URL by scanning the main page for a link
        labeled/title'd like "Patch Notes". Falls back to common slugs.
        """
        # Try to discover from main page
        try:
            main = self.get_soup(urljoin(self.base_url, ""))
            for a in (main.select_one("#mw-content-text") or main).select("a[href][title]"):
                title = (a.get("title") or "").strip().lower()
                text = a.get_text(" ", strip=True).lower()
                if ("patch notes" in title) or ("patch notes" in text):
                    href = a.get("href") or ""
                    if href.startswith("/"):
                        return urljoin(self.base_url, href)
        except Exception:
            pass

        # Fallback candidates
        for slug in ("w/Patch_Notes", "w/Patch_notes", "w/Patch_notes_(Full_list)"):
            candidate = urljoin(self.base_url, slug)
            try:
                self.get(candidate)
                return candidate
            except Exception:
                continue
        # Last resort to main page
        return urljoin(self.base_url, "")

    def list_patch_notes(self) -> List[Dict[str, str]]:
        """
        Parse the Patch notes hub tables to extract patch page URL, title, and release date.
        The hub organizes notes into multiple sections (Open Beta, Closed Alpha, Alpha Weekend Test).
        """
        soup = self.get_soup(self.hub_url())
        content = soup.select_one("#mw-content-text") or soup
        results: List[Dict[str, str]] = []

        for h2 in content.select("h2"):
            headline = h2.get_text(" ", strip=True)
            phase = headline.replace("edit", "").strip()
            table = h2.find_next("table", class_="wikitable")
            if not table:
                continue
            rows = table.select("tr")
            if not rows or len(rows) < 2:
                continue
            for tr in rows[1:]:
                tds = tr.select("td")
                if len(tds) < 2:
                    continue
                link = tds[0].select_one("a[href]")
                if not link:
                    continue
                href = link.get("href") or ""
                if not href.startswith("/"):
                    continue
                title = (link.get("title") or link.get_text(" ", strip=True) or "").strip()
                release_date = tds[1].get_text(" ", strip=True)
                results.append({
                    "title": title,
                    "url": urljoin(self.base_url, href),
                    "release_date": release_date,
                    "phase": phase,
                })

        # de-duplicate by url preserving first occurrence (usually newest first in hub)
        seen = set()
        unique: List[Dict[str, str]] = []
        for r in results:
            if r["url"] in seen:
                continue
            seen.add(r["url"])
            unique.append(r)
        return unique

    def parse_patch_page(self, url: str) -> Dict[str, object]:
        soup = self.get_soup(url)
        title_el = soup.select_one("#firstHeading")
        title = (title_el.get_text(strip=True) if title_el else "").strip()

        # Extract sections: New God, God changes, Item changes, Systems, Bug Fixes
        content = soup.select_one("#mw-content-text") or soup

        def harvest_section(keywords: List[str]) -> List[str]:
            acc: List[str] = []
            for header in content.select("h2, h3"):
                htxt = header.get_text(" ", strip=True).lower()
                if any(k in htxt for k in keywords):
                    # collect bullets until next header of same rank
                    for sib in header.find_all_next():
                        name = getattr(sib, "name", "").lower()
                        if name in {"h2", "h3"}:
                            break
                        if name in {"ul", "ol"}:
                            for li in sib.select("li"):
                                txt = li.get_text(" ", strip=True)
                                if txt:
                                    acc.append(txt)
                    break
            return acc

        new_content = harvest_section(["new god", "new content", "highlights"])
        god_changes = harvest_section(["god", "gods"])
        item_changes = harvest_section(["item", "items"])
        systems = harvest_section(["system", "mode", "gameplay", "quality of life", "qol"])  # noqa: E501
        bugfixes = harvest_section(["bug", "fix"])  # noqa: E501

        return {
            "title": title or None,
            "url": url,
            "new_content": new_content,
            "god_changes": god_changes,
            "item_changes": item_changes,
            "systems": systems,
            "bug_fixes": bugfixes,
        }

    def scrape(self, *, out_dir: Optional[str] = None, limit: Optional[int] = None) -> str:
        out_dir = out_dir or self.default_outdir()
        notes = self.list_patch_notes()
        if limit is not None:
            notes = notes[:limit]
        detailed: List[Dict[str, object]] = []
        for entry in notes:
            try:
                parsed = self.parse_patch_page(entry["url"])
                # enrich with hub metadata
                parsed.update({
                    "release_date": entry.get("release_date"),
                    "phase": entry.get("phase"),
                })
                detailed.append(parsed)
            except Exception:
                continue
        out_path = f"{out_dir}/patch_notes.json"
        self.save_json({
            "total_releases": len(detailed),
            "releases": detailed,
        }, out_path)
        return out_path


