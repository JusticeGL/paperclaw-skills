#!/usr/bin/env python3
"""Validate bci-paper-curation selection JSON against a candidate pool."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT_KEYS = {"date", "selected", "not_enough", "notes"}
SELECTED_KEYS = {"id", "two_sentence_summary", "selection_reason"}
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*(?:%| percent)?(?![A-Za-z0-9])")
SENTENCE_RE = re.compile(r"[^。！？.!?]+[。！？.!?]?")
DECIMAL_DOT_RE = re.compile(r"(?<=\d)\.(?=\d)")
ABBREVIATION_RE = re.compile(
    r"\b(?:i\.e|e\.g|etc|vs|fig|eq|dr|mr|mrs|ms|prof|inc|ltd|corp|co|dept|univ|assoc)\.",
    re.IGNORECASE,
)
INITIALISM_RE = re.compile(r"\b(?:[A-Za-z]\.){2,}")
DOT_PLACEHOLDER = "<DOT>"


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def norm_number(token: str) -> str:
    return token.replace(",", "").strip().lower()


def numbers_in(text: str) -> set[str]:
    return {norm_number(match.group(0)) for match in NUMBER_RE.finditer(text or "")}


def mask_non_sentence_dots(text: str) -> str:
    text = DECIMAL_DOT_RE.sub(DOT_PLACEHOLDER, text)
    text = ABBREVIATION_RE.sub(lambda match: match.group(0).replace(".", DOT_PLACEHOLDER), text)
    return INITIALISM_RE.sub(lambda match: mask_initialism_dots(match, text), text)


def mask_initialism_dots(match: re.Match[str], text: str) -> str:
    value = match.group(0)
    next_index = match.end()
    while next_index < len(text) and text[next_index].isspace():
        next_index += 1
    if next_index < len(text) and text[next_index].islower():
        return value.replace(".", DOT_PLACEHOLDER)
    return value[:-1].replace(".", DOT_PLACEHOLDER) + value[-1]


def sentence_count(text: str) -> int:
    parts = [
        part.strip()
        for part in SENTENCE_RE.findall(mask_non_sentence_dots(text or ""))
        if part.strip()
    ]
    return len(parts)


def candidate_lookup(candidates_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates = candidates_doc.get("candidates")
    if not isinstance(candidates, list):
        raise SystemExit("ERROR: candidate document must contain a candidates list")

    lookup: dict[str, dict[str, Any]] = {}
    for idx, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise SystemExit(f"ERROR: candidates[{idx}] must be an object")
        cid = candidate.get("id")
        if not isinstance(cid, str) or not cid:
            raise SystemExit(f"ERROR: candidates[{idx}] has missing or invalid id")
        lookup[cid] = candidate
    return lookup


def validate(args: argparse.Namespace) -> tuple[list[str], list[str]]:
    candidates_doc = load_json(args.candidates)
    selection_doc = load_json(args.selection)
    lookup = candidate_lookup(candidates_doc)
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(selection_doc, dict):
        return ["selection document must be an object"], warnings

    extra_root = set(selection_doc) - ROOT_KEYS
    missing_root = ROOT_KEYS - set(selection_doc)
    if extra_root:
        errors.append(f"selection root has forbidden keys: {sorted(extra_root)}")
    if missing_root:
        errors.append(f"selection root is missing keys: {sorted(missing_root)}")

    cdate = candidates_doc.get("date")
    sdate = selection_doc.get("date")
    if cdate and sdate and cdate != sdate:
        errors.append(f"date mismatch: candidates date {cdate!r}, selection date {sdate!r}")

    selected = selection_doc.get("selected")
    if not isinstance(selected, list):
        errors.append("selected must be a list")
        selected = []

    not_enough = selection_doc.get("not_enough")
    if not isinstance(not_enough, bool):
        errors.append("not_enough must be a boolean")
        not_enough = False

    notes = selection_doc.get("notes")
    if notes is not None and not isinstance(notes, str):
        errors.append("notes must be a string")

    if not_enough:
        if len(selected) >= args.total_min:
            warnings.append(
                f"not_enough=true but selected has {len(selected)} items; consider not_enough=false"
            )
        if not notes:
            errors.append("notes must explain the shortage when not_enough=true")
        if len(selected) > args.total_max:
            errors.append(f"selected count {len(selected)} exceeds total_max={args.total_max}")
    else:
        if not (args.total_min <= len(selected) <= args.total_max):
            errors.append(
                f"selected count {len(selected)} must be between {args.total_min} and {args.total_max}"
            )

    ids: list[str] = []
    for idx, item in enumerate(selected):
        if not isinstance(item, dict):
            errors.append(f"selected[{idx}] must be an object")
            continue

        extra_item = set(item) - SELECTED_KEYS
        missing_item = SELECTED_KEYS - set(item)
        if extra_item:
            errors.append(f"selected[{idx}] has forbidden keys: {sorted(extra_item)}")
        if missing_item:
            errors.append(f"selected[{idx}] is missing keys: {sorted(missing_item)}")

        cid = item.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append(f"selected[{idx}].id must be a non-empty string")
            continue
        ids.append(cid)

        candidate = lookup.get(cid)
        if candidate is None:
            errors.append(f"selected[{idx}].id not found in candidates: {cid}")
            continue

        summary = item.get("two_sentence_summary")
        reason = item.get("selection_reason")
        if not isinstance(summary, str) or not summary.strip():
            errors.append(f"selected[{idx}].two_sentence_summary must be a non-empty string")
            summary = ""
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"selected[{idx}].selection_reason must be a non-empty string")
            reason = ""

        if summary and sentence_count(summary) != 2:
            errors.append(f"selected[{idx}].two_sentence_summary must contain exactly two sentences")
        if reason and sentence_count(reason) != 1:
            errors.append(f"selected[{idx}].selection_reason must contain exactly one sentence")

        abstract_numbers = numbers_in(candidate.get("abstract", ""))
        summary_numbers = numbers_in(summary)
        missing_numbers = sorted(summary_numbers - abstract_numbers)
        if missing_numbers:
            message = (
                f"selected[{idx}] summary contains numbers not found in abstract: {missing_numbers}"
            )
            if args.strict_numbers:
                errors.append(message)
            else:
                warnings.append(message)

    duplicate_ids = sorted({cid for cid in ids if ids.count(cid) > 1})
    if duplicate_ids:
        errors.append(f"duplicate selected ids: {duplicate_ids}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path, help="Path to bci_candidates_{date}.json")
    parser.add_argument("selection", type=Path, help="Path to selection_{date}.json")
    parser.add_argument("--total-min", type=int, default=3)
    parser.add_argument("--total-max", type=int, default=10)
    parser.add_argument("--strict-numbers", action="store_true")
    args = parser.parse_args()

    errors, warnings = validate(args)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK: selection is structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
