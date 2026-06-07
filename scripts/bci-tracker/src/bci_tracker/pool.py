from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from bci_tracker.config import output_dir
from bci_tracker.dates import Window, compute_window
from bci_tracker.dedup import dedup_candidates
from bci_tracker.enrich import enrich_candidates
from bci_tracker.schema import Candidate
from bci_tracker.scoring import score_candidates
from bci_tracker.sources import ArxivSource, BioRxivSource, MedRxivSource, PubMedSource, SemanticScholarSource


SOURCE_FACTORIES = {
    "pubmed": PubMedSource,
    "biorxiv": BioRxivSource,
    "medrxiv": MedRxivSource,
    "arxiv": ArxivSource,
    "semantic_scholar": SemanticScholarSource,
}


def enabled_sources(cfg: Dict[str, Any]) -> list[str]:
    return [name for name, enabled in cfg.get("sources", {}).items() if enabled and name in SOURCE_FACTORIES]


def build_pool(cfg: Dict[str, Any], window: Window | None = None) -> Dict[str, Any]:
    window = window or compute_window(cfg["timezone"], int(cfg["window_days"]))
    all_candidates: list[Candidate] = []
    statuses: dict[str, dict[str, Any]] = {}

    for name in enabled_sources(cfg):
        source = SOURCE_FACTORIES[name]()
        try:
            candidates = source.fetch(window, cfg)
            all_candidates.extend(candidates)
            statuses[name] = {"status": "ok", "hit": len(candidates), "kept": len(candidates)}
        except Exception as exc:  # Keep the whole run alive if one source fails.
            statuses[name] = {"status": "failed", "reason": str(exc), "hit": 0, "kept": 0}

    deduped = dedup_candidates(enrich_candidates(all_candidates))
    scored = score_candidates(deduped, cfg)

    return {
        "date": window.end.isoformat(),
        "window": window.to_dict(),
        "sources": statuses,
        "candidates": [candidate.to_dict() for candidate in scored],
    }


def candidate_path(cfg: Dict[str, Any], date_text: str) -> Path:
    return output_dir(cfg) / cfg["output"]["candidates_filename"].format(date=date_text)


def write_pool(pool: Dict[str, Any], cfg: Dict[str, Any]) -> Path:
    out_dir = output_dir(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = candidate_path(cfg, pool["date"])
    with path.open("w", encoding="utf-8") as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def dry_run_summary(pool: Dict[str, Any]) -> str:
    lines = [f"date={pool['date']} window={pool['window']['start']}..{pool['window']['end']}"]
    for name, status in pool.get("sources", {}).items():
        if status.get("status") == "ok":
            lines.append(f"{name}: hit={status.get('hit', 0)} kept={status.get('kept', 0)}")
        else:
            lines.append(f"{name}: {status.get('status')} reason={status.get('reason', '')}")
    lines.append(f"deduped_candidates={len(pool.get('candidates', []))}")
    return "\n".join(lines)
