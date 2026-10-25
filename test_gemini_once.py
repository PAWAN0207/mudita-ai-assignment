
from core.gemini_client import generate_response

try:
    print("Testing Gemini API with one request...")

    response = generate_response(
        "Reply with exactly: GEMINI_API_WORKING"
    )

    print("\nSUCCESS")
    print("Response:", response)

except Exception as exc:
    print("\nFAILED")
    print("Error:", exc)
