
import os

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
MODEL_NAME = get_secret("GEMINI_MODEL", "gemini-2.5-flash")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. "
        "Set it in your local .env file or Streamlit Cloud Secrets."
    )

# Initialize Gemini client
client = genai.Client(api_key=API_KEY)


def generate_response(prompt: str, json_mode: bool = False) -> str:
    """
    Generate a response using the Gemini API.
    Supports both normal text and JSON output.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    config = None

    if json_mode:
        config = types.GenerateContentConfig(
            response_mime_type="application/json"
        )

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
        raise RuntimeError(
            f"Gemini API error (code={exc.code}): {exc.message}"
        ) from exc


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
