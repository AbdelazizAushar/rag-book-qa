
import argparse
import os
import sys

import yaml

sys.path.append(os.path.abspath("src"))

from ragbook.retrieve.gate import GATE_THRESHOLD  
from ragbook.retrieve.retriever import Retriever, TOP_K


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", default="chapter_6")
    ap.add_argument("--config", default="config/chapters.yaml")
    ap.add_argument("--questions", default="eval/questions.yaml")
    ap.add_argument("--top-k", type=int, default=TOP_K)
    ap.add_argument("--current-threshold", type=float, default=GATE_THRESHOLD)
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        info = yaml.safe_load(f)["chapters"][args.chapter]
    with open(args.questions, encoding="utf-8") as f:
        qs = yaml.safe_load(f)

    retriever = Retriever(info["output_dir"])

    ans_scores, un_scores, hits = [], [], 0

    print("\n=== ANSWERABLE (should be answered) ===")
    for item in qs["answerable"]:
        res = retriever.search(item["question"], top_k=args.top_k)
        best = res[0]["score"]
        pages = [c["page"] for c in res]
        hit = any(p in item["expected_pages"] for p in pages)
        hits += hit
        ans_scores.append(best)
        print(f"{'HIT ' if hit else 'MISS'} {best:.3f} pages={pages} "
              f"expected={item['expected_pages']} | {item['question']}")

    print("\n=== UNANSWERABLE (should be refused) ===")
    for item in qs["unanswerable"]:
        res = retriever.search(item["question"], top_k=args.top_k)
        best = res[0]["score"]
        un_scores.append(best)
        layer = item.get("layer", "gate")
        print(f"     {best:.3f} pages={[c['page'] for c in res]} "
              f"[{layer}] | {item['question']}")

    total = len(ans_scores) + len(un_scores)

    def accuracy(t):
        ok = sum(s <= t for s in ans_scores) + sum(s > t for s in un_scores)
        return ok / total

    scores = sorted(ans_scores + un_scores)
    cands = [scores[0] - 0.01] + [(a + b) / 2 for a, b in zip(scores, scores[1:])] + [scores[-1] + 0.01]
    best_acc = max(accuracy(t) for t in cands)
    good = [t for t in cands if accuracy(t) == best_acc]
    suggested = good[len(good) // 2]

    print("\n=== SUMMARY ===")
    print(f"Retrieval hit rate (answerable): {hits}/{len(ans_scores)}")
    print(f"Answerable scores:   min {min(ans_scores):.3f}  max {max(ans_scores):.3f}")
    print(f"Unanswerable scores: min {min(un_scores):.3f}  max {max(un_scores):.3f}")
    print(f"Gate accuracy at configured threshold {args.current_threshold}: "
          f"{accuracy(args.current_threshold):.0%}")
    print(f"Best threshold found: {suggested:.3f}  (accuracy {best_acc:.0%})")
    if max(ans_scores) >= min(un_scores):
        print("NOTE: the two groups overlap, so no threshold separates them perfectly.")
        print("      Near-topic questions are marked layer: model and are left to the LLM prompt.")


if __name__ == "__main__":
    main()