import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: API key not found.")
else:
    try:
        print("Connecting to Gemini...", flush=True)

        client = genai.Client(
            api_key=api_key,
            http_options={"timeout": 15000}
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents="Give 3 simple learning tips for a beginner Python student."
        )

        print("\nGemini API connected successfully!", flush=True)
        print(response.text, flush=True)

    except Exception as e:
        print("\nGemini API error:", e, flush=True)