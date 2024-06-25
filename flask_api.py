# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from io import BytesIO
import mammoth
import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import FileReadTool, MDXSearchTool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)
load_dotenv()

openai_api_key = os.getenv("openai_api_key")
os.environ["OPENAI_MODEL_NAME"] = 'gpt-3.5-turbo'
os.environ["OPENAI_API_KEY"] = openai_api_key

with open('./brd-template/brd-template.md', 'r', encoding='utf-8') as file:
    brd_template_content = file.read()
cleaned_brd_template = brd_template_content.replace('\ufeff', '')

def call_crew_kickoff(str_current_datetime):
    mt_tool = FileReadTool(txt=f'./meeting-transcription/meeting-transcript_{str_current_datetime}.md')
    semantic_search_resume = MDXSearchTool(mdx=f'./meeting-transcription/meeting-transcript_{str_current_datetime}.md')

    with open(f'./meeting-transcription/meeting-transcript_{str_current_datetime}.md', 'r', encoding='utf-8') as file:
        transcript_content = file.read()
    cleaned_transcript_content = transcript_content.replace('\ufeff', '')

    business_analyst = Agent(
        role="Business Analyst",
        goal="Translate the meeting transcript into a BRD using the provided template.",
        tools=[mt_tool, semantic_search_resume],
        allow_delegation=False,
        verbose=True,
        backstory="Background in business analysis."
    )

    subject_matter_expert = Agent(
        role="Subject Matter Expert",
        goal="Ensure the BRD reflects technical feasibility.",
        tools=[mt_tool, semantic_search_resume],
        allow_delegation=False,
        verbose=True,
        backstory="Expert in the project's domain."
    )

    analyze_meeting_for_brd = Task(
        description="Analyze the meeting transcript and create a BRD.",
        expected_output="A well-structured BRD.",
        agent=business_analyst,
    )

    sme_technical_review = Task(
        description="Review the BRD for technical accuracy.",
        expected_output="A refined BRD document.",
        agent=subject_matter_expert,
    )

    crew = Crew(
        agents=[business_analyst, subject_matter_expert],
        tasks=[analyze_meeting_for_brd, sme_technical_review],
        verbose=2,
        manager_llm=ChatOpenAI(temperature=0, model="gpt-3.5-turbo"),
        process=Process.hierarchical,
        memory=True,
    )

    result = crew.kickoff(inputs={'datetime': str_current_datetime})

    return result

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    # Validate the file type
    if not file.filename.endswith('.docx'):
        return jsonify({"error": "Invalid file type. Only .docx files are supported."}), 400

    current_datetime = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    filename = f'./meeting-transcription/meeting-transcript_{current_datetime}.md'

    # Use BytesIO to handle the file content properly
    file_content = file.read()
    file_stream = BytesIO(file_content)

    try:
        result = mammoth.convert_to_markdown(file_stream)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(result.value)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    response = call_crew_kickoff(current_datetime)

    output_filename = f"./generated-brd/generated-brd_{current_datetime}.md"
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(response)

    return jsonify({"file_url": output_filename, "brd_content": response})

if __name__ == '__main__':
    if not os.path.exists('./meeting-transcription'):
        os.makedirs('./meeting-transcription')
    if not os.path.exists('./generated-brd'):
        os.makedirs('./generated-brd')
    app.run(debug=True, port=5000)
