import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import re
import json

class AbilityScraper:
    def __init__(self, base_url='https://wiki.smite2.com/'):
        self.base_url = base_url
        self.gods_abilities: List[Dict] = []

    def parse_stat_lines(self, stat_text: str) -> Dict[str, str]:
        """Parse a block of text into a stat dictionary"""
        parsed_stats = {}
        for line in stat_text.splitlines():
            match = re.match(r"^(.*?):\s*(.*)$", line)
            if match:
                key, value = match.groups()
                parsed_stats[key.strip()] = value.strip()
        return parsed_stats

    def parse_god_abilities(self, god_url: str) -> List[Dict]:
        response = requests.get(god_url)
        soup = BeautifulSoup(response.text, "html.parser")
        tables = soup.find_all("table", class_="wikitable")
        abilities = []

        for table in tables:
            rows = table.find_all("tr")
            if not rows or len(rows) < 2:
                continue

            # -- Ability name and type
            header = rows[0].find("th")
            name_type = header.get_text(separator="|", strip=True).split("|")
            ability_type = name_type[0].replace("-", "").strip() if len(name_type) > 0 else ""
            ability_name = name_type[1].strip() if len(name_type) > 1 else ""

            # -- Description
            desc_cell = rows[1].find_all("td")
            ability_description = desc_cell[1].get_text(separator=" ", strip=True) if len(desc_cell) > 1 else ""

            # -- Stats
            stats_row = rows[2].find("td") if len(rows) > 2 else None
            raw_stats = ""
            if stats_row:
                raw_stats = "\n".join(stats_row.stripped_strings)
            parsed_stats = self.parse_stat_lines(raw_stats)

            # -- Notes
            notes_cell = rows[0].find_all("td")
            ability_notes = notes_cell[-1].get_text(separator="\n", strip=True) if len(notes_cell) >= 1 else ""

            abilities.append({
                "name": ability_name,
                "type": ability_type,
                "description": ability_description,
                "stats": parsed_stats,
                "notes": ability_notes
            })

        self.gods_abilities.extend(abilities)
        return abilities

    def parse_all_gods_abilities(self,json_path: str):
        with open(json_path, "r") as f:
            data = json.load(f)
        for god in data["gods"]:
            abilities = self.parse_god_abilities(god["profile_url"])
            print(f"God: {god['name']} has {len(abilities)} abilities")
            god["abilities"] = abilities
        with open("gods_abilities.json", "w") as f:
            json.dump(data, f, indent=2)

# Example usage
if __name__ == "__main__":
    AS = AbilityScraper()
    AS.parse_all_gods_abilities("smite_gods.json")
