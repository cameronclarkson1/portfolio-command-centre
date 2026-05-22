"""
sharesight_auth.py — One-time OAuth setup for Sharesight.

Visit these URLs in your browser (with the API running):

  Step 1:  http://localhost:8000/auth/sharesight/start
           → Redirects you to Sharesight to approve access

  Step 2:  (automatic) Sharesight sends you back to /auth/sharesight/callback
           → Tokens are saved to repo/.env automatically

After setup you never need to come back here — tokens auto-refresh.
"""

import os
import requests
from urllib.parse import urlencode
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config.api_keys import SHARESIGHT_CLIENT_ID, SHARESIGHT_CLIENT_SECRET

router = APIRouter()

_TOKEN_URL    = "https://api.sharesight.com/oauth2/token"
_AUTH_URL     = "https://api.sharesight.com/oauth2/authorize"
# Override with SHARESIGHT_REDIRECT_URI in repo/.env when using ngrok
_REDIRECT_URI = os.getenv("SHARESIGHT_REDIRECT_URI", "http://localhost:8000/auth/sharesight/callback")
_TIMEOUT      = 15

# Path to repo/.env
_REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "repo"))
_ENV_PATH = os.path.join(_REPO_DIR, ".env")


def _update_env(key: str, value: str) -> None:
    """Write or update a key in repo/.env without touching other lines."""
    if not os.path.exists(_ENV_PATH):
        with open(_ENV_PATH, "w") as f:
            f.write(f"{key}={value}\n")
        return

    with open(_ENV_PATH) as f:
        lines = f.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}\n")

    with open(_ENV_PATH, "w") as f:
        f.writelines(lines)


@router.get("/start")
def sharesight_start():
    """Redirect the user's browser to the Sharesight OAuth approval page."""
    if not SHARESIGHT_CLIENT_ID:
        return HTMLResponse(
            "<h2>Missing SHARESIGHT_CLIENT_ID</h2>"
            "<p>Add <code>SHARESIGHT_CLIENT_ID=your_id</code> to <code>repo/.env</code> first.</p>",
            status_code=400,
        )

    params = urlencode({
        "response_type": "code",
        "client_id":     SHARESIGHT_CLIENT_ID,
        "redirect_uri":  _REDIRECT_URI,
    })
    return RedirectResponse(url=f"{_AUTH_URL}?{params}")


@router.get("/callback")
def sharesight_callback(request: Request, code: str = None, error: str = None):
    """
    Sharesight redirects here after the user approves access.
    Exchanges the code for tokens and saves them to repo/.env.
    """
    if error or not code:
        return HTMLResponse(
            f"<h2>Sharesight auth failed</h2><p>{error or 'No code received'}</p>",
            status_code=400,
        )

    # Exchange the code for access + refresh tokens
    try:
        resp = requests.post(
            _TOKEN_URL,
            data={
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  _REDIRECT_URI,
                "client_id":     SHARESIGHT_CLIENT_ID,
                "client_secret": SHARESIGHT_CLIENT_SECRET,
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        tokens = resp.json()
    except Exception as e:
        return HTMLResponse(
            f"<h2>Token exchange failed</h2><pre>{e}</pre>",
            status_code=500,
        )

    access_token  = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")

    if not access_token:
        return HTMLResponse(
            "<h2>No access token in response</h2>"
            f"<pre>{tokens}</pre>",
            status_code=500,
        )

    # Save tokens to repo/.env
    _update_env("SHARESIGHT_ACCESS_TOKEN",  access_token)
    _update_env("SHARESIGHT_REFRESH_TOKEN", refresh_token)

    return HTMLResponse("""
    <html>
    <head><title>Sharesight Connected</title></head>
    <body style="font-family:sans-serif; max-width:500px; margin:60px auto; text-align:center;">
      <h2>&#10003; Sharesight connected successfully</h2>
      <p>Your tokens have been saved to <code>repo/.env</code>.</p>
      <p>Restart the API server, then your real portfolio holdings
         will load automatically at <code>/api/portfolio</code>.</p>
    </body>
    </html>
    """)
