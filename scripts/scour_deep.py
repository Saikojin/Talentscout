import argparse
import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.auto_scour import main

def parse_deep_args(args=None):
    """Parse CLI options for deep scouring (page N results, skipping page 1)."""
    parser = argparse.ArgumentParser(
        description="TalentScout Deep Scour — Scrapes beyond page 1 to discover deeper postings and page capacity"
    )
    parser.add_argument(
        "--page",
        type=int,
        default=2,
        help="Target page number to scour (default: 2, ignoring page 1)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="Max number of pages to scour per site from the target page (default: 1)"
    )
    parser.add_argument(
        "--detect-pages-only",
        action="store_true",
        help="Probe sites to survey available page capacity and bot blocks without extracting/scoring JDs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate scour and scoring without saving to DB or updating jobs_to_review.md"
    )

    parsed = parser.parse_args(args)
    # Deep scour always ignores page 1
    parsed.skip_page_one = True
    return parsed

def convert_to_auto_scour_args(deep_args) -> list:
    """Translate deep scour options into CLI flags for auto_scour."""
    argv = [
        "--page", str(deep_args.page),
        "--max-pages", str(deep_args.max_pages),
        "--skip-page-one"
    ]
    if deep_args.detect_pages_only:
        argv.append("--detect-pages-only")
    if deep_args.dry_run:
        argv.append("--dry-run")
    return argv

if __name__ == "__main__":
    deep_opts = parse_deep_args()
    scour_argv = convert_to_auto_scour_args(deep_opts)
    print(f"[*] Launching Deep Scour on Page {deep_opts.page} (skipping page 1)...")
    asyncio.run(main(scour_argv))
