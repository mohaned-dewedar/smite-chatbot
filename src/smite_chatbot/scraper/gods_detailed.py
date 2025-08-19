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
        # find the Abilities section using modern structure
        abilities_h2 = soup.select_one("h2 #Abilities") or soup.find("h2", string=re.compile(r"Abilities", re.I))
        container = abilities_h2.find_parent("h2") if abilities_h2 else abilities_h2
        
        # Debug info can be removed for production
        
        if container:
            # Look for ability sections after the Abilities h2
            current = container.find_next_sibling()
            while current and current.name != "h2":
                
                # Look for ability patterns - tables contain the ability data
                if current.name == "table":
                    # Get the ability header from the first cell/row of the table
                    first_cell = current.select_one("th, td")
                    if first_cell:
                        first_line = _txt(first_cell)
                    else:
                        # Fallback to first line of full text
                        ability_header = _txt(current)
                        first_line = ability_header.split('\n')[0] if ability_header else ""
                    
                    ability_type, ability_name = _parse_ability_header(first_line)
                    
                    if ability_name and ability_name != "-":
                        # Parse content within the table itself
                        table_text = _txt(current)
                        lines = table_text.split('\n')
                        
                        # Skip the header line (first line) and process the rest
                        content_lines = []
                        skip_first = True
                        for line in lines:
                            line = line.strip()
                            if skip_first and line == first_line:
                                skip_first = False
                                continue
                            if line:
                                content_lines.append(line)
                        
                        desc_parts = []
                        stats = {}
                        notes = ""
                        
                        # The content is all in one line, we need to parse it dynamically
                        if content_lines:
                            full_content = " ".join(content_lines)
                            # 1. Extract notes first (everything after "Notes:")
                            notes_match = re.search(r'Notes:\s*([^.]*?)(?=\s+[A-Z][a-z]+|\s*$)', full_content)
                            if notes_match:
                                notes_text = notes_match.group(1).strip()
                                notes = f"Notes:\n{notes_text}"
                                # Remove notes from content for further processing
                                full_content = re.sub(r'Notes:\s*[^.]*?(?=\s+[A-Z][a-z]+)', '', full_content)
                            
                            # 2. Extract description (look for sentences that describe what ability does)
                            # Description usually comes after ability name and before stats
                            # Look for complete sentences (capital letter start, period end or before stats)
                            desc_match = re.search(r'([A-Z][^:]*?(?:\.|(?=\s+[A-Z][a-z]*\s*:)))', full_content)
                            if desc_match:
                                description = desc_match.group(1).strip()
                                # Clean up description
                                if description.endswith('.'):
                                    description = description[:-1]
                            
                            # 3. Extract all stats dynamically (any "Word : Value" pattern)
                            # Look for patterns like "Damage : 100 | 150", "Range : 5 meters", etc.
                            stat_matches = re.finditer(r'([A-Z][A-Za-z\s]*?)\s*:\s*([^A-Z]+?)(?=\s*[A-Z][A-Za-z\s]*\s*:|$)', full_content)
                            
                            for match in stat_matches:
                                key = match.group(1).strip()
                                value = match.group(2).strip()
                                
                                # Skip if this looks like the ability name or notes
                                if key.lower().startswith('notes') or len(key.split()) > 4:
                                    continue
                                    
                                # Clean up the value
                                value = re.sub(r'\s+', ' ', value).strip()
                                if value:
                                    stats[key] = value
                        
                        # Compile ability data
                        description = " ".join(desc_parts) if desc_parts else ""
                        
                        abilities.append({
                            "name": ability_name,
                            "type": ability_type,
                            "description": description,
                            "stats": stats,
                            "notes": notes
                        })
                
                current = current.find_next_sibling()

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


