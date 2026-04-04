import os
import requests
from dotenv import load_dotenv

# Load .env from backend folder
load_dotenv(dotenv_path="backend/.env")

api_key = os.getenv("AGENT_THREE_API_KEY")

def test_openrouter():
    if not api_key:
        print("❌ OpenRouter API key not found in .env")
        return

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {"role": "user", "content": "What is artificial intelligence?Give me a brief answer in 2 sentences."}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)

        # Check HTTP errors
        if response.status_code != 200:
            print("❌ API Error:")
            print(response.text)
            return

        result = response.json()

        print("✅ OpenRouter Response:\n")
        print(result["choices"][0]["message"]["content"])

    except requests.exceptions.RequestException as e:
        print("❌ Network Error:", str(e))

    except Exception as e:
        print("❌ Unexpected Error occurred\n")

        error_message = str(e)

        # Common error handling
        if "rate limit" in error_message.lower():
            print("⚠️ Rate limit exceeded")
        elif "invalid" in error_message.lower():
            print("⚠️ Invalid API key or request")
        elif "quota" in error_message.lower():
            print("⚠️ Quota exceeded")
        else:
            print("⚠️ General Error:", error_message)


if __name__ == "__main__":
    test_openrouter()