import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)

models_to_try = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-pro-latest"
]

prompt = "Hello, respond with 'working' if you receive this."

for m_name in models_to_try:
    print(f"\nTrying model: {m_name}")
    try:
        model = genai.GenerativeModel(m_name)
        response = model.generate_content(prompt)
        print(f"SUCCESS! Response: {response.text.strip()}")
        break
    except Exception as e:
        print(f"FAILED: {type(e).__name__} - {e}")
