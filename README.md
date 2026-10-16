# Educational RAG Pipeline: "Help Your Kids with Computer Science"

A modular Retrieval-Augmented Generation (RAG) application designed to extract, index, and intelligently answer questions based on specific book chapters. Built with strict hallucination controls, a relevance gate, and a targeted conversational persona.

## 🏗️ Architecture & Tech Stack

This project implements an end-to-end RAG pipeline prioritizing local processing for data ingestion and high-tier LLM routing for generation:

* **Document Processing:** `PyMuPDF` for raw text and embedded image extraction.
* **Embeddings:** Local CPU-based processing using `sentence-transformers` (`all-MiniLM-L6-v2`).
* **Vector Store:** `faiss-cpu` utilizing L2 distance for fast, scalable similarity search.
* **LLM Generation:** `OpenRouter` API for strict, persona-driven answer formulation.
* **User Interface:** `Gradio` for interactive Q&A and evaluator inspection.

## 🚀 Key Features

* **Multi-Modal Linking:** Extracts images from the source PDF and explicitly links them to adjacent text chunks via page-level metadata.
* **Relevance Gating:** Implements an L2 distance threshold to block out-of-domain questions before they reach the LLM, triggering a fixed refusal phrase and saving API costs.
* **Persona Engineering:** Prompts are heavily engineered to adapt technical computer science concepts (e.g., arrays, compilers) into child-friendly language (ages 7-12) while strictly citing source pages.
* **Automated Evaluation:** Includes an offline evaluation script (`eval/run_eval.py`) to benchmark retrieval hit rates and response accuracy across answerable, unanswerable, and adversarial question sets.

## 📂 Project Structure

```text
rag-book-qa/
├── config/
│   └── chapters.yaml         # Chapter bounds and metadata
├── data/
│   ├── book.pdf              # Raw source document
│   └── processed/            # Generated chunks, FAISS index, and images
├── eval/
│   ├── questions.yaml        # Benchmark question dataset
│   └── run_eval.py           # Evaluation execution script
├── src/ragbook/
│   ├── app/                  # Gradio web interface
│   ├── generate/             # Prompt templates and OpenRouter client
│   ├── index/                # FAISS indexing and embedding logic
│   ├── ingest/               # PyMuPDF extraction, cleaning, and chunking
│   └── retrieve/             # Similarity search and relevance gating
└── .env                      # API keys (OpenRouter)
```

## ⚙️ Quick Start

**1. Environment Setup**
```bash
conda create -n rag-env python=3.10 -y
conda activate rag-env
conda install pytorch cpuonly -c pytorch -y
pip install sentence-transformers faiss-cpu pymupdf pyyaml gradio openai python-dotenv
```

**2. Configure API Key**
Create a `.env` file in the root directory:
```env
OPENROUTER_API_KEY=your_openrouter_key_here
```

**3. Run the Pipeline**
Ensure you run these from the project root so Python detects the `src` directory:

```powershell
# Phase 1 & 2: Ingest, Chunk, and Index
python src/ragbook/ingest/clean.py
python src/ragbook/ingest/chunk.py
python src/ragbook/index/embed.py
python src/ragbook/ingest/images.py

# Phase 3 & 4: Launch the User Interface
$env:PYTHONPATH="src"
python src/ragbook/app/gradio_app.py

# Phase 5: Run the Evaluation Suite
$env:PYTHONPATH="src"
python eval/run_eval.py