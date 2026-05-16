import google.generativeai as genai
import json
from database import get_secret

# Setup Gemini
GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def verify_quote_with_ai(content, title, author):
    """
    Uses Gemini to verify the quote, author, and title.
    Enforces:
    - Language: English
    - Length: <= 300 chars
    - Accuracy: Fact-checks the author/title
    """
    if not GEMINI_API_KEY:
        # Fallback if no API key is provided yet
        return {"verified": True, "reason": "AI verification skipped (no API key)", "title": title, "author": author}

    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a strict Quote Verification Agent for the 'Readvibe' platform.
    Your job is to verify the following quote submission:
    
    Quote: "{content}"
    Claimed Title: "{title}"
    Claimed Author: "{author}"
    
    RULES:
    1. Language must be English.
    2. Quote length must be <= 300 characters.
    3. Fact-check the author and source title. If the user left them blank or incorrect, you MUST provide the correct ones if possible.
    4. Verify if the author actually said/wrote this.
    5. Be strict but helpful.
    
    RESPONSE FORMAT:
    You must respond ONLY with a JSON object in this format:
    {{
        "verified": boolean,
        "reason": "short explanation of rejection or acceptance",
        "title": "the corrected or original title",
        "author": "the corrected or original author"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean the response to ensure it's just JSON
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        
        result = json.loads(text)
        
        # Final length check in code as well
        if len(content) > 300:
            result["verified"] = False
            result["reason"] = "Quote exceeds 300 characters."
            
        return result
    except Exception as e:
        return {
            "verified": False, 
            "reason": f"AI verification failed: {str(e)}", 
            "title": title, 
            "author": author
        }
