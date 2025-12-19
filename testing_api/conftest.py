import os
import time
import logging
import pytest
import requests
from typing import Optional
from dotenv import load_dotenv
from datetime import datetime, timezone
load_dotenv()

TEST_LOG_LEVEL = os.getenv("TEST_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=TEST_LOG_LEVEL, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("testing_api.conftest")

RESULTS = []
def _now_ms():
    return int(time.time() * 1000)


def record_result(test_name: str, endpoint: str, method: str, status_code: int, passed: bool, response_time_ms: int, error: Optional[str], request_body: Optional[dict] = None, expected: Optional[str] = None, actual: Optional[str] = None):
    RESULTS.append({
        "Test Name": test_name,
        "Endpoint": endpoint,
        "Method": method,
        "Status Code": status_code,
        "Result": "PASS" if passed else "FAIL",
        "Response Time (ms)": response_time_ms,
        "Error": error or "",
        "Request": (str(request_body)[:500] if request_body is not None else ""),
        "Expected": expected or "",
        "Actual": (actual or "")[:1000],
    })


@pytest.fixture(scope="session")
def base_url():
    val = os.getenv("TEST_API_BASE_URL", "http://127.0.0.1:5000")
    logger.info("Using TEST_API_BASE_URL=%s", val)
    return val


@pytest.fixture(scope="session")
def firebase_token():
    """
    Create an ID token using the Firebase service account credentials.
    Requires environment variables:
      - FIREBASE_CREDENTIALS_PATH : path to service account JSON
      - FIREBASE_WEB_API_KEY : Web API key to exchange custom token

    Returns an ID token string to use in Authorization header.
    """
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    web_api_key = os.getenv("FIREBASE_WEB_API_KEY")
    if not cred_path or not web_api_key:
        pytest.skip("FIREBASE_CREDENTIALS_PATH and FIREBASE_WEB_API_KEY must be set to run auth tests")

    try:
        import firebase_admin
        from firebase_admin import credentials, auth
    except Exception as e:
        logger.warning("firebase_admin not available: %s", e)
        pytest.skip(f"firebase_admin not available: {e}")

    # Initialize admin SDK for token creation
    try:
        firebase_admin.get_app()
    except ValueError:
        logger.info("Initializing firebase_admin SDK using %s", cred_path)
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

    # Create a custom token for a test UID and exchange it for an ID token via REST
    test_uid = os.getenv("TEST_UID", "test-suite-user")
    logger.info("Creating custom token for TEST_UID=%s", test_uid)
    custom_token = auth.create_custom_token(test_uid).decode("utf-8")

    # Exchange custom token for ID token using the Identity Toolkit REST API
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={web_api_key}"
    payload = {"token": custom_token, "returnSecureToken": True}
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    data = r.json()
    id_token = data.get("idToken")
    if not id_token:
        logger.error("Failed to obtain ID token from Firebase response: %s", data)
        raise RuntimeError("Failed to obtain ID token from Firebase")

    # Small delay to avoid "token used too early" errors caused by clock skew
    delay = float(os.getenv("TEST_TOKEN_DELAY_SECONDS", "1"))
    if delay > 0:
        logger.debug("Sleeping %ss to avoid token-timing issues", delay)
        time.sleep(delay)

    logger.info("Obtained ID token for TEST_UID=%s (token not logged)", test_uid)
    return id_token


@pytest.fixture(scope="session", autouse=True)
def create_today_entry(base_url, firebase_token):
    """
    Ensure there's a journal entry for today for the test UID. This runs once per session
    before any tests and does not depend on test execution order.

    Uses the session token to POST to /process_entry and retries a few times if needed.
    """
    headers = {"Authorization": f"Bearer {firebase_token}"}
    url = base_url.rstrip("/") + "/process_entry"
    today = datetime.now(timezone.utc).isoformat()
    payload = {
        "entry_text": "Test setup entry for API tests.",
        "timestamp": today,
    }

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=20)
            if 200 <= r.status_code < 300:
                logger.info("Session setup: created today's entry (attempt %s)", attempt)
                return True
            # If token used too early or auth issues, wait and retry
            if r.status_code == 401:
                logger.debug("Session setup attempt %s got 401 - retrying", attempt)
                time.sleep(1)
        except requests.RequestException as e:
            logger.debug("Session setup attempt %s request exception: %s", attempt, e)
            time.sleep(1)

    # If we reach here, setup didn't succeed. Tests may still run but likely fail.
    logger.error("Failed to create a session test entry after %s attempts", max_attempts)
    pytest.skip("Failed to create a session test entry; skipping tests that require data")


@pytest.fixture(scope="session")
def auth_header(firebase_token):
    return {"Authorization": f"Bearer {firebase_token}"}


@pytest.fixture
def api_client(base_url, auth_header, request):
    """
    Returns a helper function to make API calls and automatically record results.

    Usage:
      resp = api_client(method="GET", path="/entries", expected_status=200)
    """

    def do_request(method: str, path: str, *, headers: Optional[dict] = None, json: Optional[dict] = None, params: Optional[dict] = None, expected_status: Optional[int] = None, expected_desc: Optional[str] = None, use_auth: bool = True):
        url = base_url.rstrip("/") + path
        hdrs = {} if headers is None else dict(headers)
        if use_auth:
            hdrs.update(auth_header)
        start = _now_ms()
        r = requests.request(method, url, headers=hdrs, json=json, params=params, timeout=30)
        elapsed = _now_ms() - start
        passed = True
        error = None
        if expected_status is not None:
            passed = (r.status_code == expected_status)
            if not passed:
                error = r.text[:1000]
                logger.warning("Request %s %s expected %s got %s", method, path, expected_status, r.status_code)

        # Log a concise high-level summary (do not log full response bodies)
        logger.debug("Request %s %s finished: status=%s time=%sms", method, path, r.status_code, elapsed)

        # Record test result (test node name available via pytest request)
        test_name = request.node.name
        actual_snippet = r.text[:1000]
        record_result(test_name, path, method, r.status_code, passed, elapsed, error, request_body=json, expected=expected_desc, actual=actual_snippet)
        return r

    return do_request


def pytest_sessionfinish(session, exitstatus):
    """Write an Excel report with test results at session end."""
    try:
        from openpyxl import Workbook
    except Exception:
        # If openpyxl not available, skip report generation
        return

    if not RESULTS:
        return

    wb = Workbook()
    ws = wb.active
    headers = ["Test Name", "Endpoint", "Method", "Status Code", "Result", "Response Time (ms)", "Error", "Request", "Expected", "Actual"]
    ws.append(headers)
    for row in RESULTS:
        ws.append([row.get(h, "") for h in headers])

    out_dir = os.getenv("TEST_REPORT_DIR", os.getcwd())
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, os.getenv("TEST_REPORT_NAME", "api_test_report.xlsx"))
    wb.save(out_path)
    session.config._report_path = out_path
