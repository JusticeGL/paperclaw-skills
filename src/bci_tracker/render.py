from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from bci_tracker.config import output_dir
from bci_tracker.schema import Candidate


class RenderError(ValueError):
    pass


def load_json(path: str | Path) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise RenderError(f"JSON root must be an object: {path}")
    return data


def selection_path(cfg: Dict[str, Any], date_text: str) -> Path:
    name = cfg["output"].get("selection_filename", "selection_{date}.json").format(date=date_text)
    return output_dir(cfg) / name


def final_path(cfg: Dict[str, Any], date_text: str) -> Path:
    return output_dir(cfg) / cfg["output"]["final_filename"].format(date=date_text)


def candidate_lookup(pool: Dict[str, Any]) -> Dict[str, Candidate]:
    candidates = {}
    for row in pool.get("candidates", []):
        candidate = Candidate.from_dict(row)
        candidates[candidate.id] = candidate
    return candidates


def validate_selection(selection: Dict[str, Any], pool: Dict[str, Any], cfg: Dict[str, Any]) -> List[tuple[Candidate, Dict[str, str]]]:
    selected = selection.get("selected", [])
    if not isinstance(selected, list):
        raise RenderError("selection.selected must be a list")
    not_enough = bool(selection.get("not_enough", False))
    limits = cfg["selection"]
    total_min = int(limits["total_min"])
    total_max = int(limits["total_max"])
    if not_enough:
        if len(selected) > total_max:
            raise RenderError(f"selection contains {len(selected)} papers; maximum is {total_max}")
    elif not (total_min <= len(selected) <= total_max):
        raise RenderError(f"selection contains {len(selected)} papers; expected {total_min}-{total_max}")

    lookup = candidate_lookup(pool)
    result: list[tuple[Candidate, Dict[str, str]]] = []
    seen_ids: set[str] = set()
    for idx, item in enumerate(selected):
        if not isinstance(item, dict):
            raise RenderError(f"selected[{idx}] must be an object")
        cid = item.get("id")
        if not cid:
            raise RenderError(f"selected[{idx}] missing id")
        if cid in seen_ids:
            raise RenderError(f"duplicate selected id: {cid}")
        seen_ids.add(cid)
        candidate = lookup.get(cid)
        if candidate is None:
            raise RenderError(f"selected id not found in candidate pool: {cid}")
        result.append(
            (
                candidate,
                {
                    "two_sentence_summary": str(item.get("two_sentence_summary") or "").strip(),
                    "selection_reason": str(item.get("selection_reason") or "").strip(),
                },
            )
        )
    return result


def placeholder(value: str | None) -> str:
    return value if value else "（原数据未提供）"


def affiliation(candidate: Candidate) -> str:
    if candidate.corresponding_institution:
        return candidate.corresponding_institution
    if candidate.affiliations:
        return "；".join(candidate.affiliations)
    return "（原数据未提供）"


def doi_suffix(candidate: Candidate) -> str:
    return f"（DOI: {candidate.doi}）" if candidate.doi else ""


def source_summary(pool: Dict[str, Any], selected: list[tuple[Candidate, Dict[str, str]]]) -> str:
    selected_counts = Counter(candidate.source for candidate, _ in selected)
    parts = []
    for name, status in pool.get("sources", {}).items():
        kept = status.get("kept", 0)
        hit = status.get("hit", 0)
        chosen = selected_counts.get(name, 0)
        state = status.get("status")
        if state == "ok":
            parts.append(f"{name} {hit}/{kept}/入选{chosen}")
        else:
            parts.append(f"{name} {state}: {status.get('reason', '')}")
    return "；".join(parts) if parts else "无"


def render_markdown(pool: Dict[str, Any], selection: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    selected = validate_selection(selection, pool, cfg)
    window = pool.get("window", {})
    lines = [
        "# BCI论文追踪原始摘要",
        f"业务日期：{pool.get('date')}",
        f"时区：{window.get('tz', cfg.get('timezone', 'Asia/Shanghai'))}",
        f"时间范围：{window.get('start')} 至 {window.get('end')}",
        "检索来源：PubMed / bioRxiv / medRxiv / arXiv（+ 可选 Semantic Scholar）",
        "采集方式：API 优先，浏览器兜底",
        "",
    ]

    if selected:
        for idx, (candidate, prose) in enumerate(selected, start=1):
            lines.extend(
                [
                    f"## 入选论文{idx}",
                    f"- 标题：{placeholder(candidate.title)}",
                    f"- 作者：{placeholder('；'.join(candidate.authors))}",
                    f"- 所属机构/工作室/实验室：{affiliation(candidate)}",
                    f"- 来源平台：{candidate.source} / {placeholder(candidate.venue)}",
                    f"- 发布时间：{placeholder(candidate.published_date)}",
                    f"- 关键词：{placeholder('；'.join(candidate.matched_keywords))}",
                    f"- 链接（含DOI）：{placeholder(candidate.url)}{doi_suffix(candidate)}",
                    f"- 两句话总结：{placeholder(prose['two_sentence_summary'])}",
                    f"- 入选理由：{placeholder(prose['selection_reason'])}",
                    "",
                ]
            )
    else:
        lines.extend(["## 入选论文", "（无）", ""])

    lines.extend(
        [
            "---",
            "检索说明：",
            f"- 各来源命中/保留/入选：{source_summary(pool, selected)}",
            "- 浏览器兜底条目：无",
        ]
    )
    if selection.get("not_enough") or not selected:
        note = selection.get("notes") or "当前时间窗口内未发现足够高质量且适合纳入摘要的相关论文。"
        lines.extend(["", "# 若不足：", f"- {note}"])
    return "\n".join(lines).rstrip() + "\n"


def render_to_file(candidate_file: str | Path, selection_file: str | Path, cfg: Dict[str, Any], output: str | Path | None = None) -> Path:
    pool = load_json(candidate_file)
    selection = load_json(selection_file)
    markdown = render_markdown(pool, selection, cfg)
    path = Path(output) if output else final_path(cfg, pool["date"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path
