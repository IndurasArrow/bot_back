import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import time
import random

try:
    from backend.prompts import SYSTEM_PROMPT
except ImportError:
    from prompts import SYSTEM_PROMPT

load_dotenv(override=True)

# Initialize the GenAI client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

MODEL = "gemini-2.5-flash-lite"

def chat_llm(message: str, json_mode: bool = False) -> str:
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
    )
    
    if json_mode:
        config.response_mime_type = "application/json"

    max_retries = 5
    base_delay = 2

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=message,
                config=config
            )
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