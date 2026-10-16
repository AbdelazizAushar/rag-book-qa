from ragbook.generate.answer import AnswerGenerator
import yaml
import sys
import os

sys.path.append(os.path.abspath('src'))


def run_evaluation(yaml_path):
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    generator = AnswerGenerator()
    total = len(data['questions'])
    passed = 0
    retrieval_hits = 0

    print(f"Starting evaluation on {total} questions...\n")

    for q in data['questions']:
        print(f"Q: {q['question']}")
        result = generator.generate_answer(q['question'])

        hit = False
        if not q['expected_source_pages']:
            hit = True
        else:
            for page in q['expected_source_pages']:
                if page in result['sources']:
                    hit = True
                    break
        if hit:
            retrieval_hits += 1

        is_pass = False
        if "unanswerable" in q['type'] or q['type'] == 'adversarial':
            if "I can't find the answer to that" in result['answer']:
                is_pass = True
        else:
            concepts_found = sum(
                1 for c in q['expected_concepts'] if c.lower() in result['answer'].lower())
            if concepts_found / len(q['expected_concepts']) >= 0.5:
                is_pass = True

        if is_pass:
            passed += 1

        print(
            f"Result: {'PASS' if is_pass else 'FAIL'} | Hit: {'YES' if hit else 'NO'}")
        print("-" * 40)

    print(f"\nEvaluation Complete!")
    print(f"Overall Pass Rate: {passed}/{total} ({(passed/total)*100:.1f}%)")
    print(
        f"Retrieval Hit Rate: {retrieval_hits}/{total} ({(retrieval_hits/total)*100:.1f}%)")


if __name__ == "__main__":
    run_evaluation("eval/questions.yaml")
