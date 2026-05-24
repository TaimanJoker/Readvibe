import google.generativeai as genai
import json
from database import get_secret

def verify_quote_with_ai(content, title, author):
    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        return {"verified": True, "reason": "AI verification skipped (No API Key)", "title": title, "author": author}

    genai.configure(api_key=api_key)
    friendly_prefix = "We couldn't verify this quote right now. 🌿"

    # Try models starting from newest to oldest stable
    models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']

    # 1. Try hardcoded preferred models
    for model_name in models_to_try:
        res = _try_model(model_name, content, title, author)
        if res: return res

    # 2. Dynamic Fallback: Find ANY flash model in the list
    try:
        available_models = [m.name for m in genai.list_models()]
        flash_models = [m for m in available_models if 'flash' in m]
        if flash_models:
            res = _try_model(flash_models[0], content, title, author)
            if res: return res
    except:
        pass

    return {
        "verified": False, 
        "reason": f"{friendly_prefix} (Please try again in a moment! 🌿)", 
        "title": title, 
        "author": author
    }

def _try_model(model_name, content, title, author):
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"""
        Task: Strict Verification for Readvibe.
        Quote: "{content}"
        Title: "{title}"
        Author: "{author}"
        
        RULES:
        1. If the quote is accurately attributed to a published book, movie, or historical figure, "verified" MUST be true. Minor punctuation/word differences are acceptable.
        2. If title/author are generic (e.g., "Anonymous", "Internet") but you know the exact correct source, fill them in and set "verified" to true.
        3. If it is completely fake, hallucinated, or wrongly attributed, set "verified" to false and explain why in "reason".
        
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
            return json.loads(text)
    except:
        return None
