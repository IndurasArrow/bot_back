from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from data import inventory_df, warehouse_df
from report_service import get_out_of_stock_price_report
from utils import df_to_context
from llm import chat_llm

from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI(
    title="PVR Chat Assistant",
    description="Query your inventory and warehouse data",
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
    print("Inside the chat endpoint")
    
    inventory_context = df_to_context(inventory_df, "Inventory Data")
    warehouse_context = df_to_context(warehouse_df, "Warehouse Data")

    prompt = f"""
    {inventory_context}

    {warehouse_context}

    User Question: {request.message}

    Answer the question first.
    Then suggest 3 short follow-up questions the user might ask next.
    Return the result as JSON with keys:
    - answer
    - suggestions (array of strings)
    """

    result = chat_llm(prompt)

    parsed = json.loads(result)
    print("suggestions: ", parsed["suggestions"])
    return {
        "answer": parsed["answer"],
        "suggestions": parsed["suggestions"]
    }


@app.post("/generate-price-report")
def generate_price_report():
    report_context = get_out_of_stock_price_report()

    prompt = f"""
    You are a procurement assistant for PVR Cinemas.

    Based ONLY on the following report data,
    generate a report

    Report Data:
    {report_context}
    """

    result = chat_llm(prompt)
    return {
        "answer": result
    }
