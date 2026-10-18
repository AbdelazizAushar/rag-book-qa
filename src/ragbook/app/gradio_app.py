import os
import sys

import gradio as gr
import yaml

sys.path.append(os.path.abspath("src"))

from ragbook.generate.answer import AnswerGenerator 

CHAPTER = os.environ.get("CHAPTER", "chapter_6")

with open("config/chapters.yaml", "r", encoding="utf-8") as f:
    INFO = yaml.safe_load(f)["chapters"][CHAPTER]

OUTPUT_DIR = INFO["output_dir"]
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")

generator = AnswerGenerator(OUTPUT_DIR, INFO.get("page_offset", 0))

STATUS_LABELS = {
    "answered": "✅ Answered from the book",
    "refused_by_gate": "🚫 Refused: nothing relevant found in the chapter",
    "refused_by_model": "🚫 Refused: the retrieved passages do not answer the question",
    "error": "⚠️ Error",
}


def process_query(question):
    if not question or not question.strip():
        return "Please type a question first.", [], "No question asked.", ""

    result = generator.generate_answer(question.strip())

    chunks_display = ""
    for idx, chunk in enumerate(result["chunks"], 1):
        chunks_display += (
            f"**Chunk {idx} | Book page {chunk['printed_page']} "
            f"(PDF page {chunk['page']}) | {chunk.get('heading', '')} | "
            f"Distance: {chunk['score']:.4f}**\n\n{chunk['text']}\n\n---\n\n"
        )
    if not chunks_display:
        chunks_display = "No chunks retrieved."

    image_files = []
    for img_path in result["images"]:
        full_path = os.path.join(IMAGES_DIR, os.path.basename(img_path))
        if os.path.exists(full_path):
            image_files.append(full_path)

    status = STATUS_LABELS.get(result["status"], result["status"])
    return result["answer"], image_files, chunks_display, status


with gr.Blocks(title=f"Chapter {INFO['id']} RAG Q&A", theme=gr.themes.Soft()) as demo:
    gr.Markdown(f"# 📖 Children's Book Q&A - Chapter {INFO['id']} ({INFO['title']})")

    with gr.Row():
        with gr.Column(scale=2):
            question_input = gr.Textbox(
                label="Ask a question about the chapter:",
                placeholder="e.g., What is an array?",
            )
            submit_btn = gr.Button("Ask", variant="primary")

    status_output = gr.Markdown()

    with gr.Row():
        with gr.Column(scale=2):
            answer_output = gr.Textbox(label="Answer", lines=5, interactive=False)
        with gr.Column(scale=1):
            image_output = gr.Gallery(
                label="Related Images", columns=1, object_fit="contain", height="auto"
            )

    with gr.Accordion("🔍 Retrieved Context & Scores (Evaluator View)", open=False):
        chunks_output = gr.Markdown()

    outputs = [answer_output, image_output, chunks_output, status_output]
    submit_btn.click(fn=process_query, inputs=[question_input], outputs=outputs)
    question_input.submit(fn=process_query, inputs=[question_input], outputs=outputs)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)