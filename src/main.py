#!/usr/bin/env python3
"""Generate a daily, deduplicated literature brief from Crossref metadata."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_FILE = ROOT / "data" / "seen_papers.json"
BRIEFS_DIR = ROOT / "briefs"
CROSSREF_API = "https://api.crossref.org"


@dataclass(frozen=True)
class Source:
    name: str
    tier: str
    route: str


@dataclass(frozen=True)
class Paper:
    key: str
    title: str
    authors: str
    doi: str
    url: str
    published: str
    source: str
    tier: str
    score: int
    labels: tuple[str, ...]
    matches: tuple[str, ...]


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def normalized_text(value: str) -> str:
    plain = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(plain)).strip()


def first_date(record: dict[str, Any]) -> str:
    for field in ("published-online", "published-print", "published", "issued", "created"):
        parts = record.get(field, {}).get("date-parts", [[]])
        if parts and parts[0]:
            values = parts[0]
            try:
                year = int(values[0])
                month = int(values[1]) if len(values) > 1 else 1
                day = int(values[2]) if len(values) > 2 else 1
                return date(year, month, day).isoformat()
            except (TypeError, ValueError):
                continue
    return "Unknown"


def author_line(record: dict[str, Any]) -> str:
    authors = []
    for author in record.get("author", []):
        name = " ".join(part for part in (author.get("given"), author.get("family")) if part)
        authors.append(name or author.get("name", ""))
    if not authors:
        return "Authors unavailable"
    return ", ".join(authors[:6]) + (" et al." if len(authors) > 6 else "")


def fetch_crossref(route: str, since: date, mailto: str | None) -> list[dict[str, Any]]:
    params = {
        "filter": f"from-index-date:{since.isoformat()}",
        "sort": "indexed",
        "order": "desc",
        "rows": "100",
        "select": "DOI,title,author,URL,published-online,published-print,published,issued,created,abstract,type",
    }
    if mailto:
        params["mailto"] = mailto
    request = Request(
        f"{CROSSREF_API}{route}?{urlencode(params)}",
        headers={"User-Agent": "quant-marketing-literature-brief/0.1 (mailto: set CROSSREF_MAILTO)"},
    )
    try:
        with urlopen(request, timeout=45) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"WARNING: Crossref request failed for {route}: {error}", file=sys.stderr)
        return []
    return payload.get("message", {}).get("items", [])


def classify(title: str, abstract: str, topics: dict[str, list[str]]) -> tuple[int, tuple[str, ...], tuple[str, ...]]:
    haystack = f"{title}\n{abstract}".lower()
    labels: list[str] = []
    matches: list[str] = []
    score = 0
    for label, phrases in topics.items():
        topic_matches = [phrase for phrase in phrases if phrase.lower() in haystack]
        if topic_matches:
            labels.append(label)
            matches.extend(topic_matches[:3])
            score += 12 + min(len(topic_matches), 4) * 6
    return score, tuple(labels), tuple(dict.fromkeys(matches))


def make_paper(record: dict[str, Any], source: Source, topics: dict[str, list[str]]) -> Paper | None:
    if record.get("type") not in {None, "journal-article", "report", "posted-content", "proceedings-article"}:
        return None
    doi = str(record.get("DOI", "")).strip().lower()
    title_values = record.get("title") or []
    title = normalized_text(title_values[0] if title_values else "")
    if not doi or not title:
        return None
    abstract = normalized_text(record.get("abstract", ""))
    score, labels, matches = classify(title, abstract, topics)
    return Paper(
        key=f"doi:{doi}",
        title=title,
        authors=author_line(record),
        doi=doi,
        url=record.get("URL") or f"https://doi.org/{doi}",
        published=first_date(record),
        source=source.name,
        tier=source.tier,
        score=score,
        labels=labels,
        matches=matches,
    )


def escape_markdown(value: str) -> str:
    return value.replace("[", "\\[").replace("]", "\\]")


def brief_path(run_date: date) -> Path:
    return BRIEFS_DIR / f"{run_date:%Y}" / f"{run_date:%m}" / f"{run_date.isoformat()}.md"


def render_brief(run_date: date, papers: list[Paper], scanned: int, since: date) -> str:
    header = [
        f"# Quant Marketing Literature Brief — {run_date.isoformat()}",
        "",
        f"> Scanned {scanned} new Crossref records indexed since {since.isoformat()}; selected {len(papers)} topical papers.",
        "> Inclusion is a keyword-based first-pass screen. Open the DOI link to verify the source metadata and paper version.",
        "",
    ]
    if not papers:
        return "\n".join(header + ["No new papers met the current topical threshold today.", ""])

    lines = header
    for index, paper in enumerate(papers, start=1):
        labels = " · ".join(paper.labels)
        matched = ", ".join(f"`{item}`" for item in paper.matches)
        lines.extend(
            [
                f"## {index}. [{escape_markdown(paper.title)}]({paper.url})",
                "",
                f"- **Source:** {paper.source} · {paper.tier} · metadata date {paper.published}",
                f"- **Authors:** {paper.authors}",
                f"- **Relevance:** {paper.score}/100 · {labels}",
                f"- **Matched terms:** {matched}",
                f"- **DOI:** [{paper.doi}](https://doi.org/{paper.doi})",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print results without changing files.")
    parser.add_argument("--lookback-days", type=int, default=7, help="Days of Crossref index history to scan.")
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now(UTC).date(), help="Brief date (YYYY-MM-DD).")
    args = parser.parse_args()
    if args.lookback_days < 1:
        parser.error("--lookback-days must be at least 1")

    sources_config = read_json(CONFIG_DIR / "sources.json")
    topics_config = read_json(CONFIG_DIR / "topics.json")
    since = args.date - timedelta(days=args.lookback_days)
    mailto = os.getenv("CROSSREF_MAILTO")
    sources: list[Source] = []
    for item in sources_config["journals"]:
        sources.append(Source(item["name"], item["tier"], f"/journals/{item['issn']}/works"))
    for item in sources_config["working_paper_prefixes"]:
        sources.append(Source(item["name"], item["tier"], f"/prefixes/{item['prefix']}/works"))

    all_records: list[tuple[dict[str, Any], Source]] = []
    for source in sources:
        records = fetch_crossref(source.route, since, mailto)
        print(f"{source.name}: fetched {len(records)} records")
        all_records.extend((record, source) for record in records)

    state = read_json(DATA_FILE)
    seen: dict[str, Any] = state.setdefault("papers", {})
    candidates: dict[str, Paper] = {}
    for record, source in all_records:
        paper = make_paper(record, source, topics_config["topics"])
        if not paper or paper.key in seen or paper.score < topics_config["minimum_score"]:
            continue
        existing = candidates.get(paper.key)
        if existing is None or paper.score > existing.score:
            candidates[paper.key] = paper

    selected = sorted(candidates.values(), key=lambda item: (-item.score, item.title.lower()))[: topics_config["daily_limit"]]
    output = render_brief(args.date, selected, len(all_records), since)
    print("\n" + output)
    if args.dry_run:
        return 0

    destination = brief_path(args.date)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(output, encoding="utf-8", newline="\n")
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    for paper in selected:
        seen[paper.key] = {
            "title": paper.title,
            "source": paper.source,
            "first_seen_at": timestamp,
            "brief_date": args.date.isoformat(),
        }
    write_json(DATA_FILE, state)
    print(f"\nWrote {destination.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

