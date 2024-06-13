import warnings
warnings.filterwarnings('ignore')

from crewai import Agent, Task, Crew, Process
from crewai_tools import (
    FileReadTool,
    MDXSearchTool
)
from datetime import datetime

import os
import gradio as gr
import mammoth
import markdown
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.getenv("openai_api_key")
os.environ["OPENAI_MODEL_NAME"] = 'gpt-3.5-turbo'
os.environ["OPENAI_API_KEY"] = openai_api_key

with open('./brd-template/brd-template.md', 'r', encoding='utf-8') as file:
    brd_template_content = file.read()
# Remove BOM character if it exists
cleaned_brd_template = brd_template_content.replace('\ufeff', '')

#print(cleaned_brd_template)

def call_crew_kickoff(str_current_datetime):
    # Instantiate tools
    mt_tool = FileReadTool(txt='./meeting-transcription/meeting-transcript_' + str_current_datetime + '.md')

    semantic_search_resume = MDXSearchTool(mdx='./meeting-transcription/meeting-transcript_' + str_current_datetime + '.md')

    with open('./meeting-transcription/meeting-transcript_' + str_current_datetime + '.md', 'r', encoding='utf-8') as file:
        transcript_content = file.read()
    # Remove BOM character if it exists
    cleaned_transcript_content = transcript_content.replace('\ufeff', '')

    business_analyst = Agent(
        role="Business Analyst",
        goal="Effectively translate the meeting transcript and discussions into a well-structured BRD using the provided template, "
             "ensuring it accurately captures project requirements and stakeholder needs as per the template attached.",
        tools=[mt_tool, semantic_search_resume],
        allow_delegation=False,
        verbose=True,
        backstory=(
            "You come from a background in business analysis, with experience in similar IT projects or a strong understanding "
            "of the organization's needs. Your skillset includes: You can effectively guide discussions and ensure everyone is "
            "on the same page, even in a technical environment. You possess the ability to translate complex information into "
            "clear and concise written documents. You can analyze information effectively, identify key requirements, and prioritize "
            "them based on importance. You possess a strong understanding of the provided BRD template and its purpose."
        )
    )

    subject_matter_expert = Agent(
        role="Subject Matter Expert",
        goal="Ensure the BRD accurately reflects the project's technical feasibility and translates technical discussions into "
             "actionable requirements for a successful IT project. Additionally, propose a clear and concise project name that "
             "captures the essence of the initiative.",
        tools=[mt_tool, semantic_search_resume],
        allow_delegation=False,
        verbose=True,
        backstory=(
            "You possess in-depth knowledge and experience specific to the project's domain (data analytics and integrations). While "
            "not directly involved in the initial meeting discussions, your expertise is crucial for refining the BRD's technical aspects "
            "and ensuring stakeholder needs are addressed."
        )
    )

    analyze_meeting_for_brd = Task(
        description=(
            "###" + cleaned_transcript_content + "###\n"
            "Given above is the meeting transcript.\n"
            "1. Pay close attention to sections outlining functionalities, technical requirements, and references to specific technologies.\n"
            "2. Analyze the technical aspects discussed in the transcript (e.g., data processing infrastructure updates, cloud migration) and "
                "assess their feasibility. If needed, suggest alternative solutions or approaches to achieve the desired functionalities.\n"
            "3. Based on the transcript and your understanding of data analytics, translate the technical needs into clear and concise "
                "requirements within the BRD. This could include: \n"
            "Specific data points or sources needed for analysis.\n"
            "Functionality requirements for data ingestion, processing, and visualization.\n"
            "Integration requirements with existing systems.\n"
            "4. Review the stakeholder discussions in the transcript (e.g., IT team's need for robust backend support, marketing team's need "
                "for advanced analytics features). Ensure the BRD reflects these needs by outlining functionalities that address them.\n"
            "5. Familiarize yourself with the template's structure, sections, and required information for each section.\n"
            "6. Identify key points relevant to the BRD, focusing on project background, goals, functionalities, success criteria, risks, and "
                "stakeholder needs as per template ###\n" + cleaned_brd_template + "\n###.\n"
            "7. Fill in the appropriate sections of the BRD template using the information extracted from the transcript.\n"
            "8. Ensure consistency and clarity throughout the document. Check for completeness and address any missing information. Consider "
                "using the transcript to clarify details or resolve potential inconsistencies.\n"
        ),
        expected_output="A well-structured BRD, completed using the provided template, that accurately reflects the information captured in the "
            "meeting transcript. This includes clearly defined requirements, identified stakeholder needs, success criteria, and a preliminary "
            "understanding of project scope and risks.",
        agent=business_analyst,
    )

    sme_technical_review = Task(
        description=(
            "1. Pay close attention to sections outlining functionalities, technical requirements, and any references to specific technologies.\n"
            "2. Analyze whether the documented requirements align with technical constraints and capabilities. Identify any areas where the BRD "
                "might propose functionalities that are technically unrealistic or infeasible and add those in the BRD.\n"
            "3. If the BRD uses technical terms that might be unclear to non-technical stakeholders, propose alternative wording or explanations "
                "and update the BRD accordingly.\n"
            "4. Based on your expertise, anticipate and mention potential technical hurdles in the BRD that could arise during development based "
                "on the proposed requirements. Add mitigation strategies or alternative approaches in the BRD if necessary.\n"
            "5. Based on the project goals and functionalities discussed in the transcript, suggest a clear and concise name for the project. This "
                "name should accurately represent the initiative and be easily understood by all stakeholders."
        ),
        expected_output=("Comprehensive and refined BRD document including a proposed project name that captures the essence of the initiative."
        ),
        agent=subject_matter_expert,
    )

    crew = Crew(
       agents=[business_analyst, subject_matter_expert],
       tasks=[analyze_meeting_for_brd, sme_technical_review],
       verbose=2,
       manager_llm=ChatOpenAI(temperature=0, model="gpt-3.5-turbo"),  # Mandatory for hierarchical process
       process=Process.hierarchical,  # Specifies the hierarchical management approach
       memory=True,  # Enable memory usage for enhanced task execution
    )

    result = crew.kickoff(inputs={'datetime': str_current_datetime})

    return result


def process_file(input_file):
    if input_file is not None:
        current_datetime = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        print("Current date & time : ", current_datetime)
        
        str_current_datetime = str(current_datetime)
        filename = 'meeting-transcription/meeting-transcript_' + str_current_datetime + '.md'
        
        with open(input_file, "rb") as docx_file:
            result = mammoth.convert_to_markdown(docx_file)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result.value)
                f.close()

        response = call_crew_kickoff(str_current_datetime)

        output_filename = "generated-brd/generated-brd_" + str_current_datetime + ".md"
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(response)
            f.close()
        

        return output_filename, response


with gr.Blocks() as demo:
    with gr.Row():
        file_input = gr.File(label="Upload the meeting transcript (.docx file supported only)", file_types=[".docx"], file_count="single")
        download_btn = gr.File(label="Download Processed File in Markdown", file_count="single")
    with gr.Row():
        markdown_output = gr.Markdown()

    file_input.change(process_file, inputs=file_input, outputs=[download_btn, markdown_output])

demo.launch()



