from typing import Dict, List, Optional
from urllib.parse import urljoin

from .base import BaseScraper
from .patch_notes import PatchNotesScraper


class PatchIndexScraper(BaseScraper):
    """
    Builds an index of all patch notes across phases (Open Beta, Closed Alpha, etc.)
    by leveraging the logic from PatchNotesScraper to discover the hub URL and parse
    the tables. Produces a flat JSON list that other jobs can consume to scrape details.
    """

    def __init__(self, base_url: str = "https://wiki.smite2.com/") -> None:
        super().__init__(base_url)
        self._patch = PatchNotesScraper(base_url)

    def build_index(self) -> List[Dict[str, str]]:
        return self._patch.list_patch_notes()

    def save_index(self, *, out_dir: Optional[str] = None, filename: str = "patch_index.json") -> str:
        out_dir = out_dir or self.default_outdir()
        items = self.build_index()
        out_path = f"{out_dir}/{filename}"
        self.save_json({
            "total": len(items),
            "patches": items,
        }, out_path)
        return out_path


