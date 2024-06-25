from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from datetime import datetime
import mammoth
import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import FileReadTool, MDXSearchTool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

app = FastAPI()
load_dotenv()

openai_api_key = os.getenv("openai_api_key")
os.environ["OPENAI_MODEL_NAME"] = 'gpt-3.5-turbo'
os.environ["OPENAI_API_KEY"] = openai_api_key

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    current_datetime = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    filename = f'meeting-transcription/meeting-transcript_{current_datetime}.md'

    # Save file and convert to markdown
    content = await file.read()
    with open(f"{file.filename}", "wb") as docx_file:
        docx_file.write(content)
    with open(file.filename, "rb") as docx_file:
        result = mammoth.convert_to_markdown(docx_file)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(result.value)

    response = call_crew_kickoff(current_datetime)

    output_filename = f"generated-brd/generated-brd_{current_datetime}.md"
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(response)

    return JSONResponse(content={"file_url": output_filename, "brd_content": response})

def call_crew_kickoff(str_current_datetime):
    # Setup CrewAI agents and tasks
    mt_tool = FileReadTool(txt=f'./meeting-transcription/meeting-transcript_{str_current_datetime}.md')
    semantic_search_resume = MDXSearchTool(mdx=f'./meeting-transcription/meeting-transcript_{str_current_datetime}.md')

    with open(f'./meeting-transcription/meeting-transcript_{str_current_datetime}.md', 'r', encoding='utf-8') as file:
        transcript_content = file.read()
    cleaned_transcript_content = transcript_content.replace('\ufeff', '')

    with open('./brd-template/brd-template.md', 'r', encoding='utf-8') as file:
        brd_template_content = file.read()
    cleaned_brd_template = brd_template_content.replace('\ufeff', '')

    business_analyst = Agent(
        role="Business Analyst",
        goal="Effectively translate the meeting transcript and discussions into a well-structured BRD...",
        tools=[mt_tool, semantic_search_resume],
        allow_delegation=False,
        verbose=True,
        backstory="You come from a background in business analysis..."
    )

    subject_matter_expert = Agent(
        role="Subject Matter Expert",
        goal="Ensure the BRD accurately reflects the project's technical feasibility...",
        tools=[mt_tool, semantic_search_resume],
        allow_delegation=False,
        verbose=True,
        backstory="You possess in-depth knowledge and experience specific to the project's domain..."
    )

    analyze_meeting_for_brd = Task(
        description="Analyze the meeting transcript and create a BRD...",
        expected_output="A well-structured BRD...",
        agent=business_analyst,
    )

    sme_technical_review = Task(
        description="Review the BRD for technical accuracy...",
        expected_output="Comprehensive and refined BRD document...",
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
