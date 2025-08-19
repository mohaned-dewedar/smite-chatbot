import argparse
import json
import os
from typing import Dict

from .base import BaseScraper
from .gods_detailed import GodsDetailedScraper
from .items import SmiteItemsScraper
from .patch_notes import PatchNotesScraper
from .patch_index import PatchIndexScraper
from .patch_detail import PatchDetailScraper


def run_all(output_dir: str | None = None, *, limit_patch_notes: int | None = None) -> Dict[str, str]:
    base = BaseScraper()
    out_dir = output_dir or base.default_outdir()

    gods_out = GodsDetailedScraper().scrape(out_dir=out_dir)
    items_out = SmiteItemsScraper().scrape(out_dir=out_dir)
    # Build patch index and detailed pages
    index_path = PatchIndexScraper().save_index(out_dir=out_dir, filename="patch_index.json")
    # Load index
    with open(index_path, "r", encoding="utf-8") as f:
        idx_data = json.load(f)
    patches = idx_data.get("patches", [])
    if limit_patch_notes is not None:
        patches = patches[:limit_patch_notes]
    patch_out = PatchDetailScraper().scrape_many(patches, out_dir=out_dir)

    # manifest to quickly locate latest bundle
    manifest_path = os.path.join(out_dir, "manifest.json")
    base.save_json({
        "gods_json": os.path.basename(gods_out),
        "items_json": os.path.basename(items_out),
        "patch_index_json": os.path.basename(index_path),
        "patch_notes_json": os.path.basename(patch_out),
    }, manifest_path, include_timestamp=True)

    return {
        "gods": gods_out,
        "items": items_out,
        "patch_notes": patch_out,
        "manifest": manifest_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Smite 2 wiki scraper orchestrator")
    parser.add_argument("--out", dest="out", default=None, help="Output directory under data/")
    parser.add_argument("--limit-patch-notes", dest="limit_patch", type=int, default=None,
                        help="Limit number of patch notes to scrape (newest first if hub is ordered)")
    args = parser.parse_args()

    result = run_all(output_dir=args.out, limit_patch_notes=args.limit_patch)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()


