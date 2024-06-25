# frontend/app.py
import gradio as gr
import requests

def process_file(input_file):
    if input_file:
        files = {'file': input_file}
        try:
            response = requests.post("http://127.0.0.1:5000/upload", files=files)
            response.raise_for_status()  # Raise an error for bad status codes
            output = response.json()
            return output['file_url'], output['brd_content']
        except requests.RequestException as e:
            print(f"Error: {e}")
            return "Error processing the file. Check the backend server.", ""

with gr.Blocks() as demo:
    with gr.Row():
        file_input = gr.File(label="Upload the meeting transcript (.docx file supported only)", file_types=[".docx"], file_count="single")
        download_btn = gr.File(label="Download Processed File in Markdown", file_count="single")
    with gr.Row():
        markdown_output = gr.Markdown()

    file_input.change(process_file, inputs=file_input, outputs=[download_btn, markdown_output])

demo.launch()
