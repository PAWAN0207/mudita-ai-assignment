
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


# Project root directory
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

# Load .env for local development
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(ENV_FILE)


def get_secret(name: str, default=None):
    """
    Read configuration from environment variables or Streamlit Secrets.
    Environment variables take priority.
    """
    value = os.getenv(name)

    if value:
        return value

    try:
        import streamlit as st

        return st.secrets.get(name, default)
    except Exception:
        return default


# Gemini configuration
API_KEY = get_secret("GEMINI_API_KEY")
MODEL_NAME = get_secret("GEMINI_MODEL", "gemini-3.8-flash")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. "
        "Set it in your local .env file or Streamlit Cloud Secrets."
    )

# Initialize Gemini client
client = genai.Client(api_key=API_KEY)

# Retry configuration
MAX_ATTEMPTS = 3
INITIAL_RETRY_DELAY = 2


def generate_response(prompt: str, json_mode: bool = False) -> str:
    """
    Generate a response using the Gemini API.

    Retries transient server errors up to three total attempts.
    Does not automatically retry quota or authentication errors.
    Supports normal text and JSON output.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    config = None

    if json_mode:
        config = types.GenerateContentConfig(
            response_mime_type="application/json"
        )

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config,
            )

            response_text = response.text

            if not response_text or not response_text.strip():
                raise RuntimeError(
                    "Gemini returned an empty response. Please try again."
                )

            return response_text.strip()

        except errors.APIError as exc:
            status_code = getattr(exc, "code", None)

            # Retry only temporary server-side errors.
            # Do not retry quota, authentication, permission,
            # invalid request, or model-not-found errors.
            retryable = (
                isinstance(status_code, int)
                and status_code in (500, 502, 503, 504)
            )

            if retryable and attempt < MAX_ATTEMPTS:
                delay = INITIAL_RETRY_DELAY * (2 ** (attempt - 1))

                print(
                    f"Temporary Gemini API error ({status_code}). "
                    f"Retrying in {delay}s "
                    f"(attempt {attempt + 1}/{MAX_ATTEMPTS})..."
                )

                time.sleep(delay)
                continue

            raise RuntimeError(
                f"Gemini API error (code={status_code}): {exc.message}"
            ) from exc

    raise RuntimeError(
        "Gemini request failed after multiple attempts."
    )


if __name__ == "__main__":
    try:
        result = generate_response(
            "Introduce yourself in one sentence as an AI assistant."
        )

        print("\nGemini API connection successful!")
        print("Model:", MODEL_NAME)
        print("Response:", result)

    except Exception as exc:
        print("Gemini API test failed:", str(exc))
