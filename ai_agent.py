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

    # Friendly error message for all AI failures
    friendly_error = "We couldn't verify this quote right now. Please check the spelling or try a different one! 🌿"

    # Try different model identifiers that might be supported by the current SDK version
    models_to_try = ['gemini-1.5-flash', 'gemini-pro']

    last_exception = None
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)

            prompt = f"""
            Verify this quote for 'Readvibe'. 
            Content: "{content}"
            Title: "{title}"
            Author: "{author}"

            RULES:
            1. Language: English only.
            2. Length: <= 300 chars.
            3. Accuracy: Fact-check author/title. Fill missing ones.

            RESPOND ONLY IN JSON:
            {{ "verified": bool, "reason": "short friendly reason", "title": "str", "author": "str" }}
            """

            response = model.generate_content(prompt)
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()

            result = json.loads(text)

            # User requested friendly, non-technical reasons
            if not result.get("verified"):
                result["reason"] = "We couldn't verify this quote or its author. Please double-check the details or try another one! 🌿"

            return result
        except Exception as e:
            last_exception = e
            continue # Try next model

    # If all models fail
    return {
        "verified": False, 
        "reason": friendly_error, 
        "title": title, 
        "author": author
    }

