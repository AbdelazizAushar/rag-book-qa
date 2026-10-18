# Document-Grounded RAG: *Help Your Kids with Computer Science*

A Retrieval-Augmented Generation system that answers questions about **one chapter** of the book *Help Your Kids with Computer Science* (chapter 6, *Programming techniques*). Answers come only from the book, are written in its friendly kids' tone, cite the book's page numbers, and show the page images they came from. Questions the chapter cannot answer are refused.

- **Grounded:** two layers keep it honest: a retrieval-distance gate (no LLM call for clearly off-topic questions) and a strict prompt that makes the model refuse near-topic questions the passages don't answer.
- **Chapter = config:** processing another chapter means adding an entry to `config/chapters.yaml`. No code changes.
- **Inspectable:** every pipeline stage is its own module that writes its own file. A Gradio interface shows the answer, its status, page images, and the retrieved chunks with distances.
- **Tested:** 55 automated tests plus a retrieval evaluation set (see [Tests and evaluation](#tests-and-evaluation)).

Design rationale and trade-offs: [`docs/DECISIONS.md`](docs/DECISIONS.md). How AI tools were used: [`docs/AI_WORKFLOW_REPORT.md`](docs/AI_WORKFLOW_REPORT.md). End-to-end demo: [`notebooks/walkthrough.ipynb`](notebooks/walkthrough.ipynb).

## Setup

Requires Python 3.11 (conda shown; any environment manager works).

```bash
git clone https://github.com/AbdelazizAushar/rag-book-qa.git
cd rag-book-qa

conda create -n ragbook python=3.11 -y
conda activate ragbook
pip install -r requirements.txt
```

**1. API key and model.** Copy the template and fill it in:

```bash
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
```

```
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=<a free chat/instruct model id from openrouter.ai/models>
```

Get a key at <https://openrouter.ai/keys>. The assessment names `meta-llama/llama-3.3-70b-instruct:free`; use it if it is still available to you, otherwise any free instruct model (see `docs/DECISIONS.md`, decision 10). Do **not** use the `openrouter/free` router: it can route a request to a safety-classifier model.

**2. The book.** Download the PDF (link from the assessment) and save it as **`data/file.pdf`**. It is git-ignored and not included in this repository.

> <https://repo.darmajaya.ac.id/5689/1/Help%20Your%20Kids%20with%20Computer%20Science_%20A%20Unique%20Visual%20Step-by-Step%20Guide%20to%20Computers%2C%20Coding%2C%20and%20Communication%20%28%20PDFDrive%20%29.pdf>

The first run downloads the embedding model (`all-MiniLM-L6-v2`, about 90 MB) from Hugging Face.

## Run

**Build the chapter** (extract, clean, chunk, embed, render page images; about a minute):

```bash
python run_pipeline.py --chapter chapter_6
```

**Start the web interface:**

```bash
python gradio_app.py
```

Open <http://127.0.0.1:7860>. Try *"What is an array?"*, then *"Who won the World Cup?"* (refused) and open the **Retrieved Context & Scores** panel.

**Ask from the command line:**

```bash
# bash
PYTHONPATH=src python -m ragbook.generate.answer chapter_6 "What is a syntax error?"
```

```powershell
# PowerShell
$env:PYTHONPATH = "src"
python -m ragbook.generate.answer chapter_6 "What is a syntax error?"
```

**Notebook:** open `notebooks/walkthrough.ipynb` and run all cells. It runs each pipeline stage separately and shows the intermediate results.

## Processing a different chapter

Add an entry to `config/chapters.yaml`. Page numbers are **PDF page numbers** (the book's printed page number plus 2):

```yaml
chapters:
  chapter_6:
    id: 6
    title: Programming techniques
    start_page: 98
    end_page: 117
    page_offset: 2            # PDF page - printed page
    output_dir: data/processed/chapter_06
  chapter_5:
    id: 5
    title: Data
    start_page: 80
    end_page: 97
    page_offset: 2
    output_dir: data/processed/chapter_05
```

```bash
python run_pipeline.py --chapter chapter_5
CHAPTER=chapter_5 python gradio_app.py        # PowerShell: $env:CHAPTER="chapter_5"
```

> **Note on the chapter number.** The assessment says "chapter number #6 (Data)". In this book, chapter 6 is *Programming techniques* and *Data* is chapter 5. Chapter 6 is the primary chapter here, and the question set and calibration are for it. Chapter 5 is configured so that either reading of the brief can be run. `PDF pages = printed pages + 2` was verified against the book's table of contents (see `scripts/` and `docs/DECISIONS.md`, decision 12).

## How a question is answered

```
question
  -> embed (all-MiniLM-L6-v2) -> FAISS search -> top 5 chunks (+ page, heading, distance)
  -> GATE: best distance > 1.1 ?  -> yes: refuse (no LLM call)
  -> prompt = rules + examples + the 5 passages -> LLM (OpenRouter)
  -> model replies "I can't find the answer..." ? -> refuse
  -> answer with cited book pages + images of the pages used
```

Every result has a `status`: `answered`, `refused_by_gate`, `refused_by_model` or `error`. Refusals and errors still return the retrieved chunks so they can be inspected. Temporary API errors (rate limits, timeouts, connection drops, 5xx) are retried up to 3 times; a bad key or model name fails at once with a message saying which `.env` setting to check.

## Tests and evaluation

```bash
pytest -q tests                      # 55 tests; needs the built index for the gate tests
python eval/run_eval.py              # retrieval-only evaluation, no LLM calls
```

- `tests/test_gate.py` (46 tests) is driven by `eval/questions.yaml`: each answerable question must retrieve a chunk from the expected page and pass the gate; each off-topic question must be refused by the gate; and the configured threshold must lie inside the range that separates the two groups.
- `tests/test_answer.py` (9 tests) uses a fake retriever and a fake LLM client: gate refusal returns chunks without calling the LLM, rate-limit retry, bad key not retried, empty replies retried, model refusal detected, page-number mapping, image de-duplication.
- Gate tests are skipped if the index has not been built.
- Answer *quality* is checked manually (see `docs/AI_WORKFLOW_REPORT.md`), not by automated tests.

Current numbers for chapter 6: 60 chunks; all 18 answerable questions retrieve the expected page in the top 5 (17 of 18 in the top 3); answerable best-distances range 0.41 to 0.94, clearly off-topic questions 1.21 to 1.80; gate threshold 1.1.

## Project structure

```
rag-book-qa/
├── README.md
├── requirements.txt
├── .env.example
├── run_pipeline.py            # runs all ingestion stages for one chapter
├── gradio_app.py              # web interface
├── config/chapters.yaml       # a chapter is a config entry
├── src/ragbook/
│   ├── ingest/                # extract.py  clean.py  chunk.py  images.py
│   ├── index/                 # embed.py            (embeddings + FAISS index)
│   ├── retrieve/              # retriever.py  gate.py
│   └── generate/              # answer.py  prompts.py
├── notebooks/walkthrough.ipynb
├── eval/                      # questions.yaml  run_eval.py
├── tests/                     # conftest.py  test_gate.py  test_answer.py
├── scripts/                   # one-off inspection helpers (TOC, images, debug queries)
├── docs/                      # DECISIONS.md  AI_WORKFLOW_REPORT.md
└── data/                      # git-ignored: file.pdf and processed/<chapter>/
```

Output of one chapter (`data/processed/chapter_06/`): `raw_extracted.json`, `cleaned_data.json`, `chunks.jsonl`, `faiss_index.bin`, `metadata.json`, `manifest.json`, `images/`.

## Page numbers

The book prints its own page numbers, which differ from PDF viewer page numbers (printed + 2). Answers cite the **printed** page numbers. The evaluator panel shows both, e.g. "Book page 107 (PDF page 109)". Config and the evaluation set use PDF pages.

## Known limitations

- The book is a **scan with an OCR text layer**. Some chunks contain OCR noise from diagrams and illustrations.
- Images are **whole-page images** (each page is a single picture in the PDF), not individual figures. Up to one image per retrieved page is shown.
- The gate threshold was tuned on a small hand-written question set. Questions close to the chapter's topic but not covered by it pass the gate and rely on the prompt, which is not perfect.
- Retrieval is dense-only. A question like "What do the AND, OR and NOT operators do?" ranks the page with the gate definitions only 4th. Keyword search or a reranker would likely help (see `docs/DECISIONS.md`, decision 7).
- `run_pipeline.py` rebuilds every stage on each run; only the notebook skips stages whose outputs exist.
- The free LLM can be rate limited or busy. Temporary errors are retried, then reported clearly.