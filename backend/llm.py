import os
import google.generativeai as genai
from dotenv import load_dotenv

try:
    from backend.prompts import SYSTEM_PROMPT
except ImportError:
    from prompts import SYSTEM_PROMPT
    


load_dotenv(override=True)

# Configure Gemini
# Ensure you have GOOGLE_API_KEY in your .env file
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

MODEL = "gemini-2.5-flash-lite" 

def chat_llm(message: str, json_mode: bool = False) -> str:
    generation_config = {}
    if json_mode:
        generation_config["response_mime_type"] = "application/json"

    model = genai.GenerativeModel(
        model_name=MODEL,
        system_instruction=SYSTEM_PROMPT,
        generation_config=generation_config
    )
    
    try:
        response = model.generate_content(message)
        return response.text
    except Exception as e:
        return f"Error communicating with Gemini: {str(e)}"