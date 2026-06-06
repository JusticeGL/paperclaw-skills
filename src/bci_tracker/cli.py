from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bci_tracker.config import ConfigError, load_config
from bci_tracker.dates import compute_window, parse_date
from bci_tracker.pool import build_pool, candidate_path, dry_run_summary, write_pool
from bci_tracker.render import RenderError, render_to_file, selection_path


def cmd_fetch(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    today = parse_date(args.date) if args.date else None
    window = compute_window(cfg["timezone"], int(cfg["window_days"]), today=today)
    pool = build_pool(cfg, window)
    if args.dry_run:
        print(dry_run_summary(pool))
        return 0
    path = write_pool(pool, cfg)
    print(f"wrote {path}")
    print(dry_run_summary(pool))
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    date_text = args.date
    if not date_text:
        date_text = compute_window(cfg["timezone"], int(cfg["window_days"])).end.isoformat()
    candidate_file = Path(args.candidates) if args.candidates else candidate_path(cfg, date_text)
    sel_file = Path(args.selection) if args.selection else selection_path(cfg, date_text)
    output = Path(args.output) if args.output else None
    path = render_to_file(candidate_file, sel_file, cfg, output)
    print(f"wrote {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bci-tracker")
    parser.add_argument("--config", default="config.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="Fetch and write candidate pool")
    fetch.add_argument("--date", help="Business date YYYY-MM-DD; defaults to today in configured timezone")
    fetch.add_argument("--dry-run", action="store_true", help="Print source counts without writing files")
    fetch.set_defaults(func=cmd_fetch)

    render = sub.add_parser("render", help="Render final Markdown from candidates and selection")
    render.add_argument("--date", help="Business date YYYY-MM-DD; defaults to today in configured timezone")
    render.add_argument("--candidates", help="Path to bci_candidates_{date}.json")
    render.add_argument("--selection", help="Path to selection_{date}.json")
    render.add_argument("--output", help="Output Markdown path")
    render.set_defaults(func=cmd_render)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, RenderError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
