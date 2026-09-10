"""Frozen page/query specification and deterministic Poppler preparation."""

import hashlib
import subprocess
from pathlib import Path

from longmem.experiment_io import write_json


PAGE_GROUPS = (
    ("v1", "VisRAG-v1-arXiv-2410.10594.pdf", (1, 2, 4, 5, 6)),
    ("v2", "VisRAG-v2-arXiv-2510.09733.pdf", (1, 2, 3)),
)

QUERIES = (
    {"query_id": "q1", "query": "Find the diagram comparing the TextRAG pipeline on the left with the VisRAG pipeline on the right.", "target_page_id": "v1-p4"},
    {"query_id": "q2", "query": "Find the bar chart comparing TextRAG and VisRAG accuracy using MiniCPM-V and GPT-4o generators.", "target_page_id": "v1-p2"},
    {"query_id": "q3", "query": "Find the example comparing Japan and Spain population, with sports news interest at 35 percent.", "target_page_id": "v2-p2"},
    {"query_id": "q4", "query": "Which page defines position-weighted mean pooling for the retrieval embedding?", "target_page_id": "v1-p4"},
    {"query_id": "q5", "query": "Find the equations for per-image evidence recording and answer reasoning in EVisRAG.", "target_page_id": "v2-p3"},
)


def prepare_pages(*, paper_directory: Path, output: Path) -> tuple[list[dict], list[dict]]:
    examples = output / "examples"
    examples.mkdir()
    pages = []
    for version, filename, page_numbers in PAGE_GROUPS:
        source = paper_directory / filename
        pdf_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
        for page_number in page_numbers:
            page_id = f"{version}-p{page_number}"
            prefix = examples / page_id
            subprocess.run(
                ["pdftoppm", "-f", str(page_number), "-l", str(page_number), "-scale-to", "1400",
                 "-singlefile", "-png", str(source), str(prefix)],
                check=True,
            )
            subprocess.run(
                ["pdftotext", "-f", str(page_number), "-l", str(page_number), "-layout",
                 str(source), str(prefix.with_suffix(".txt"))],
                check=True,
            )
            pages.append({
                "page_id": page_id,
                "source_pdf": filename,
                "page_number": page_number,
                "source_pdf_sha256": pdf_sha256,
                "image_path": f"examples/{page_id}.png",
                "native_text_path": f"examples/{page_id}.txt",
            })
    queries = [dict(query) for query in QUERIES]
    write_json(
        examples / "manifest.json",
        {
            "pages": pages,
            "queries": queries,
            "selection": "Hand-selected exploratory queries and one designated evidence page each; not exhaustive relevance labels.",
        },
    )
    return pages, queries
