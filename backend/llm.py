import os
from openai import OpenAI
from dotenv import load_dotenv

from prompts import SYSTEM_PROMPT

load_dotenv(override=True)

client = OpenAI()
MODEL = "qwen/qwen3-next-80b-a3b-instruct"

def chat_llm(message: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content
