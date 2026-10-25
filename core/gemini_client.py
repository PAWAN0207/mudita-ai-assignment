
"""Shared Gemini API client for the Mudita AI applications."""

import os
import random
import time

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


# ---------------------------------------------------------
# Project configuration
# ---------------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

ENV_FILE = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(ENV_FILE)


def get_secret(name: str, default=None):
    """Read configuration from environment or Streamlit Secrets.

    Environment variables take priority over Streamlit Secrets.
    """

    value = os.getenv(name)

    if value:
        return value

    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


API_KEY = get_secret("GEMINI_API_KEY")
MODEL_NAME = get_secret("GEMINI_MODEL", "gemini-3.8-flash")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Configure it in "
        "Streamlit Cloud Secrets or the local .env file."
    )


# ---------------------------------------------------------
# Client and retry configuration
# ---------------------------------------------------------

# Disable SDK retries so the application controls retry attempts.
client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=1,
        )
    ),
)

# Maximum total calls per generate_response() invocation.
MAX_ATTEMPTS = 3

# Wait approximately 2, then 4 seconds, plus small random jitter.
INITIAL_RETRY_DELAY = 2

RETRYABLE_STATUS_CODES = {408, 500, 502, 503, 504}


# ---------------------------------------------------------
# Gemini response generation
# ---------------------------------------------------------

def generate_response(prompt: str, json_mode: bool = False) -> str:
    """Generate text using Gemini with controlled transient-error retries.

    Retries temporary server errors and request timeouts.
    Does not retry quota, authentication, permission, or invalid-request
    errors. Each invocation makes at most MAX_ATTEMPTS API calls.
    """

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    config = None

    if json_mode:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
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
                    "Gemini returned an empty response."
                )

            return response_text.strip()

        except errors.APIError as exc:
            status_code = getattr(exc, "code", None)

            # Retry only temporary service/network-related HTTP errors.
            if (
                status_code in RETRYABLE_STATUS_CODES
                and attempt < MAX_ATTEMPTS
            ):
                delay = (
                    INITIAL_RETRY_DELAY * (2 ** (attempt - 1))
                    + random.uniform(0, 0.5)
                )

                print(
                    f"Temporary Gemini API error ({status_code}). "
                    f"Retrying in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{MAX_ATTEMPTS})."
                )

                time.sleep(delay)
                continue

            if status_code == 429:
                raise RuntimeError(
                    "Gemini API quota or rate limit exceeded. "
                    "Check the API project's usage, quota, and billing."
                ) from exc

            if status_code == 503:
                raise RuntimeError(
                    "Gemini is temporarily unavailable after retries. "
                    "Please wait briefly before trying again."
                ) from exc

            raise RuntimeError(
                f"Gemini API error (code={status_code}): {exc}"
            ) from exc

    raise RuntimeError(
        "Gemini request failed after multiple attempts."
    )


# ---------------------------------------------------------
# Local smoke test
# ---------------------------------------------------------

if __name__ == "__main__":
    try:
        result = generate_response(
            "Reply with a short greeting.",
        )

        print("Gemini API connection successful.")
        print("Model:", MODEL_NAME)
        print("Response:", result)

    except Exception as exc:
        print("Gemini API test failed:", exc)

