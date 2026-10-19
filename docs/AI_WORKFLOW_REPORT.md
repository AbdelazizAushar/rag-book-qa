# AI-Assisted Development Report

## Tools

Development was done with Claude as a pair-programming assistant in a chat/agent workspace. The assistant wrote plans, code and documentation drafts; the author (Abdelaziz) ran everything on his own machine, made the design choices, and decided what to keep. The assistant had no access to the author's machine: the author executed every command and pasted back results, and files were exchanged by upload.

## Workflow

Work followed one step per message: the assistant proposed one step, the author ran it and reported the result (output, error, or file), and the next step depended on that result. This kept every step verifiable and meant bugs were found within a step of being introduced.

1. **Plan.** The assistant read the brief and produced a seven-page plan (PDF) covering the pipeline, repo layout, deliverables and evaluation criteria. The author challenged the first repo structure ("are you sure this is the structure I need?") and asked for a leaner one.
2. **Environment and repo.** Conda environment, GitHub repo, early commits.
3. **Ingestion.** Extraction, cleaning, chunking, embedding, indexing, image rendering, each as a separate module, plus `run_pipeline.py`.
4. **Retrieval and gate.** Retriever, distance gate, then calibration against a written question set.
5. **Generation.** Prompt with few-shot examples, OpenRouter client with retries, tests with fakes.
6. **Interface.** Gradio app with an inspection panel.
7. **Evaluation and tests.** `eval/questions.yaml`, `run_eval.py`, pytest.
8. **Deliverables.** Walkthrough notebook, README, decisions, this report.

## Context given to the AI

- The full text of the assessment brief (`AI-task.md`) and its evaluation criteria.
- The book's title and PDF; the author's chosen chapter and, later, the table of contents pasted as text.
- The author's own code files when asking for review (the eleven source files at the first review).
- Real outputs: tracebacks, pytest results, evaluation printouts, chunk outlines, Gradio answers with the retrieved chunks, image reports.
- Standing instructions: conda not venv; one step per message; do not download things for me; keep it lean.

## What was delegated, and what was not

**Delegated to the AI (then reviewed):** first drafts of every module, the plan, the test code, the evaluation harness, the notebook, and drafts of these documents.

**Decided by the author:**
- Which chapter (chapter 6, *Programming techniques*) and the correction of the page range using the table of contents.
- Using a newer free model than the brief's Llama 3.3 70B.
- Dropping the reranker when it could not be downloaded or shown to help.
- Dropping extra image work and over-engineering ("why so much work, isn't there a better way?", "why are we doing this, aren't we done?").
- Branches, commits and merges: the author's git history, including merging the `feat/compliance-fixes` branch into `main`.

## How the output was reviewed and validated

- **Reading the data, not the code.** The chunk outline (page, heading, first words) was printed and read after every change to cleaning or chunking. That is how the chunk bugs below were found.
- **Running it.** Every module was run by the author. Several errors only showed up that way.
- **Automated checks.** An evaluation set of 29 questions (18 answerable with expected pages, 11 unanswerable) drives retrieval and gate tests. 55 pytest tests pass (46 gate/retrieval, 9 answer-path).
- **Calibration instead of guessing.** The gate threshold was chosen from measured distances, and a test asserts it stays inside the valid range.
- **Manual answer review.** Answers for a set of questions were read in the Gradio app together with the retrieved chunks: AND/OR/NOT must define the operators, "best language for beginners" must be refused by the model, an off-topic question ("Who won the World Cup?") must be refused by the gate with the chunks visible
- **Reading the assistant's claims critically.** Several assistant claims were tested and turned out wrong or incomplete (below).

## Mistakes found in AI output (and how)

| # | Problem | How it was found | Fix |
|---|---------|------------------|-----|
| 1 | The assistant guessed a page range (96 to 116) that included the end of *Data*. | The chunk outline showed the wrong chapter's headings; the author pasted the table of contents. | Range set to 98 to 117 from the TOC; `page_offset` added. |
| 2 | Chunking bugs: heading assigned off by one, short blocks dropped, sentence fragments treated as headings. | Reading the chunk outline. | Rewrote `chunk.py` to be lossless with stricter heading rules. |
| 3 | Running headers and OCR junk inside chunk text. | Same outline. | New `clean.py` with repeated-block detection and spaced-letter stripping. |
| 4 | The dependency list contained `rank-bm25` that nothing used. | Reviewing the final dependencies. | Removed. |
| 5 | An evaluation check was too lenient (the AND/OR/NOT answer looked fine while the right page was not retrieved at top 3). | Looking at the retrieved chunks next to the answer. | Evaluation checks the *expected page*; `TOP_K` raised to 5. |
| 6 | The gate threshold was loose, and the evaluation's "current threshold" was only a default argument, so editing the app's value changed nothing in the report. | The author edited the threshold and saw identical output. | One shared constant; calibration test. |
| 7 | `TOP_K` was still hard-coded to 3 in one test after the change. | pytest failure. | Test reads the shared constant. |
| 8 | The `openrouter/free` router returned "User Safety: safe". | Running the answer module. | Pin the model with `OPENROUTER_MODEL`. |
| 9 | A first-run import error (`ModuleNotFoundError: ragbook`). | Running a module from the wrong place. | Documented `PYTHONPATH=src` and the `-m` form; scripts add `src` to the path. |
| 10 | The assistant proposed a cross-encoder reranker, then BM25 hybrid, which would have added complexity with no measured gain; the download stalled. | The author asked whether it was needed and tried the download. | Evaluated, documented as not adopted (decision 7). |
| 11 | Extra image rework was proposed when the real constraint is that the source is a scan. | The author stopped it as unnecessary. | Kept whole-page images; documented. |

## Limits of this workflow

- The assistant's code ran on the author's machine only; the assistant tested what it could in its own sandbox (for example the answer-path tests with fakes), not the full pipeline on the real PDF.
- Evaluation questions were written by the author and the assistant together, so they may share blind spots with the system they test.
- The prompt's few-shot examples include one paraphrased context, to be verified against the book text.
- Answer quality is a manual judgment, not a measured score.
