import os
import google.generativeai as genai
from dotenv import load_dotenv
import time
import random

try:
    from backend.prompts import SYSTEM_PROMPT
except ImportError:
    from prompts import SYSTEM_PROMPT
    


load_dotenv(override=True)

# Configure Gemini
# Ensure you have GOOGLE_API_KEY in your .env file
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

MODEL = "gemini-2.0-flash-lite-preview-02-05" 

def chat_llm(message: str, json_mode: bool = False) -> str:
    generation_config = {}
    if json_mode:
        generation_config["response_mime_type"] = "application/json"

    model = genai.GenerativeModel(
        model_name=MODEL,
        system_instruction=SYSTEM_PROMPT,
        generation_config=generation_config
    )
    
    max_retries = 5
    base_delay = 2

    for attempt in range(max_retries):
        try:
            response = model.generate_content(message)
            return response.text
        except Exception as e:
            error_str = str(e)
            # Check for 429 Resource Exhausted error
            if "429" in error_str or "Resource exhausted" in error_str:
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    sleep_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                    print(f"Rate limited (429). Retrying in {sleep_time:.2f}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(sleep_time)
                    continue
                else:
                    return f"Error communicating with Gemini: Rate limit exceeded after {max_retries} retries."
            else:
                # For non-429 errors, return immediately
                return f"Error communicating with Gemini: {error_str}"
    
    return "Error communicating with Gemini: Unknown error."