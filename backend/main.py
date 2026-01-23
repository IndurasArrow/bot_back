from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import sys
import os

# Add the parent directory to sys.path to allow imports from 'backend' if running from root,
# or ensure current dir is in path if running from inside backend.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

try:
    from backend.data import inventory_df
    from backend.utils import df_to_context
    from backend.llm import chat_llm
except ImportError:
    # Fallback for when running directly inside the backend folder
    from data import inventory_df
    from utils import df_to_context
    from llm import chat_llm

from fastapi.middleware.cors import CORSMiddleware
import json
import re

app = FastAPI(
    title="PVR Chat Assistant",
    description="Query your procurement data",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str   

class ReportRequest(BaseModel):
    chat_history: list[str]

@app.post("/chat")
def chat(request: ChatRequest):
    print(f"User Message: {request.message}")
    
    inventory_context = df_to_context(inventory_df, "Procurement/Maintenance Data")

    prompt = f"""
    Context Data:
    {inventory_context}

    User Question: {request.message}

    Instructions:
    1. Answer based ONLY on the provided Context Data.
    2. If the user asks for a list, category, or item details, respond with a Markdown table.
    3. IMPORTANT: Ensure there are TWO blank lines before the table starts.
    4. The table MUST include these columns: S/NO, ITEM DESCRIPTION, CATEGORY, LEAD TIME (DAYS), REMARKS, CREATED BY.
    5. IMPORTANT: If there are more than 20 items matching the request, show only the first 20.
    6. At the end of the response (after the table or note), include a summary in this exact format:
       ✅ Total rows: [total count of matching items]
       ✅ Columns: 6
    7. CRITICAL: You MUST provide exactly 3 follow-up suggestions in the "suggestions" array.

    SUGGESTION LOGIC:
    - Suggestions MUST be specific, actionable queries based on the data.
    - Suggestions MUST be short (under 6 words).
    - GOOD: "Show items in R & M", "Lead time for Ventilation", "List all categories"
    - BAD: "Would you like to know...", "Can I help you with...", "Do you want to see..."
    - VARY the suggestions: 
        1. One about a related category or listing all categories.
        2. One about a specific item mentioned or related.
        3. One about filtering by a column (e.g., Lead time, Created by).

    Output Format:
    You must format your entire response strictly as follows:

    <<<ANSWER>>>
    [Put your full answer here, including any text and the markdown table]
    <<</ANSWER>>>

    <<<SUGGESTIONS>>>
    [Suggestion 1]
    [Suggestion 2]
    [Suggestion 3]
    <<</SUGGESTIONS>>>
    """

    # Disable JSON mode to avoid escaping issues with complex markdown tables
    raw_result = chat_llm(prompt, json_mode=False)
    
    # Parse the delimited response
    return parse_llm_response(raw_result)

@app.post("/generate-report")
def generate_report(request: ReportRequest):
    print(f"Generating report for history: {request.chat_history}")
    
    inventory_context = df_to_context(inventory_df, "Procurement/Maintenance Data")
    
    history_text = "\n".join([f"User: {msg}" for msg in request.chat_history])

    prompt = f"""
    Context Data:
    {inventory_context}

    Chat History:
    {history_text}

    Instructions:
    1. Analyze the Chat History to identify all specific items or categories the user asked about.
    2. Create a summary report specifically focusing on the LEAD TIME for these items.
    3. Present the data in a Markdown table with columns: S/NO, ITEM DESCRIPTION, CATEGORY, LEAD TIME (DAYS).
    4. If no specific items were discussed, show a general summary of items with short lead times (e.g., 7 days).
    5. IMPORTANT: Ensure there are TWO blank lines before the table starts.
    
    SUGGESTION LOGIC:
    - Suggestions MUST be specific, actionable queries for the next steps.
    - Suggestions MUST be short (under 6 words).
    - GOOD: "Analyze cost for these", "List all categories", "Compare lead times"
    - BAD: "Would you like to...", "Do you want information about..."

    Output Format:
    You must format your entire response strictly as follows:

    <<<ANSWER>>>
    Here is the Lead Time Report based on your session:

    [Markdown Table]
    <<</ANSWER>>>

    <<<SUGGESTIONS>>>
    [Suggestion 1]
    [Suggestion 2]
    [Suggestion 3]
    <<</SUGGESTIONS>>>
    """

    raw_result = chat_llm(prompt, json_mode=False)
    return parse_llm_response(raw_result)

def parse_llm_response(raw_result: str):
    # Default suggestions if none found
    default_suggestions = ["Show items in R & M", "Search for 'Ventilation'", "What is the lead time for item 1?"]
    suggestions = default_suggestions

    try:
        # Extract Answer
        answer_match = re.search(r"<<<ANSWER>>>(.*?)<<</ANSWER>>>", raw_result, re.DOTALL)
        if answer_match:
            answer = answer_match.group(1).strip()
        else:
            # Silently fall back to raw result if tags are missing
            answer = raw_result

        # Extract Suggestions
        suggestions_match = re.search(r"<<<SUGGESTIONS>>>(.*?)<<</SUGGESTIONS>>>", raw_result, re.DOTALL)
        if suggestions_match:
            suggestions_text = suggestions_match.group(1).strip()
            suggestions_list = [s.strip() for s in suggestions_text.split('\n') if s.strip()]
            if suggestions_list:
                suggestions = suggestions_list[:3]
        
        return {
            "answer": answer,
            "suggestions": suggestions
        }

    except Exception as e:
        print(f"Parsing Error: {e}")
        # Fallback to returning the raw result so the user still sees the content
        return {
            "answer": raw_result,
            "suggestions": default_suggestions
        }