import google.generativeai as genai
import json
from database import get_secret

# Setup Gemini
GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def verify_quote_with_ai(content, title, author):
    if not GEMINI_API_KEY:
        return {"verified": True, "reason": "AI verification skipped", "title": title, "author": author}

    # Friendly error message template
    friendly_prefix = "We couldn't verify this quote right now. 🌿"

    # Try specific model strings
    models_to_try = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']

    error_details = ""
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)

            prompt = f"""
            You are a verification agent for Readvibe.
            Task: Verify if this quote is real, find the author/title if missing.

            Quote: "{content}"
            Title: "{title}"
            Author: "{author}"

            Rules:
            - English only.
            - Length max 300.
            - Fact-check accuracy.

            Respond ONLY in valid JSON:
            {{ "verified": bool, "reason": "friendly string", "title": "str", "author": "str" }}
            """

            response = model.generate_content(prompt)

            if not response or not response.text:
                error_details = "AI returned an empty response."
                continue

            text = response.text.strip()
            # Handle potential markdown formatting in response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            result = json.loads(text)
            return result

        except Exception as e:
            error_details = str(e)
            continue

    # If we reached here, all attempts failed
    return {
        "verified": False, 
        "reason": f"{friendly_prefix} (Error: {error_details[:100]})", 
        "title": title, 
        "author": author
    }
