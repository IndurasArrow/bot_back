from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import sys
import os
import smtplib
import logging
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add the parent directory to sys.path to allow imports from 'backend' if running from root,
# or ensure current dir is in path if running from inside backend.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

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
    title="AI Chat Assistant",
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
    history: list[dict] = []

class ReportRequest(BaseModel):
    chat_history: list[str]

def send_email_notification(details: str):
    """
    Sends an email using the Gmail API (Port 443 - Firewall Friendly).
    """
    receiver_email = "vcs.vin3@gmail.com"
    subject = "Procurement Request - Lead Time Generation"
    
    logger.info("---------------------------------------------------------")
    logger.info(f"📧 Preparing to send email via Gmail API to: {receiver_email}")

    # Determine absolute path for token.json to avoid CWD issues
    base_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(base_dir, 'token.json')

    # Check if the token file exists (uploaded via Render Secret Files)
    if not os.path.exists(token_path):
        logger.error(f"❌ 'token.json' not found at {token_path}. Please upload it as a Secret File in Render.")
        return False

    try:
        # 1. Load Credentials
        creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/gmail.send'])
        
        # Refresh if expired (Google handles this automatically)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        # 2. Build the Service
        service = build('gmail', 'v1', credentials=creds)

        # 3. Create the Email Message
        message = MIMEMultipart()
        message['To'] =", ".join(receiver_email)
        message['Subject'] = subject
        message.attach(MIMEText(details, 'plain'))
        
        # Encode the message (Gmail API requires base64url format)
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw_message}

        # 4. Send
        logger.info("🚀 Sending email via API...")
        sent_message = service.users().messages().send(userId="me", body=body).execute()
        
        logger.info(f"✅ Email sent successfully! Message ID: {sent_message['id']}")
        logger.info("---------------------------------------------------------")
        return True

    except Exception as e:
        logger.exception(f"❌ Gmail API Error: {e}")
        logger.info("---------------------------------------------------------")
        return False

@app.post("/chat")
def chat(request: ChatRequest):
    print(f"User Message: {request.message}")
    
    inventory_context = df_to_context(inventory_df, "Procurement/Maintenance Data")

    # Format history for the LLM
    history_text = ""
    if request.history:
        # Take last 6 messages to provide context
        for msg in request.history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_text += f"{role.upper()}: {content}\n"

    prompt = f"""
    Context Data:
    {inventory_context}

    Chat History:
    {history_text}

    User Question: {request.message}

    Instructions:
    1. **GREETINGS:** If the user input is a greeting (e.g., 'hi', 'hello'), respond with a polite greeting and ask how you can assist. Do NOT list items or show a table.
    2. Answer based ONLY on the provided Context Data.
    3. If the user asks for a list, category, or item details, respond with a Markdown table.
    4. **EMAIL TRIGGER:**
       - **Step 1 (Request Initiated):** If the user asks to "Send procurement email for..." or "Confirm request for..." a list of items:
         - Do NOT include `<<<ACTION:SEND_EMAIL>>>` yet.
         - You MUST list the items to be requested.
         - You MUST explicitly ask: "Do you want to send this request to the Procurement Team? Please reply 'Yes' to confirm."
    5. IMPORTANT: Ensure there are TWO blank lines before the table starts.
    6. The table MUST include these columns: S/NO, ITEM DESCRIPTION, CATEGORY, LEAD TIME (DAYS), REMARKS, CREATED BY.
    7. IMPORTANT: If there are more than 20 items matching the request, show only the first 20.
    8. At the end of the response (after the table or note), include a summary in this exact format:
       ✅ Total rows: [total count of matching items]
       ✅ Columns: 6
    9. **FORMATTING:** Use standard Markdown for tables (e.g., | Column 1 | Column 2 |). DO NOT use HTML tags like <TABLE>.
    10. CRITICAL: You MUST provide exactly 3 follow-up suggestions in the "suggestions" array.
    11. **NO DUPLICATION:** Do NOT repeat the table. Do NOT include text suggestions in the <<<ANSWER>>> block. Only provide suggestions in the <<<SUGGESTIONS>>> block.
    
    CRITICAL ACTION INSTRUCTIONS:
    - If the user confirms a request (says "Yes", "Confirm", "Go ahead"):
      1. You MUST include the tag `<<<ACTION:SEND_EMAIL>>>` anywhere in your response.
      2. Respond with EXACTLY: "Email request sent successfully."
    
    ----- EXAMPLE INTERACTION -----
    User: Yes, please confirm.
    Assistant:
    <<<ANSWER>>>
    <<<ACTION:SEND_EMAIL>>>
    Email request sent successfully.
    <<</ANSWER>>>
    -------------------------------

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

    # This will show you EXACTLY why it failed if it happens again
    print("------------------------------------------------")
    print(f"DEBUG: Raw AI Response:\n{raw_result}") 
    print("------------------------------------------------")
    
    # [CHANGE 2] THE ROBUST TRIGGER CHECK
    # We now check for the Tag OR the specific Phrase the model loves to use.
    trigger_phrase = "Email request sent successfully"
    
    if "<<<ACTION:SEND_EMAIL>>>" in raw_result or trigger_phrase in raw_result:
        print(f"DEBUG: Trigger found! (Tag or Phrase detected)")
        
        # Send the email
        email_success = send_email_notification(f"User confirmed request.\n\nContext:\n{history_text}\n\nUser Request: {request.message}")
        
        # Cleanup the tag if it exists so the user doesn't see it
        raw_result = raw_result.replace("<<<ACTION:SEND_EMAIL>>>", "")
        
        # Optional: If email failed, let the user know by overwriting the success message
        if not email_success:
             raw_result = raw_result.replace(trigger_phrase, "I tried to send the email, but there was a server error.")
    else:
        print("DEBUG: No Action tag or Trigger phrase found.")

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
    1. Analyze the Chat History to identify EVERY specific item or category the user has asked about in this session.
    2. **STRICT FILTERING:** Only include items that were EXPLICITLY requested or discussed by the user. Do NOT include random items from the context.
    3. If NO specific items were found in the history, respond with: "No specific items were found in the chat history to generate a report." and return an empty JSON array `<<<DATA>>>[]<<</DATA>>>`.
    4. Create a summary report specifically focusing on the LEAD TIME for the identified items.
    5. Present the data in a Markdown table with columns: S/NO, ITEM DESCRIPTION, CATEGORY, LEAD TIME (DAYS).
    6. **DATA EXTRACTION:** You MUST also provide the raw data for the report in JSON format wrapped in `<<<DATA>>>` tags.
       - The JSON should be a list of dictionaries.
       - The JSON data must match the rows in the Markdown table exactly.
       - Example: <<<DATA>>>[{{"S/NO": "1", "ITEM DESCRIPTION": "Valve", "CATEGORY": "...", "LEAD TIME (DAYS)": "..."}}]<<</DATA>>>
    7. IMPORTANT: Ensure there are TWO blank lines before the table starts.
    8. **FORMATTING:** Use standard Markdown for tables (e.g., | Column 1 | Column 2 |). DO NOT use HTML tags like <TABLE>.
    9. CRITICAL: You MUST provide exactly 3 follow-up suggestions.
    10. **NO DUPLICATION:** Do NOT repeat the table. Do NOT include text suggestions in the <<<ANSWER>>> block. Only provide suggestions in the <<<SUGGESTIONS>>> block.
    
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
    
    <<<DATA>>>
    [JSON Array of items if applicable]
    <<</DATA>>>

    <<<SUGGESTIONS>>>
    [Suggestion 1]
    [Suggestion 2]
    [Suggestion 3]
    <<</SUGGESTIONS>>>
    """

    raw_result = chat_llm(prompt, json_mode=False)
    return parse_llm_response(raw_result)

