import google.generativeai as genai
import os

GEMINI_API_KEY = "AIzaSyDVgHAvnclF_ethXsNNQCA_HGVtr-4HlNk"
genai.configure(api_key=GEMINI_API_KEY)

print("Listing models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error: {e}")
