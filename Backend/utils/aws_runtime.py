import logging
import os
from typing import Optional


logger = logging.getLogger(__name__)


def _deployment_environment() -> str:
    return os.environ.get("DEPLOYMENT_ENV", "local").strip().lower()


def resolve_runtime_region() -> Optional[str]:
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if region:
        return region.strip()
    return None


def inspect_aws_identity() -> dict:
    """
    Resolve AWS identity context without exposing credentials.
    Uses boto3 default provider chain only.
    """
    import boto3

    session = boto3.Session(region_name=resolve_runtime_region())
    credentials = session.get_credentials()
    frozen = credentials.get_frozen_credentials() if credentials else None
    credential_source = getattr(credentials, "method", None) if credentials else "unresolved"
    region = session.region_name or resolve_runtime_region()

    sts = session.client("sts")
    caller = sts.get_caller_identity()

    # Access key id is intentionally not logged/returned.
    return {
        "deployment_env": _deployment_environment(),
        "region": region or "unset",
        "credential_source": credential_source or "unknown",
        "caller_arn": caller.get("Arn", "unknown"),
        "caller_account": caller.get("Account", "unknown"),
        "credentials_resolved": frozen is not None,
    }


def log_aws_startup_context() -> dict:
    context = inspect_aws_identity()
    logger.info(
        "AWS startup context: env=%s region=%s credential_source=%s caller_arn=%s",
        context["deployment_env"],
        context["region"],
        context["credential_source"],
        context["caller_arn"],
    )
    return context


def validate_aws_startup_access(
    required_secret_name: Optional[str],
    required_model_bucket: Optional[str],
    model_source: Optional[str],
) -> None:
    """
    Validate required AWS capabilities at startup and fail fast on permission/config errors.
    """
    import boto3

    session = boto3.Session(region_name=resolve_runtime_region())

    if required_secret_name:
        sm = session.client("secretsmanager")
        sm.describe_secret(SecretId=required_secret_name)
        logger.info("AWS startup validation: Secrets Manager access OK for secret=%s", required_secret_name)

    if model_source == "s3":
        if not required_model_bucket:
            raise RuntimeError("MODEL_SOURCE=s3 requires MODEL_S3_BUCKET to be set")
        s3 = session.client("s3")
        s3.head_bucket(Bucket=required_model_bucket)
        logger.info("AWS startup validation: S3 access OK for bucket=%s", required_model_bucket)
