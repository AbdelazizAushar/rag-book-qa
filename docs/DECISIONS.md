# Technical Decisions

Each decision lists the choice, the alternatives considered, and the trade-off. Numbers are from chapter 6 (*Programming techniques*, 60 chunks, 29 evaluation questions).

## 1. PDF extraction: PyMuPDF

**Chosen:** PyMuPDF (`fitz`) with block-level extraction.
**Alternatives:** pdfplumber, pypdf, OCR from scratch (Tesseract).
**Why:** The book is a scan: every page is one 2008x2400 image with an OCR text layer already embedded. PyMuPDF reads that layer quickly, returns text blocks with types and positions, and also renders pages to images. Running OCR again would be slower and add nothing.
**Trade-off:** We inherit the OCR's mistakes (stray characters from diagrams, spaced-out letters). These are handled in cleaning (decision 2), not eliminated.

## 2. Cleaning is a separate, rule-based stage

**Chosen:** Keep text blocks only; drop blocks with OCR junk characters; strip runs of spaced single letters; strip a leading page number; drop page-number-only blocks; drop short blocks that repeat on many pages (running headers). Removed header patterns are printed so they can be checked.
**Alternatives:** Feed raw text to the chunker; use an LLM to clean text.
**Why:** Raw text put header junk inside chunks, which hurt both retrieval and answers. An LLM cleaner is slow, costs calls and can rewrite the book's content. Rules are deterministic and reproducible per chapter.
**Trade-off:** Rules are tuned to this book's layout. A very different book would need its thresholds revisited.

## 3. Chunking: section-aware, about 150 words, lossless

**Chosen:** Split on headings detected by simple rules (1 to 8 words, starts with a capital, does not end in punctuation or a function word), then pack paragraphs up to 150 words; tiny page tails (under 30 words) merge into the previous chunk. Headings stay in the chunk text. Each chunk stores page and heading.
**Alternatives:** Fixed-size character windows with overlap; one chunk per page; semantic chunking.
**Why:** The chapter is built from short, self-contained topics. Section-aware chunks keep a definition with its heading and map cleanly to one page for citations. Fixed windows cut definitions in half.
**Trade-off:** Heading detection is heuristic. Early versions had an off-by-one in heading assignment, dropped short blocks, and treated sentence fragments as headings; all were found by reading the chunk outline and fixed. The detector can still mislabel a heading on rare pages. This only affects the label, because the text is never discarded.

## 4. Embeddings: local `all-MiniLM-L6-v2`

**Chosen:** sentence-transformers `all-MiniLM-L6-v2`, normalised vectors.
**Alternatives:** Hosted embedding APIs; larger local models (bge, e5).
**Why:** Runs on CPU, about 90 MB, no key or rate limit, so indexing and the tests are reproducible offline once the model is downloaded. The chapter is small (60 chunks), so a small model is enough: 18 of 18 answerable questions retrieve the right page at top 5.
**Trade-off:** Lower ceiling than larger models on hard paraphrases (see decision 7).

## 5. Vector index: FAISS `IndexFlatL2`

**Chosen:** Exact L2 search over normalised vectors.
**Alternatives:** Approximate indexes (IVF, HNSW); a vector database (Chroma, Qdrant).
**Why:** With 60 vectors, exact search is instant and has no tuning. A database adds a service for no benefit. Distances are easy to reason about: lower is closer, and the gate uses them directly.
**Trade-off:** Flat search does not scale to very large collections. For many chapters, each chapter has its own index, so each one stays small.

## 6. Retrieval depth: TOP_K = 5

**Chosen:** 5 chunks, defined once in `retriever.py` and imported by the answer code, the evaluation and the tests.
**Why:** With top 3, "What do the AND, OR and NOT operators do?" missed PDF page 107 (17 of 18). Top 5 retrieves it (18 of 18). A single shared constant came after the evaluation script and the tests silently disagreed with the app about k.
**Trade-off:** More context per prompt (about 5 x 150 words) and slightly more room for the model to wander. The prompt rules limit that.

## 7. Reranker and hybrid (BM25) search: evaluated, not adopted

**Considered:** A cross-encoder reranker (retrieve 10 to 20, rescore with a cross-encoder, keep 5) and BM25 + dense hybrid search with rank fusion.
**Why it was attractive:** The one retrieval weakness we saw is the AND/OR/NOT question, which ranks the right page 4th: the dense model matches generally on "logic" while keywords such as "AND", "OR", "NOT" point to the right page.
**Why not adopted:** (a) Retrieval is already 18 of 18 at top 5, so the measured benefit is zero on our set. (b) The cross-encoder download repeatedly stalled on the available connection, so it could not be tested properly; adopting something we cannot evaluate would be worse than not adopting it. (c) It adds a second model, latency and another failure point. A `rank-bm25` dependency was added during exploration and later removed as unused.
**Fallback:** Raising `TOP_K` is a zero-cost change. If the question set grows and misses appear, a reranker is the first thing to add.

## 8. Two-layer refusal (unsupported questions)

**Layer 1: retrieval-distance gate.** If the best chunk's L2 distance is above `GATE_THRESHOLD = 1.1`, the question is refused without calling the LLM. It is cheap, deterministic and works when the LLM is down.
**Layer 2: prompt.** Near-topic questions that pass the gate but are not answered by the passages ("Who invented Python?", "What is the best programming language for beginners?") are refused by the model with one fixed sentence, which the code detects (`refused_by_model`).
**Why two layers:** Distance alone cannot separate "near the topic but not in the book" from "in the book". A prompt alone costs a call for every off-topic question and trusts the model completely.
**Calibration:** Instead of guessing, `eval/questions.yaml` has 18 answerable and 11 unanswerable questions. Answerable best-distances: 0.41 to 0.94. Gate-layer unanswerable best-distances: 1.21 to 1.80. Valid range for the threshold: (0.944, 1.209). 1.1 sits inside it with margin both sides. `test_gate.py` asserts that the configured threshold lies inside the range measured from the data, so changing the question set or the index forces a re-check instead of silently breaking.
**Early mistake:** the first threshold was loose, and the evaluation script's "current threshold" was only a CLI default, not the value in the app. After the constant was shared, the numbers agree.
**Trade-off:** 29 questions is a small calibration set. The margin is real but it is not a proof for all questions; this is listed under limitations.

