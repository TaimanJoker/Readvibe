import google.generativeai as genai
import json
from database import get_secret

def verify_quote_with_ai(content, title, author):
    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        return {"verified": True, "reason": "AI verification skipped (No API Key)", "title": title, "author": author}

    # Re-configure to ensure the key is active in this process
    genai.configure(api_key=api_key)

    friendly_prefix = "We couldn't verify this quote right now. 🌿"

    # Try the most reliable model names
    models_to_try = ['gemini-1.5-flash', 'models/gemini-1.5-flash']

    last_error = ""
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)

            prompt = f"""
            Task: Verify if this is a real quote and identify the author/title.
            Quote: "{content}"
            Title: "{title}"
            Author: "{author}"

            Format: Respond ONLY in JSON.
            {{ "verified": boolean, "reason": "friendly text", "title": "string", "author": "string" }}
            """

            response = model.generate_content(prompt)

            if response and response.text:
                text = response.text.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()

                result = json.loads(text)
                return result
        except Exception as e:
            last_error = str(e)
            continue

    # If we failed, let's try to help the developer by showing what models ARE available
    try:
        available = [m.name for m in genai.list_models()]
        debug_info = f"Models available: {available}"
    except:
        debug_info = "Could not list models."

    return {
        "verified": False, 
        "reason": f"{friendly_prefix} (Debug: {last_error[:50]} | {debug_info[:100]})", 
        "title": title, 
        "author": author
    }

