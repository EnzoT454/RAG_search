#!/usr/bin/env python3
"""
Automatic scientific paper pipeline for local RAG.

Pipeline:
- Search papers by theme using OpenAlex and arXiv
- Save metadata
- Download legal open-access PDFs when available
- Convert PDFs to Markdown using PyMuPDF
- Convert manually added base-theory PDFs to Markdown
- Save clean .md files for Open WebUI / RAG

Usage:
    python scripts/pipeline.py --themes themes.yaml
    python scripts/pipeline.py --themes themes.yaml --force
    python scripts/pipeline.py --themes themes.yaml --base-theory-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import feedparser
import fitz
import pandas as pd
import requests
import yaml
from dotenv import load_dotenv
from tqdm import tqdm


OPENALEX_BASE = "https://api.openalex.org/works"
ARXIV_BASE = "https://export.arxiv.org/api/query"
UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
PLACEHOLDER_EMAIL = "ton.email@example.com"


@dataclass
class Paper:
    theme: str
    source: str
    title: str
    year: Optional[int]
    authors: str
    doi: Optional[str]
    url: Optional[str]
    pdf_url: Optional[str]
    abstract: Optional[str]
    cited_by_count: Optional[int]
    venue: Optional[str]
    local_pdf: Optional[str] = None
    local_md: Optional[str] = None


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_contact_email(settings: Dict[str, Any]) -> str:
    env_email = os.getenv("RAG_PIPELINE_EMAIL", "").strip()
    if env_email:
        return env_email

    yaml_email = str(settings.get("email", "")).strip()
    if yaml_email and yaml_email != PLACEHOLDER_EMAIL:
        return yaml_email

    return ""


def safe_name(text: str, max_len: int = 90) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len] or "untitled"


def short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def reconstruct_openalex_abstract(inv_index: Optional[Dict[str, List[int]]]) -> Optional[str]:
    if not inv_index:
        return None

    positions = []
    for word, indexes in inv_index.items():
        for idx in indexes:
            positions.append((idx, word))

    if not positions:
        return None

    positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in positions)


def clean_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    doi = doi.replace("https://doi.org/", "").strip()
    return doi or None


def get_openalex_pdf_url(work: Dict[str, Any]) -> Optional[str]:
    best = work.get("best_oa_location") or {}
    if best.get("pdf_url"):
        return best.get("pdf_url")

    primary = work.get("primary_location") or {}
    if primary.get("pdf_url"):
        return primary.get("pdf_url")

    for loc in work.get("locations", []) or []:
        if loc and loc.get("pdf_url"):
            return loc.get("pdf_url")

    return None


def search_openalex(
    theme_name: str,
    query: str,
    max_results: int,
    year_from: int,
    email: str,
) -> List[Paper]:
    params = {
        "search": query,
        "filter": f"from_publication_date:{year_from}-01-01,type:article",
        "sort": "cited_by_count:desc",
        "per-page": max_results,
        "mailto": email,
    }

    r = requests.get(OPENALEX_BASE, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    papers: List[Paper] = []
    for work in data.get("results", []):
        title = work.get("title") or "Untitled"
        authorships = work.get("authorships", []) or []
        authors = ", ".join(
            a.get("author", {}).get("display_name", "")
            for a in authorships[:8]
            if a.get("author", {}).get("display_name")
        )

        primary = work.get("primary_location") or {}
        source = primary.get("source") or {}
        venue = source.get("display_name") if source else None

        papers.append(
            Paper(
                theme=theme_name,
                source="OpenAlex",
                title=title,
                year=work.get("publication_year"),
                authors=authors,
                doi=clean_doi(work.get("doi")),
                url=work.get("id"),
                pdf_url=get_openalex_pdf_url(work),
                abstract=reconstruct_openalex_abstract(work.get("abstract_inverted_index")),
                cited_by_count=work.get("cited_by_count"),
                venue=venue,
            )
        )

    return papers


def search_arxiv(theme_name: str, query: str, max_results: int) -> List[Paper]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    r = requests.get(ARXIV_BASE, params=params, timeout=30)
    r.raise_for_status()

    feed = feedparser.parse(r.text)
    papers: List[Paper] = []

    for entry in feed.entries:
        title = re.sub(r"\s+", " ", entry.get("title", "")).strip()
        abstract = re.sub(r"\s+", " ", entry.get("summary", "")).strip()
        authors = ", ".join(a.name for a in entry.get("authors", []))
        url = entry.get("id")

        pdf_url = None
        for link in entry.get("links", []):
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href")
                break

        if not pdf_url and url:
            pdf_url = url.replace("/abs/", "/pdf/") + ".pdf"

        year = None
        if entry.get("published"):
            try:
                year = int(entry.published[:4])
            except ValueError:
                pass

        papers.append(
            Paper(
                theme=theme_name,
                source="arXiv",
                title=title or "Untitled",
                year=year,
                authors=authors,
                doi=None,
                url=url,
                pdf_url=pdf_url,
                abstract=abstract,
                cited_by_count=None,
                venue="arXiv",
            )
        )

    return papers


def get_unpaywall_pdf(doi: str, email: str) -> Optional[str]:
    if not doi or not email or email == PLACEHOLDER_EMAIL:
        return None

    url = f"{UNPAYWALL_BASE}/{quote_plus(doi)}"
    params = {"email": email}

    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
    except Exception:
        return None

    best = data.get("best_oa_location") or {}
    return best.get("url_for_pdf")


def looks_like_pdf(content: bytes, content_type: str) -> bool:
    return content.startswith(b"%PDF") or "pdf" in content_type.lower()


def download_pdf(pdf_url: str, out_path: Path) -> bool:
    headers = {"User-Agent": "local-rag-paper-pipeline/0.1 (personal academic use)"}

    try:
        with requests.get(
            pdf_url,
            headers=headers,
            stream=True,
            timeout=45,
            allow_redirects=True,
        ) as r:
            r.raise_for_status()

            content_type = r.headers.get("content-type", "")
            first_chunk = next(r.iter_content(chunk_size=8192), b"")
            if not looks_like_pdf(first_chunk, content_type):
                return False

            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("wb") as f:
                f.write(first_chunk)
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        return out_path.exists() and out_path.stat().st_size > 10_000
    except Exception:
        return False


def pdf_to_markdown(pdf_path: Path, md_path: Path, paper: Paper) -> bool:
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return False

    chunks: List[str] = [
        f"# {paper.title}\n",
        "## Metadata\n",
        f"- Theme: {paper.theme}\n",
        f"- Source: {paper.source}\n",
        f"- Year: {paper.year or 'Unknown'}\n",
        f"- Authors: {paper.authors or 'Unknown'}\n",
        f"- DOI: {paper.doi or 'None'}\n",
        f"- URL: {paper.url or 'None'}\n",
        f"- PDF URL: {paper.pdf_url or 'None'}\n",
        f"- Venue: {paper.venue or 'Unknown'}\n\n",
    ]

    if paper.abstract:
        chunks.extend(["## Abstract\n", paper.abstract.strip() + "\n\n"])

    chunks.append("## Full Text Extracted From PDF\n\n")

    for i, page in enumerate(doc, start=1):
        text = page.get_text("text")
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            chunks.extend([f"\n\n## Page {i}\n\n", text, "\n"])

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(chunks), encoding="utf-8")
    return True


def save_metadata_json(path: Path, paper: Paper) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(paper), indent=2, ensure_ascii=False), encoding="utf-8")


def article_theme_dir(output_dir: Path, theme_name: str) -> Path:
    return output_dir / safe_name(theme_name)


def deduplicate_papers(papers: List[Paper]) -> List[Paper]:
    seen = set()
    unique = []

    for paper in papers:
        if paper.doi:
            key = f"doi:{paper.doi.lower()}"
        elif paper.title:
            key = f"title:{safe_name(paper.title, 120)}"
        else:
            key = f"url:{paper.url}"

        if key in seen:
            continue

        seen.add(key)
        unique.append(paper)

    return unique


def load_existing_papers(output_dir: Path) -> List[Paper]:
    json_path = output_dir / "papers.json"
    rows = []

    if json_path.exists():
        try:
            rows = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] Could not read existing papers index: {e}")

    if not rows:
        for metadata_path in output_dir.glob("*/metadata/*.json"):
            try:
                rows.append(json.loads(metadata_path.read_text(encoding="utf-8")))
            except Exception as e:
                print(f"[WARN] Could not read metadata file {metadata_path}: {e}")

    papers: List[Paper] = []
    for row in rows:
        try:
            papers.append(Paper(**row))
        except TypeError as e:
            print(f"[WARN] Skipping invalid existing paper entry: {e}")

    return papers


def theme_has_outputs(output_dir: Path, theme_name: str) -> bool:
    theme_dir = article_theme_dir(output_dir, theme_name)
    metadata_dir = theme_dir / "metadata"
    md_dir = theme_dir / "md"
    pdf_dir = theme_dir / "pdf"

    for directory, pattern in (
        (metadata_dir, "*.json"),
        (md_dir, "*.md"),
        (pdf_dir, "*.pdf"),
    ):
        if directory.exists() and any(directory.glob(pattern)):
            return True

    return False


def write_metadata_only_markdown(md_path: Path, paper: Paper) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_content = f"""# {paper.title}

