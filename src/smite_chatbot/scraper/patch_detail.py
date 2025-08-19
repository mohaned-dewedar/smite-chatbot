from typing import Dict, List, Optional

from .base import BaseScraper

import re

def _headline_text(h):
    el = h.select_one(".mw-headline")
    txt = el.get_text(" ", strip=True) if el else h.get_text(" ", strip=True)
    # harden against stray edit text if present
    return re.sub(r'\s*\[\s*edit(?:\s*\|\s*edit\s*source)?\s*\]\s*$', "", txt, flags=re.I)
class PatchDetailScraper(BaseScraper):
    """
    Scrapes a single patch page and normalizes its content into structured fields
    suitable for Q&A and change tracking.
    """

    def parse_patch_page(self, url: str) -> Dict[str, object]:
        soup = self.get_soup(url)
        content = soup.select_one("#mw-content-text") or soup

        title_el = soup.select_one("#firstHeading")
        title = (title_el.get_text(strip=True) if title_el else "").strip()

        def section_texts(keywords: List[str]) -> List[str]:
            acc: List[str] = []
            for header in content.select("h2, h3"):
                htxt = _headline_text(header).lower()
                if any(k in htxt for k in keywords):
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

        def entity_changes_by_h3(section_keywords: List[str]) -> List[Dict[str, object]]:
            """
            Parse a balance section (e.g., Item Balance, God Balance) into a list of
            {name, title, changes[]} where `title` is the raw header text and name is
            stripped of parenthetical qualifiers.
            """
            results: List[Dict[str, object]] = []

            # Locate the section root (h2)
            root = None
            for h2 in content.select("h2"):
                txt = _headline_text(h2).lower()
                if any(k in txt for k in section_keywords):
                    root = h2
                    break
            if root is None:
                return results

            # Iterate until next h2; capture h3 entity blocks
            node = root
            while node is not None:
                node = node.find_next()
                if node is None:
                    break
                name = getattr(node, "name", "").lower()
                if name == "h2":
                    break
                if name == "h3":
                    if name == "h3":
                        header_text = _headline_text(node)           # <-- no "edit | edit source"
                        display_name = header_text.split(" (")[0].strip()
                    changes: List[str] = []
                    # Collect lists until next h3 or h2
                    cursor = node
                    while True:
                        cursor = cursor.find_next()
                        if cursor is None:
                            break
                        cname = getattr(cursor, "name", "").lower()
                        if cname in {"h3", "h2"}:
                            break
                        if cname in {"ul", "ol"}:
                            for li in cursor.select("li"):
                                txt = li.get_text(" ", strip=True)
                                if txt:
                                    changes.append(txt)
                    results.append({
                        "title": header_text,
                        "name": display_name,
                        "changes": changes,
                    })
            return results

        def item_balance_from_bold(section_keywords: List[str]) -> List[Dict[str, object]]:
            """
            Parse Item Balance where items appear as bolded labels (<b>Ancient Signet (Buff)</b>)
            followed by a <ul> of bullet changes, repeating. Falls back to h3 parsing when present.
            """
            # Prefer h3-based parsing if present
            h3_based = entity_changes_by_h3(section_keywords)
            if h3_based:
                return h3_based

            results: List[Dict[str, object]] = []
            # Locate the section root (h2)
            root = None
            for h2 in content.select("h2"):
                txt = _headline_text(h2).lower()
                if any(k in txt for k in section_keywords):
                    root = h2
                    break
            if root is None:
                return results

            node = root
            current_item_title = None
            current_item_name = None
            while node is not None:
                node = node.find_next()
                if node is None:
                    break
                name = getattr(node, "name", "").lower()
                if name == "h2":
                    break
                # pattern: <p><b>Item Name (Qualifier)</b></p>
                if name == "p":
                    b = node.select_one("b")
                    if b:
                        header_text = b.get_text(" ", strip=True)
                        if header_text:
                            current_item_title = header_text
                            current_item_name = header_text.split(" (")[0].strip()
                            results.append({
                                "title": current_item_title,
                                "name": current_item_name,
                                "changes": [],
                            })
                        continue
                if name in {"ul", "ol"} and results:
                    # attach bullets to the last seen item
                    for li in node.select("li"):
                        txt = li.get_text(" ", strip=True)
                        if txt:
                            results[-1]["changes"].append(txt)
            # Filter out entries with no changes
            results = [r for r in results if r.get("changes")]
            return results

        return {
            "title": title or None,
            "url": url,
            "highlights": section_texts(["new god", "new content", "highlight"]),
            # Structured entity changes
            "god_balance": entity_changes_by_h3(["god balance", "gods"]),
            "item_balance": item_balance_from_bold(["item balance", "items"]),
            "systems": section_texts(["system", "mode", "gameplay", "quality of life", "qol"]),
            "bug_fixes": section_texts(["bug", "fix"]),
        }

    def scrape_many(self, patches: List[Dict[str, str]], *, out_dir: Optional[str] = None) -> str:
        out_dir = out_dir or self.default_outdir()
        detailed: List[Dict[str, object]] = []
        for entry in patches:
            try:
                parsed = self.parse_patch_page(entry["url"])
                parsed.update({
                    "release_date": entry.get("release_date"),
                    "phase": entry.get("phase"),
                })
                detailed.append(parsed)
            except Exception:
                continue
        out_path = f"{out_dir}/patch_details.json"
        self.save_json({
            "total": len(detailed),
            "patches": detailed,
        }, out_path)
        return out_path