## 9. Prompt design

**Chosen:** A system prompt with seven rules (use only the passages, say the fixed refusal sentence if the answer is not there, keep the book's friendly tone for kids, short answers, no invented facts, etc.) and four few-shot examples, including one refusal. Passages are labelled with the printed book page so the model can cite them.
**Alternatives:** Zero-shot prompt; fine-tuning.
**Why:** Few-shot examples were the most reliable way to get both the tone and the refusal sentence from a free model. Temperature 0.1 and a 400-token cap keep answers consistent and short.
**Trade-off:** Free models vary. Tone and refusal were checked by hand on a set of questions, not by an automated metric (see the AI workflow report).

## 10. LLM: a pinned free OpenRouter model instead of the brief's Llama 3.3 70B

**Chosen:** The model id comes from the `OPENROUTER_MODEL` environment variable. The assessment suggests `meta-llama/llama-3.3-70b-instruct:free`; the author considers it outdated and used a newer free model instead.
**Why not the `openrouter/free` router:** it picks a model per request, and one request was routed to a safety-classifier model that replied "User Safety: safe" instead of answering. Pinning one model makes the behaviour repeatable.
**Why an env var:** free models are withdrawn and renamed often. A grader can set any free instruct model without touching code.
**Trade-off:** Results depend on the model a grader configures. The prompt and gate are model-independent as far as possible, since the gate runs before any model is called.

## 11. Reliability: bounded retries, clear errors

**Chosen:** Timeout 45 s; up to 3 attempts; retry only on connection errors, timeouts, empty responses and HTTP 408, 409, 429 and 5xx. Never retry 400, 401, 403 or 404 (bad key, bad model name). Missing `.env` settings raise an error that names the setting. Retrieval failures return `status: "error"` instead of crashing the UI.
**Why:** Free endpoints rate limit often. Retrying a wrong key just wastes time and hides the mistake.
**Trade-off:** No backoff cache or fallback model. If the pinned model is down for long, the user sees a clear error, not a different answer.

## 12. Page numbering: printed page for users, PDF page internally

The PDF page is the printed page plus 2 (checked against the table of contents). Config and evaluation data use PDF pages because those are what a PDF viewer and PyMuPDF use. Answers and citations show the printed page, because that is what a reader holding the book sees. The evaluator panel shows both. A `page_offset` per chapter keeps the conversion explicit instead of hard-coded.

## 13. Images: whole-page renders

**What the source gives us:** Each page of this scan is a single image, so there are no separate embedded figures to extract.
**Chosen:** Render the pages that supplied the retrieved chunks and show them in a gallery, de-duplicated.
**Alternatives:** Detect and crop figures with layout analysis or a vision model; filter pages by caption.
**Why:** Cropping figures from a scan needs a vision/layout model, which is a large addition. A page image is accurate and shows the real diagram next to the explanation.
**Trade-off:** A shown page may contain more than the figure that matters, and may include unrelated content. Not every retrieved page is relevant to the question. A cap on shown images and figure cropping are the natural next steps.

## 14. One chapter = one config entry

Chapter ranges, page offset and output folder live in `config/chapters.yaml`; the pipeline, app, tests and notebook read from it. Each chapter writes to its own folder and index. No chapter-specific code exists.
**Chapter ambiguity:** The brief says "#6 (Data)". In this PDF, chapter 6 is *Programming techniques* and *Data* is chapter 5. The author chose chapter 6 (the number), and configured chapter 5 as well. The two readings could not be reconciled from the brief alone; this should be confirmed with the assessor.
**Early mistake:** The first page range (96 to 116) mixed the end of *Data* with *Programming techniques*; the table of contents gave the correct 98 to 117.
**Not implemented:** Skip-if-unchanged for `run_pipeline.py`. The notebook skips stages whose outputs already exist; the script rebuilds everything (about a minute).

## 15. Testing and evaluation

- **Gate and retrieval tests** are generated from `eval/questions.yaml` (46 tests): expected page retrieved, gate passes, off-topic refused, threshold in the valid range.
- **Answer-path tests** (9) use a fake retriever and fake LLM client: no network, no key.
- **Retrieval evaluation** (`eval/run_eval.py`) prints HIT/MISS per question, the distances and a suggested threshold.
- **Not automated:** The correctness and tone of generated answers. They need a judge (a human or an LLM), and a free model as judge would add noise. They were reviewed manually.

## 16. Interface: Gradio

Gradio gives a working QA interface in one file, with a gallery for images and an accordion for inspection. The accordion shows chunks with book page, PDF page, heading and distance, so a reviewer can see why a question was answered or refused. A web framework with a separate frontend was not needed.

## Known limitations

- OCR noise remains in some chunks (decision 1, 2).
- Images are whole pages, not figures (decision 13).
- Calibration uses 29 questions; the gate margin is measured, not guaranteed (decision 8).
- Dense-only retrieval; one known weak ranking (decision 7).
- The LLM is a free model and can be slow, rate limited or changed by the provider (decisions 10, 11).
- The brief's chapter reference is ambiguous (decision 14).