## Metadata
- Theme: {paper.theme}
- Source: {paper.source}
- Year: {paper.year or "Unknown"}
- Authors: {paper.authors or "Unknown"}
- DOI: {paper.doi or "None"}
- URL: {paper.url or "None"}
- PDF URL: {paper.pdf_url or "None"}
- Venue: {paper.venue or "Unknown"}
- Cited by count: {paper.cited_by_count or "Unknown"}

## Abstract
{paper.abstract or "No abstract found."}

## Notes
PDF was not downloaded or could not be converted. This file contains metadata and abstract only.
"""
    md_path.write_text(md_content, encoding="utf-8")


def process_theme(
    theme: Dict[str, str],
    settings: Dict[str, Any],
    output_dir: Path,
) -> List[Paper]:
    theme_name = theme["name"]
    query = theme["query"]

    max_results = int(settings.get("max_results_per_theme", 20))
    year_from = int(settings.get("year_from", 2018))
    email = settings.get("email", "")
    download_pdfs = bool(settings.get("download_pdfs", True))
    convert_to_md = bool(settings.get("convert_to_md", True))

    print(f"\n=== Theme: {theme_name} ===")
    print(f"Query: {query}")

    papers: List[Paper] = []

    try:
        papers.extend(search_openalex(theme_name, query, max_results, year_from, email))
        time.sleep(1)
    except Exception as e:
        print(f"[WARN] OpenAlex failed for {theme_name}: {e}")

    try:
        papers.extend(search_arxiv(theme_name, query, max_results))
        time.sleep(3)
    except Exception as e:
        print(f"[WARN] arXiv failed for {theme_name}: {e}")

    papers = deduplicate_papers(papers)
    theme_dir = article_theme_dir(output_dir, theme_name)
    pdf_dir = theme_dir / "pdf"
    md_dir = theme_dir / "md"
    metadata_dir = theme_dir / "metadata"

    for paper in tqdm(papers, desc=f"Processing {theme_name}"):
        base = safe_name(f"{paper.year or 'unknown'}_{paper.title}", 100)
        base = f"{base}_{short_hash(paper.title)}"

        metadata_path = metadata_dir / f"{base}.json"
        pdf_path = pdf_dir / f"{base}.pdf"
        md_path = md_dir / f"{base}.md"

        if not paper.pdf_url and paper.doi and email:
            paper.pdf_url = get_unpaywall_pdf(paper.doi, email)
            time.sleep(1)

        if download_pdfs and paper.pdf_url:
            ok = download_pdf(paper.pdf_url, pdf_path)
            if ok:
                paper.local_pdf = str(pdf_path)

                if convert_to_md and pdf_to_markdown(pdf_path, md_path, paper):
                    paper.local_md = str(md_path)

        if convert_to_md and not paper.local_md:
            write_metadata_only_markdown(md_path, paper)
            paper.local_md = str(md_path)

        save_metadata_json(metadata_path, paper)

    return papers


def ensure_base_theory_structure(rag_root: Path, base_theory: List[Dict[str, str]]) -> None:
    base_dir = rag_root / "base_theory"
    clean_dir = rag_root / "clean_notes"

    for topic in base_theory:
        topic_name = safe_name(topic["name"])
        for subdir in ("pdf", "md", "metadata"):
            (base_dir / topic_name / subdir).mkdir(parents=True, exist_ok=True)

    (clean_dir / "fiches_articles").mkdir(parents=True, exist_ok=True)
    (clean_dir / "syntheses_theoriques").mkdir(parents=True, exist_ok=True)


def process_base_theory(
    rag_root: Path,
    base_theory: List[Dict[str, str]],
    force: bool,
) -> List[Paper]:
    papers: List[Paper] = []
    base_dir = rag_root / "base_theory"

    for topic in base_theory:
        topic_name = safe_name(topic["name"])
        topic_dir = base_dir / topic_name
        pdf_dir = topic_dir / "pdf"
        md_dir = topic_dir / "md"
        metadata_dir = topic_dir / "metadata"

        pdf_dir.mkdir(parents=True, exist_ok=True)
        md_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        pdf_paths = sorted(pdf_dir.glob("*.pdf"))
        print(f"\n=== Base theory: {topic_name} ===")
        print(f"PDF directory: {pdf_dir}")

        if not pdf_paths:
            print("No PDF found. Add files manually, then rerun the pipeline.")
            continue

        for pdf_path in tqdm(pdf_paths, desc=f"Converting {topic_name}"):
            base = safe_name(pdf_path.stem, 100)
            md_path = md_dir / f"{base}.md"
            metadata_path = metadata_dir / f"{base}.json"

            if md_path.exists() and not force:
                continue

            paper = Paper(
                theme=topic_name,
                source="Local base theory PDF",
                title=pdf_path.stem.replace("_", " ").replace("-", " ").strip() or pdf_path.stem,
                year=None,
                authors="Unknown",
                doi=None,
                url=str(pdf_path),
                pdf_url=None,
                abstract=None,
                cited_by_count=None,
                venue="Local reference",
                local_pdf=str(pdf_path),
            )

            if pdf_to_markdown(pdf_path, md_path, paper):
                paper.local_md = str(md_path)
                save_metadata_json(metadata_path, paper)
                papers.append(paper)
            else:
                print(f"[WARN] Could not convert local PDF: {pdf_path}")

    return papers


def save_global_outputs(output_dir: Path, papers: List[Paper]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "papers.json"
    csv_path = output_dir / "papers.csv"

    json_path.write_text(
        json.dumps([asdict(p) for p in papers], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    df = pd.DataFrame([asdict(p) for p in papers])
    df.to_csv(csv_path, index=False)

    print(f"\nSaved JSON: {json_path}")
    print(f"Saved CSV:  {csv_path}")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--themes", type=str, default="themes.yaml")
    parser.add_argument("--rag-root", type=str, default="RAG")
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument(
        "--force",
        action="store_true",
        help="reprocess all themes, including themes that already have output files",
    )
    parser.add_argument(
        "--base-theory-only",
        action="store_true",
        help="only convert manually added PDFs in RAG/base_theory; skip online article search",
    )
    args = parser.parse_args()

    config = load_config(Path(args.themes))
    settings = config.get("settings", {})
    settings["email"] = get_contact_email(settings)
    themes = config.get("themes", [])
    base_theory = config.get("base_theory", [])

    rag_root = Path(args.rag_root)
    output_dir = Path(args.output) if args.output else rag_root / "scientific_articles"
    ensure_base_theory_structure(rag_root, base_theory)
    process_base_theory(rag_root, base_theory, args.force)

    if args.base_theory_only:
        print("\nDone.")
        print(f"Base theory Markdown files are in: {rag_root}/base_theory/*/md")
        return

    existing_papers = load_existing_papers(output_dir)
    new_papers: List[Paper] = []
    skipped_themes = []

    for theme in themes:
        theme_name = theme["name"]
        if not args.force and theme_has_outputs(output_dir, theme_name):
            skipped_themes.append(theme_name)
            print(f"\n=== Theme: {theme_name} ===")
            print("Already covered in output; skipping. Use --force to reprocess.")
            continue

        papers = process_theme(theme, settings, output_dir)
        new_papers.extend(papers)

    if args.force:
        all_papers = deduplicate_papers(new_papers + existing_papers)
    else:
        all_papers = deduplicate_papers(existing_papers + new_papers)
    save_global_outputs(output_dir, all_papers)

    print("\nDone.")
    print(f"Processed themes: {len(themes) - len(skipped_themes)}")
    print(f"Skipped existing themes: {len(skipped_themes)}")
    print(f"Next step: upload {output_dir}/*/md and {rag_root}/base_theory/*/md into Open WebUI Knowledge/RAG.")


if __name__ == "__main__":
    main()
