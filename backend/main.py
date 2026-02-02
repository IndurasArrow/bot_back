from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import sys
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    history: list[dict] = []

class ReportRequest(BaseModel):
    chat_history: list[str]

def send_email_notification(details: str):
    """
    Sends an email notification using SMTP.
    """
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", 587))
    receiver_email = "divyansh.m@superaip.com"

    print("---------------------------------------------------------")
    print(f"📧 Preparing to send email to: {receiver_email}")
    
    if not sender_email or not sender_password:
        print("⚠️  Email credentials (EMAIL_SENDER, EMAIL_PASSWORD) not found in .env.")
        print("⚠️  Mocking email send. Here is the content:")
        print(f"SUBJECT: Procurement Request - Lead Time Generation")
        print(f"BODY:\n{details}")
        print("---------------------------------------------------------")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = "Procurement Request - Lead Time Generation"

        msg.attach(MIMEText(details, "plain"))

        print(f"🔌 Connecting to SMTP server: {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        
        print("🔑 Logging in...")
        server.login(sender_email, sender_password)
        
        print("🚀 Sending email...")
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()

        print(f"✅ Email sent successfully to {receiver_email}")
        print("---------------------------------------------------------")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        print("---------------------------------------------------------")
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
       - If the user explicitly asks to "Send procurement email for..." or "Confirm request for..." a list of items:
       - You MUST include `<<<ACTION:SEND_EMAIL>>>` in your response.
       - Respond with a clear confirmation message like "Email request sent successfully."
    5. IMPORTANT: Ensure there are TWO blank lines before the table starts.
    6. The table MUST include these columns: S/NO, ITEM DESCRIPTION, CATEGORY, LEAD TIME (DAYS), REMARKS, CREATED BY.
    7. IMPORTANT: If there are more than 20 items matching the request, show only the first 20.
    8. At the end of the response (after the table or note), include a summary in this exact format:
       ✅ Total rows: [total count of matching items]
       ✅ Columns: 6
    9. **FORMATTING:** Use standard Markdown for tables (e.g., | Column 1 | Column 2 |). DO NOT use HTML tags like <TABLE>.
    10. CRITICAL: You MUST provide exactly 3 follow-up suggestions in the "suggestions" array.
    11. **NO DUPLICATION:** Do NOT repeat the table. Do NOT include text suggestions in the <<<ANSWER>>> block. Only provide suggestions in the <<<SUGGESTIONS>>> block.

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
    
    # Check for Action
    if "<<<ACTION:SEND_EMAIL>>>" in raw_result:
        # We need to extract what to email. Usually the previous bot message or the current summary.
        # For simplicity, we'll email the current answer content or a fixed message.
        # Ideally, the LLM should provide the content to email.
        # Let's assume the LLM summarizes what is being sent in the Answer.
        send_email_notification(f"User confirmed request.\n\nContext:\n{history_text}\n\nUser Request: {request.message}")
        # Remove the action tag from the result so the user doesn't see it (though parse_llm_response handles tags)
        raw_result = raw_result.replace("<<<ACTION:SEND_EMAIL>>>", "")

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
    1. Analyze the ENTIRE Chat History to identify EVERY specific item or category the user has asked about in this session. Do not miss any.
    2. Create a summary report specifically focusing on the LEAD TIME for these items.
    3. Present the data in a Markdown table with columns: S/NO, ITEM DESCRIPTION, CATEGORY, LEAD TIME (DAYS).
    4. **DATA EXTRACTION:** You MUST also provide the raw data for the report in JSON format wrapped in `<<<DATA>>>` tags.
       - The JSON should be a list of dictionaries.
       - Example: <<<DATA>>>[{{"S/NO": "1", "ITEM": "Valve"}}]<<</DATA>>>
    5. If no specific items were discussed, show a general summary of items with short lead times (e.g., 7 days).
    6. IMPORTANT: Ensure there are TWO blank lines before the table starts.
    7. **FORMATTING:** Use standard Markdown for tables (e.g., | Column 1 | Column 2 |). DO NOT use HTML tags like <TABLE>.
    8. CRITICAL: You MUST provide exactly 3 follow-up suggestions.
    9. **NO DUPLICATION:** Do NOT repeat the table. Do NOT include text suggestions in the <<<ANSWER>>> block. Only provide suggestions in the <<<SUGGESTIONS>>> block.
    
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