import gradio as gr
import requests

def process_file(input_file):
    if input_file:
        with open(input_file, "rb") as f:
            files = {'file': (input_file, f)}
            response = requests.post("https://fozan-talat-llm-powered-it-documentation-specialist.hf.space/upload", files=files)
            output = response.json()
            return output['file_url'], output['brd_content']

with gr.Blocks() as demo:
    with gr.Row():
        file_input = gr.File(label="Upload the meeting transcript (.docx file supported only)", file_types=[".docx"], file_count="single")
        download_btn = gr.File(label="Download Processed File in Markdown", file_count="single")
    with gr.Row():
        markdown_output = gr.Markdown()

    file_input.change(process_file, inputs=file_input, outputs=[download_btn, markdown_output])

demo.launch()

#hey
