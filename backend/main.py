from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from .data import inventory_df
from .utils import df_to_context
from .llm import chat_llm

from fastapi.middleware.cors import CORSMiddleware
import json

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
    3. The table MUST include these columns: S/NO, ITEM DESCRIPTION, CATEGORY, LEAD TIME (DAYS), REMARKS, CREATED BY.
    4. IMPORTANT: If there are more than 20 items matching the request, show the first 20 and add a note that more items are available.
    5. CRITICAL: You MUST provide exactly 3 follow-up suggestions in the "suggestions" array. These should be questions the user might ask next (e.g., specific item details, other categories, or lead times).

    Return the result as a VALID JSON object with this structure:
    {{
        "answer": "Your text and markdown table here",
        "suggestions": ["Follow-up Q1", "Follow-up Q2", "Follow-up Q3"]
    }}
    """

    raw_result = chat_llm(prompt, json_mode=True)
    
    # Robust JSON extraction
    clean_result = raw_result.strip()
    if clean_result.startswith("```json"):
        clean_result = clean_result.replace("```json", "", 1).rsplit("```", 1)[0].strip()
    elif clean_result.startswith("```"):
        clean_result = clean_result.replace("```", "", 1).rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(clean_result)
        suggestions = parsed.get("suggestions", [])
        print(f"Generated Suggestions: {suggestions}") # Debug log
        
        return {
            "answer": parsed.get("answer", "No answer provided."),
            "suggestions": suggestions
        }
    except json.JSONDecodeError as e:
        print(f"JSON Error: {e}")
        print(f"Raw Result: {raw_result}")
        return {
            "answer": "I processed the data but had trouble formatting the final response. Please try asking for a specific item or a smaller category.",
            "suggestions": ["Show items in R & M", "Search for 'Ventilation'", "What is the lead time for item 1?"]
        }