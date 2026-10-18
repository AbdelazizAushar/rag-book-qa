"""Gate tests driven by eval/questions.yaml.

Needs the chapter index: run `python run_pipeline.py --chapter chapter_6` first.
Questions marked `layer: model` are near-topic on purpose: the gate lets them
through and the LLM prompt is responsible for refusing them.
"""
import os

import pytest
import yaml

from ragbook.retrieve.gate import GATE_THRESHOLD, check_relevance
from ragbook.retrieve.retriever import TOP_K, Retriever

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHAPTER = os.environ.get("CHAPTER", "chapter_6")

with open(os.path.join(ROOT, "config", "chapters.yaml"), encoding="utf-8") as f:
    INFO = yaml.safe_load(f)["chapters"][CHAPTER]
with open(os.path.join(ROOT, "eval", "questions.yaml"), encoding="utf-8") as f:
    QS = yaml.safe_load(f)

INDEX_DIR = os.path.join(ROOT, INFO["output_dir"])
GATE_LAYER = [q for q in QS["unanswerable"] if q.get("layer", "gate") == "gate"]

pytestmark = pytest.mark.skipif(
    not os.path.exists(os.path.join(INDEX_DIR, "faiss_index.bin")),
    reason="index not built; run run_pipeline.py first",
)


def _qid(item):
    return item["question"]


@pytest.fixture(scope="module")
def retriever():
    return Retriever(INDEX_DIR)


def _search(retriever, question):
    return retriever.search(question, top_k=TOP_K)


@pytest.mark.parametrize("item", QS["answerable"], ids=_qid)
def test_answerable_retrieves_expected_page(retriever, item):
    pages = [c["page"] for c in _search(retriever, item["question"])]
    assert any(p in item["expected_pages"] for p in pages)


@pytest.mark.parametrize("item", QS["answerable"], ids=_qid)
def test_answerable_passes_gate(retriever, item):
    assert check_relevance(_search(retriever, item["question"]))


@pytest.mark.parametrize("item", GATE_LAYER, ids=_qid)
def test_offtopic_is_refused_by_gate(retriever, item):
    assert not check_relevance(_search(retriever, item["question"]))


def test_threshold_is_inside_valid_range(retriever):
    answerable = [_search(retriever, q["question"])[0]["score"] for q in QS["answerable"]]
    offtopic = [_search(retriever, q["question"])[0]["score"] for q in GATE_LAYER]
    low, high = max(answerable), min(offtopic)
    print(f"\nvalid threshold range: ({low:.3f}, {high:.3f})  "
          f"midpoint {(low + high) / 2:.3f}  configured {GATE_THRESHOLD}")
    assert low < high, "answerable and off-topic scores overlap"
    assert low < GATE_THRESHOLD < high, "configured threshold is outside the valid range"