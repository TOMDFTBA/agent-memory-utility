# Stage 4: Three-Way Page-Retrieval Comparison

[Chinese version](report.md)

The visual path uses VisRAG-Ret. Native PDF text and uncorrected Tesseract OCR use the same MiniCPM-Embedding model.

| Query | Designated page | Visual rank | Native-text rank | OCR rank |
|---|---|---:|---:|---:|
| Find the diagram comparing the TextRAG pipeline on the left with the VisRAG pipeline on the right. | v1-p4 | 1 | 2 | 3 |
| Find the bar chart comparing TextRAG and VisRAG accuracy using MiniCPM-V and GPT-4o generators. | v1-p2 | 1 | 1 | 2 |
| Find the example comparing Japan and Spain population, with sports news interest at 35 percent. | v2-p2 | 1 | 1 | 1 |
| Which page defines position-weighted mean pooling for the retrieval embedding? | v1-p4 | 1 | 1 | 1 |
| Find the equations for per-image evidence recording and answer reasoning in EVisRAG. | v2-p3 | 1 | 1 | 1 |

The designated page ranked first for 5/5 visual queries, 4/5 native-text queries, and 3/5 OCR queries.

## Evaluation protocol

Text is divided into 512 content-token chunks with 64-token overlap, after which model special tokens are added. Original token IDs are encoded without truncation. A page receives the maximum cosine similarity across its chunks. The native-text and OCR paths use the same model, queries, and aggregation rule.

OCR is fixed to English, PSM 3, and OEM 1. Recognized text, TSV coordinates/confidences, and logs are preserved locally without manual correction. Images use a longest side of 1,400 pixels so the comparison does not also vary resolution.

## Boundaries

This is a descriptive result over eight fixed pages and five hand-written queries, not an exhaustive relevance judgment set. Native PDF text is not a perfect OCR gold standard, and the two text paths can differ in reading order; their differences are not a character-error-rate measurement. Max-chunk aggregation gives pages with more chunks more opportunities to match. Visual and text paths use different encoders, so differences cannot be attributed solely to modality.

No generator was run. The experiment does not establish answer correctness or long-term memory effectiveness. Per-query rankings and scores are available in [`results.json`](results.json); source page images, OCR derivatives, and vector files remain excluded pending redistribution review.
