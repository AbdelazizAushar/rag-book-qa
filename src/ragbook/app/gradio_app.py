import sys
import os
import gradio as gr

sys.path.append(os.path.abspath('src'))

from ragbook.generate.answer import AnswerGenerator

generator = AnswerGenerator()

def process_query(question):
    result = generator.generate_answer(question)
    
    answer_text = result.get("answer", "Error generating answer.")
    
    chunks_display = ""
    for idx, chunk in enumerate(result.get("chunks", [])):
        chunks_display += f"**Chunk {idx + 1} (Page {chunk['page']}, Score: {chunk.get('score', 0):.4f})**\n{chunk['text']}\n\n"
        
    if not chunks_display:
        chunks_display = "No relevant chunks retrieved."

    image_files = []
    base_dir = "data/processed/chapter_06/images"
    for img_path in result.get("images", []):
        filename = os.path.basename(img_path)
        full_path = os.path.join(base_dir, filename)
        if os.path.exists(full_path):
            image_files.append(full_path)

    return answer_text, image_files, chunks_display

with gr.Blocks(title="Chapter 6 RAG Q&A", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 📖 Children's Book Q&A - Chapter 6 (Data)")
    
    with gr.Row():
        with gr.Column(scale=2):
            question_input = gr.Textbox(label="Ask a question about the chapter:", placeholder="e.g., What is an array?")
            submit_btn = gr.Button("Ask", variant="primary")
            
    with gr.Row():
        with gr.Column(scale=2):
            answer_output = gr.Textbox(label="Answer", lines=5, interactive=False)
        with gr.Column(scale=1):
            image_output = gr.Gallery(label="Related Images", columns=1, object_fit="contain", height="auto")
            
    with gr.Accordion("🔍 Retrieved Context & Scores (Evaluator View)", open=False):
        chunks_output = gr.Markdown()
        
    submit_btn.click(
        fn=process_query,
        inputs=[question_input],
        outputs=[answer_output, image_output, chunks_output]
    )
    # Allow pressing Enter to submit
    question_input.submit(
        fn=process_query,
        inputs=[question_input],
        outputs=[answer_output, image_output, chunks_output]
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)