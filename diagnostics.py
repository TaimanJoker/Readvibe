import google.generativeai as genai
import os
from dotenv import load_dotenv

# This is a diagnostic script to run in the terminal or as a temporary streamlit page
def run_diagnostics():
    print("--- Readvibe AI Diagnostics ---")
    
    # 1. Check API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("FAIL: GEMINI_API_KEY not found in environment.")
        return
    else:
        print(f"SUCCESS: API Key found (starts with: {api_key[:5]}...)")

    # 2. Configure and List Models
    try:
        genai.configure(api_key=api_key)
        print("Attempting to list models...")
        models = genai.list_models()
        model_names = [m.name for d in [models] for m in d] # Handle iterator
        print(f"SUCCESS: Found {len(model_names)} models.")
        print(f"Models available: {model_names}")
    except Exception as e:
        print(f"FAIL: Could not list models. Error: {e}")
        return

    # 3. Simple Generation Test
    test_model = 'models/gemini-1.5-flash'
    if test_model not in model_names:
        # Try to find any flash or pro model
        test_model = next((m for m in model_names if 'flash' in m or 'pro' in m), None)
    
    if not test_model:
        print("FAIL: No suitable Gemini model found in your account.")
        return

    print(f"Testing generation with model: {test_model}...")
    try:
        model = genai.GenerativeModel(test_model)
        response = model.generate_content("Say 'Hello Readvibe' if you can hear me.")
        print(f"SUCCESS: AI Response: {response.text}")
    except Exception as e:
        print(f"FAIL: Content generation failed. Error: {e}")

if __name__ == "__main__":
    load_dotenv()
    run_diagnostics()