def parse_llm_response(raw_result: str):
    default_suggestions = ["Show items in R & M", "Search for 'Ventilation'", "What is the lead time for item 1?"]
    suggestions = default_suggestions
    answer = raw_result
    data = []

    try:
        # 1. Extract Data (using regex to find it anywhere)
        data_match = re.search(r"<<<DATA>>>(.*?)<<</DATA>>>", raw_result, re.DOTALL)
        if data_match:
            try:
                data_text = data_match.group(1).strip()
                data = json.loads(data_text)
            except json.JSONDecodeError:
                print("Failed to parse JSON data from LLM")
        
        # 2. Extract Suggestions
        suggestions_match = re.search(r"<<<SUGGESTIONS>>>(.*?)<<</SUGGESTIONS>>>", raw_result, re.DOTALL)
        if suggestions_match:
            suggestions_text = suggestions_match.group(1).strip()
            suggestions_list = [s.strip() for s in suggestions_text.split('\n') if s.strip()]
            if suggestions_list:
                suggestions = suggestions_list[:3]

        # 3. Extract Answer (prioritize the tag, but have a fallback)
        answer_match = re.search(r"<<<ANSWER>>>(.*?)<<</ANSWER>>>", raw_result, re.DOTALL)
        if answer_match:
            answer = answer_match.group(1).strip()
        else:
            # Fallback: remove other known tags from the raw result
            temp_answer = raw_result
            # Remove DATA block
            temp_answer = re.sub(r"<<<DATA>>>.*?<<</DATA>>>", "", temp_answer, flags=re.DOTALL)
            # Remove SUGGESTIONS block
            temp_answer = re.sub(r"<<<SUGGESTIONS>>>.*?<<</SUGGESTIONS>>>", "", temp_answer, flags=re.DOTALL)
            answer = temp_answer.strip()

        # 4. Aggressive Cleanup of Tags (Standard & Malformed)
        # This handles cases where regex fails or tags are slightly malformed (e.g. <</ANSWER>>>)
        tags_to_remove = [
            "<<<ANSWER>>>", "<<</ANSWER>>>", "<</ANSWER>>>", 
            "<<<DATA>>>", "<<</DATA>>>", "<</DATA>>>", 
            "<<<SUGGESTIONS>>>", "<<</SUGGESTIONS>>>", "<</SUGGESTIONS>>>"
        ]
        for tag in tags_to_remove:
            answer = answer.replace(tag, "")
        
        return {
            "answer": answer.strip(),
            "suggestions": suggestions,
            "data": data
        }

    except Exception as e:
        print(f"Parsing Error: {e}")
        # Fallback: try to clean up raw result
        clean_result = raw_result
        clean_result = re.sub(r"<<<DATA>>>.*?<<</DATA>>>", "", clean_result, flags=re.DOTALL)
        clean_result = re.sub(r"<<<SUGGESTIONS>>>.*?<<</SUGGESTIONS>>>", "", clean_result, flags=re.DOTALL)
        clean_result = clean_result.replace("<<<ANSWER>>>", "").replace("<<</ANSWER>>>", "")
        
        return {
            "answer": clean_result.strip(),
            "suggestions": default_suggestions,
            "data": []
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
