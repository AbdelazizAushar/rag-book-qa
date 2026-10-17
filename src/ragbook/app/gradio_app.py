import os
import sys

import gradio as gr
import yaml

sys.path.append(os.path.abspath("src"))

from ragbook.generate.answer import AnswerGenerator  # noqa: E402

CHAPTER = os.environ.get("CHAPTER", "chapter_6")

with open("config/chapters.yaml", "r", encoding="utf-8") as f:
    info = yaml.safe_load(f)["chapters"][CHAPTER]

OUTPUT_DIR = info["output_dir"]
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")

# Built once at startup so the model and index are not reloaded per question.
generator = AnswerGenerator(OUTPUT_DIR)


def process_query(question):
    if not question or not question.strip():
        return "Please type a question first.", [], "No question asked."

    try:
        result = generator.generate_answer(question.strip())
    except Exception as e:
        return f"Something went wrong: {e}", [], "No chunks retrieved."

    answer_text = result.get("answer", "Error generating answer.")

    chunks_display = ""
    for idx, chunk in enumerate(result.get("chunks", [])):
        chunks_display += (
            f"**Chunk {idx + 1} | Page {chunk['page']} | "
            f"{chunk.get('heading', '')} | Score: {chunk.get('score', 0):.4f}**\n\n"
            f"{chunk['text']}\n\n---\n\n"
        )
    if not chunks_display:
        chunks_display = "No relevant chunks retrieved."

    image_files = []
    for img_path in result.get("images", []):
        full_path = os.path.join(IMAGES_DIR, os.path.basename(img_path))
        if os.path.exists(full_path):
            image_files.append(full_path)

    return answer_text, image_files, chunks_display


with gr.Blocks(title=f"Chapter {info['id']} RAG Q&A", theme=gr.themes.Soft()) as demo:
    gr.Markdown(f"# 📖 Children's Book Q&A - Chapter {info['id']} ({info['title']})")

    with gr.Row():
        with gr.Column(scale=2):
            question_input = gr.Textbox(
                label="Ask a question about the chapter:",
                placeholder="e.g., What is an array?",
            )
            submit_btn = gr.Button("Ask", variant="primary")

    with gr.Row():
        with gr.Column(scale=2):
            answer_output = gr.Textbox(label="Answer", lines=5, interactive=False)
        with gr.Column(scale=1):
            image_output = gr.Gallery(
                label="Related Images", columns=1, object_fit="contain", height="auto"
            )

    with gr.Accordion("🔍 Retrieved Context & Scores (Evaluator View)", open=False):
        chunks_output = gr.Markdown()

    outputs = [answer_output, image_output, chunks_output]
    submit_btn.click(fn=process_query, inputs=[question_input], outputs=outputs)
    question_input.submit(fn=process_query, inputs=[question_input], outputs=outputs)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)