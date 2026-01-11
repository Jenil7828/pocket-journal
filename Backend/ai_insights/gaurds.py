import os

def setup_gemini_env():
    """
    Sets Gemini credentials safely.
    Call this ONLY at runtime, never at import time.
    """
    # gemini_json = os.getenv("GEMINI_CREDENTIALS_PATH")
    # if gemini_json:
    #     os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gemini_json

    return {
        "api_key": os.getenv("GEMINI_API_KEY"),
        "enabled": bool(os.getenv("GEMINI_API_KEY"))
    }
