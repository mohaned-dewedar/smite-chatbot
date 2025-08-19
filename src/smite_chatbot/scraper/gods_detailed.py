import re
from typing import Dict, List, Optional

from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .base import BaseScraper

def _txt(el): return el.get_text(" ", strip=True) if el else ""

def _clean_templates(s: str) -> str:
    s = re.sub(r"\{\{\{[^}]+\}\}\}", "", s)   # drop {{{template}}}
    return re.sub(r"\s+", " ", s).strip()

def _parse_ability_header(s: str) -> tuple[str, str]:
    # "Passive - Gift of the Gods | CHOOSE ARMOR" -> ("Passive", "Gift of the Gods")
    m = re.match(r"^\s*([^-|]+?)(?:\s*-\s*([^|]+))?(?:\s*\|.*)?$", s)
    if not m: return "-", "-"
    atype = m.group(1).strip()
    aname = (m.group(2) or "-").strip()
    return atype, aname

class GodsDetailedScraper(BaseScraper):
    """
    Fetches god list from main page and scrapes per-god details:
    - Name, URL, key infobox properties (Pantheon, Type/Role), image URL if present
    - Abilities parsed from wikitable layout
    """

    def main_url(self) -> str:
        return urljoin(self.base_url, "")

    def list_gods(self) -> List[Dict[str, str]]:
        """
        Extract god links from the main page. Try multiple selectors to find god containers.
        """
        soup = self.get_soup(self.main_url())
        gods: List[Dict[str, str]] = []
        
        # Try different selectors for god containers
        selectors = [
            '.mp-heroes div[style*="display: inline-block"]',
            '.mp-heroes a[title]',
            'a[title*="God"]',
            'a[href*="/w/"]'
        ]
        
        elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                print(f"Found {len(elements)} elements with selector: {selector}")
                break
        
        if not elements:
            # Fallback: look for any links that might be gods
            elements = soup.select('a[href][title]')
            print(f"Fallback: found {len(elements)} links with titles")
        
        for element in elements:
            # If we got a container, find the link inside
            if element.name == 'div':
                a = element.select_one('a[title]')
            else:
                a = element
            
            if not a:
                continue
                
            title = (a.get("title") or "").strip()
            href = a.get("href") or ""
            
            # Skip if no title or href, or if it's not a god page
            if not title or not href:
                continue
            if not href.startswith('/w/'):
                continue
            if any(skip in title.lower() for skip in ['patch', 'item', 'category', 'special']):
                continue
                
            url = urljoin(self.base_url, href)

            # Try to find an image
            img_url: Optional[str] = None
            container = element if element.name == 'div' else element.parent
            if container:
                for img in container.select('img[src]'):
                    src = img.get('src') or ''
                    if 'Transparent_God_Icon' in src:
                        continue
                    img_url = urljoin(self.base_url, src) if src.startswith('/') else src
                    break

            gods.append({
                "name": title,
                "url": url,
                "image_url": img_url,
            })
            
        print(f"Extracted {len(gods)} gods")
        return gods

    def parse_god_page(self, url: str) -> Dict[str, object]:
        soup = self.get_soup(url)
        title_el = soup.select_one("#firstHeading")
        name = (title_el.get_text(strip=True) if title_el else "").strip()

        info: Dict[str, str] = {}
        infobox = soup.select_one(".infobox, table.infobox")
        if infobox:
            for row in infobox.select("tr"):
                if "style" in row.attrs and "display: none" in row["style"]:
                    continue
                th, td = row.select_one("th"), row.select_one("td")
                if th and td:
                    key = _txt(th)
                    val = _clean_templates(_txt(td))
                    info[key] = val

        abilities = []
        # find the Abilities section
        abilities_h2 = soup.select_one("h2 #Abilities")
        container = abilities_h2.find_parent("h2") if abilities_h2 else None
        if container:
            for sib in container.find_all_next("table", class_="wikitable"):
                head = sib.select_one("th[colspan='2']")
                if not head: break  # stop at unrelated tables

                ability_type, ability_name = _parse_ability_header(_txt(head))

                # description
                desc_td = sib.select_one("tr td[width='526px']")
                desc = _txt(desc_td) if desc_td else ""

                # stats
                stats = {}
                ul = sib.select_one("tr ul")
                if ul:
                    for li in ul.select("li"):
                        txt = _txt(li)
                        if ":" in txt:
                            k, v = txt.split(":", 1)
                            stats[k.strip()] = v.strip()
                        else:
                            stats[""] = txt

                # notes
                notes_td = sib.select_one("td[rowspan]")
                notes = ""
                if notes_td:
                    items = [ _txt(li) for li in notes_td.select("li") ]
                    notes = "Notes:\n" + "\n".join(items) if items else _txt(notes_td)

                abilities.append({
                    "name": ability_name,
                    "type": ability_type,
                    "description": desc,
                    "stats": stats,
                    "notes": notes
                })

        return {
            "name": name or None,
            "url": url,
            "info": info,
            "abilities": abilities,
        }

    def scrape(self, *, out_dir: Optional[str] = None) -> str:
        out_dir = out_dir or self.default_outdir()
        gods = self.list_gods()
        detailed: List[Dict[str, object]] = []
        for g in gods:
            try:
                detailed.append(self.parse_god_page(g["url"]))
            except Exception:
                continue
        out_path = f"{out_dir}/gods.json"
        self.save_json({
            "total_gods": len(detailed),
            "gods": detailed,
        }, out_path)
        return out_path


