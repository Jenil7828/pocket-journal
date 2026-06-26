"""
Secrets loader supporting local (.env) and AWS Secrets Manager modes.

Usage:
    from utils.secrets_loader import load_application_secrets
    load_application_secrets()

Behavior:
- If AWS_SECRET_NAME is set, fetch secret from AWS Secrets Manager and inject keys into os.environ.
- Otherwise, load local .env for local-only development compatibility.

This module never logs secret values.
"""
import os
import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# List of supported secret keys (present in the secret JSON stored in AWS Secrets Manager)
SUPPORTED_SECRETS = [
    "FIREBASE_CREDENTIALS_JSON",
    "FIREBASE_WEB_API_KEY",
    "TMDB_API_KEY",
    "SONG_ID",
    "SONG_SECRET",
    "GEMINI_API_KEY",
    "CRON_SECRET",
]

# Keys that are required for application to run in production
# FIREBASE_CREDENTIALS_JSON must be present for Firebase initialization to succeed.
REQUIRED_KEYS = ["FIREBASE_CREDENTIALS_JSON"]


def _load_from_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        logger.warning("python-dotenv not installed; skipping .env loading")
        return
    load_dotenv()
    logger.info("Secrets source: Local .env")


def _fetch_secret_from_aws(secret_name: str) -> Dict[str, str]:
    # Import boto3 lazily to avoid adding it as a hard dependency for non-AWS runs
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except Exception as e:
        raise RuntimeError("boto3 is required for AWS secrets loading but is not installed") from e

    client = boto3.client("secretsmanager")
    try:
        resp = client.get_secret_value(SecretId=secret_name)
    except Exception as e:
        # Fail fast with descriptive message
        raise RuntimeError(f"Failed to retrieve secret '{secret_name}' from AWS Secrets Manager: {e}") from e

    secret_str = resp.get("SecretString")
    if secret_str is None:
        # Binary secret not supported by this loader
        raise RuntimeError(f"Secret '{secret_name}' does not contain a SecretString payload")

    try:
        secret_obj = json.loads(secret_str)
    except Exception as e:
        raise RuntimeError(f"Secret '{secret_name}' contains invalid JSON: {e}") from e

    if not isinstance(secret_obj, dict):
        raise RuntimeError(f"Secret '{secret_name}' JSON must be an object/dict of key/value pairs")

    return secret_obj


def _inject_secrets_into_env(secret_obj: Dict[str, str]) -> None:
    # Only inject supported keys to avoid accidental pollution
    for key in SUPPORTED_SECRETS:
        if key in secret_obj:
            value = secret_obj[key]
            # Coerce non-string values to string
            if value is None:
                # Ensure we set an empty string rather than 'None'
                value = ""
            else:
                value = str(value)
            os.environ[key] = value
        else:
            # Not present — leave absent; required keys are checked separately
            continue


def load_application_secrets() -> None:
    """Load application secrets from AWS (preferred) or local .env fallback.

    This function logs which secrets source is used but never logs secret values.
    It raises RuntimeError on fatal errors when AWS_SECRET_NAME is set and AWS
    retrieval or secret validation fails.
    """
    secret_name = (os.environ.get("AWS_SECRET_NAME") or "").strip()
    if not secret_name:
        _load_from_dotenv()
        return

    logger.info("Secrets source: AWS Secrets Manager (secret=%s)", secret_name)

    secret_obj = _fetch_secret_from_aws(secret_name)

    # Validate required keys
    missing_required = [k for k in REQUIRED_KEYS if k not in secret_obj]
    if missing_required:
        raise RuntimeError(f"Secrets Manager secret '{secret_name}' is missing required keys: {missing_required}")

    # Inject supported secrets into environment
    _inject_secrets_into_env(secret_obj)

    # Warn about any unknown keys (do not fail) to aid debugging
    unknown_keys = [k for k in secret_obj.keys() if k not in SUPPORTED_SECRETS]
    if unknown_keys:
        logger.debug("Secrets Manager secret contains additional keys (ignored): %s", unknown_keys)

    # Log a succinct success message (no values)
    logger.info("Secrets source: AWS Secrets Manager")

