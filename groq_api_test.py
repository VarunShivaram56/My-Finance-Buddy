import os
from dotenv import load_dotenv
from groq import Groq

# Load .env from backend folder
load_dotenv(dotenv_path="backend/.env")

api_key = os.getenv("AGENT_ONE_API_KEY")

def test_groq():
    if not api_key:
        print("❌ GROQ API key not found in .env")
        return

    try:
        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Groq compound model
            messages=[
                {"role": "user", "content": "Explain what is machine learning in simple terms"}
            ]
        )

        print("✅ Groq Response:\n")
        print(response.choices[0].message.content)

    except Exception as e:
        print("❌ Error occurred while calling Groq API\n")

        error_message = str(e)

        # Common error handling
        if "rate limit" in error_message.lower():
            print("⚠️ Rate limit exceeded: Too many requests")
        elif "invalid api key" in error_message.lower():
            print("⚠️ Invalid API Key")
        elif "quota" in error_message.lower():
            print("⚠️ Quota exceeded")
        else:
            print("⚠️ General Error:", error_message)


if __name__ == "__main__":
    test_groq()