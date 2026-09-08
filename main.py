import os
import asyncio
import json
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware


from liveapiworker import LiveAPIWorker
from languages import languages_json, name_for_code

load_dotenv(override=True)  # .env wins over inherited env (e.g. GOOGLE_CLOUD_LOCATION=global)

# --- Configuration (all overridable via .env) ---
DEFAULT_SOURCE_LANG_CODE = os.getenv("DEFAULT_SOURCE_LANG_CODE", "zh-Hans")
DEFAULT_TARGET_LANG_CODE = os.getenv("DEFAULT_TARGET_LANG_CODE", "en")
DEFAULT_SOURCE_LANG = os.getenv("DEFAULT_SOURCE_LANG") or name_for_code(DEFAULT_SOURCE_LANG_CODE)
DEFAULT_TARGET_LANG = os.getenv("DEFAULT_TARGET_LANG") or name_for_code(DEFAULT_TARGET_LANG_CODE)
DEFAULT_MODE = os.getenv("DEFAULT_MODE", "transcription")

liveapiworker: Optional[LiveAPIWorker] = None
_worker_task: Optional[asyncio.Task] = None


def check_gcloud_auth() -> bool:
    """Check for gcloud application-default credentials (non-blocking).

    Returns True if ADC is present. If not, prints a clear instruction and
    returns False rather than launching an interactive login (which would
    hang the server startup). The UI still boots; the Live API session will
    error until the user authenticates.
    """
    try:
        subprocess.check_output(
            ["gcloud", "auth", "application-default", "print-access-token"],
            stderr=subprocess.STDOUT,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("=" * 70)
        print("  Google Cloud ADC not found. Translation will fail until you run:")
        print("      gcloud auth application-default login")
        print("=" * 70)
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    global liveapiworker, _worker_task
    check_gcloud_auth()

    liveapiworker = LiveAPIWorker(
        DEFAULT_SOURCE_LANG,
        DEFAULT_TARGET_LANG,
        source_language_code=DEFAULT_SOURCE_LANG_CODE,
        target_language_code=DEFAULT_TARGET_LANG_CODE,
        mode=DEFAULT_MODE,
    )

    def _on_worker_done(t):
        if not t.cancelled() and t.exception():
            print(f"[main] CRITICAL: Live API worker crashed: {t.exception()}")

    _worker_task = asyncio.create_task(liveapiworker.run(), name="live-api-worker")
    _worker_task.add_done_callback(_on_worker_done)
    yield
    # Graceful shutdown: cancel the background worker task.
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        await asyncio.gather(_worker_task, return_exceptions=True)


app = FastAPI(lifespan=lifespan)

# --- Google OAuth 2.0 & Session Configuration ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("OAUTH_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("OAUTH_CLIENT_SECRET", "")
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY") or os.getenv("SESSION_SECRET", "change-this-to-a-very-secure-random-key-in-prod-123456")
ALLOWED_HD = os.getenv("ALLOWED_HD", "").strip().lower()

_raw_enable = os.getenv("ENABLE_OAUTH", "")
if _raw_enable:
    ENABLE_OAUTH = _raw_enable.lower() in ("1", "true", "yes", "on")
else:
    # Default to OAuth on Cloud Run (where K_SERVICE is set); allow local dev without OAuth by default
    ENABLE_OAUTH = bool(os.getenv("K_SERVICE") and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

ALLOWED_EMAILS = [
    email.strip().lower()
    for email in os.getenv("ALLOWED_EMAILS", "jerryscy@gmail.com,jerryscy@google.com").split(",")
    if email.strip()
]

def is_allowed_user(email: Optional[str], hd: Optional[str] = None) -> bool:
    if not email:
        return False
    email_clean = email.strip().lower()
    if email_clean in ALLOWED_EMAILS:
        return True
    if ALLOWED_HD:
        if email_clean.endswith(f"@{ALLOWED_HD}"):
            return True
        if hd and hd.strip().lower() == ALLOWED_HD:
            return True
    return False

def _get_redirect_uri(request: Request) -> str:
    if configured := os.getenv("OAUTH_REDIRECT_URI"):
        return configured
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{proto}://{request.headers.get('host')}/callback"

# Enable Starlette's SessionMiddleware for managing signed session cookies (needed only if OAuth is enabled)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY, max_age=86400 * 7) # 7 days session

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/audio-processor.js")
async def get_audio_processor():
    """Direct route for the audio worklet with guaranteed JS MIME type."""
    return FileResponse("static/audio-processor.js", media_type="application/javascript")


@app.get("/login")
async def login(request: Request):
    """Redirect to Google's OAuth 2.0 Consent Screen."""
    if not ENABLE_OAUTH:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    redirect_uri = _get_redirect_uri(request)
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=openid%20email"
        f"&state=auth-state"
    )
    return RedirectResponse(url=auth_url)


@app.get("/auth")
@app.get("/callback")
async def callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """Handle Google OAuth 2.0 callback, exchange code, verify email, and set session."""
    if not ENABLE_OAUTH:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    if error or not code:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error or 'missing authorization code'}")
    
    redirect_uri = _get_redirect_uri(request)
    
    async with httpx.AsyncClient() as client:
        # Exchange authorization code for an access token
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to fetch OAuth token: {token_res.text}")
        
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        
        # Fetch user profile using the access token
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to fetch user info: {user_res.text}")
            
        user_info = user_res.json()
        email = user_info.get("email", "").strip().lower()
        
        # Restrict login to authorized test users or domain
        if not is_allowed_user(email, user_info.get("hd")):
            print(f"[OAuth] Access denied for: {email} (hd: {user_info.get('hd')})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {email} is not authorized for this application."
            )
        
        # Store identity in session
        request.session["email"] = email
        request.session["user_name"] = user_info.get("name", "User")
        print(f"[OAuth] Successfully authenticated: {email}")
        
    return RedirectResponse(url="/")


@app.get("/logout")
async def logout(request: Request):
    """Clear session cookies and redirect to home."""
    if not ENABLE_OAUTH:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    request.session.clear()
    return RedirectResponse(url="/")


@app.get("/config")
async def get_config(request: Request):
    """Expose language list + defaults + mode + model state to the frontend."""
    if ENABLE_OAUTH:
        email = request.session.get("email")
        if not is_allowed_user(email):
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_name = request.session.get("user_name", "User")
    else:
        user_name = None

    current_mode = liveapiworker.mode if liveapiworker else DEFAULT_MODE
    current_model = liveapiworker.model_id if liveapiworker else LiveAPIWorker.TRANSCRIPTION_MODEL_ID
    source_codes = liveapiworker.source_language_codes if liveapiworker else [DEFAULT_SOURCE_LANG_CODE]

    available_models = [
        {
            "id": LiveAPIWorker.TRANSCRIPTION_MODEL_ID,
            "name": "Gemini 3.5 Live Transcribe (Preview)",
            "mode": "transcription",
            "description": "Real-time speech-to-text transcription (Preview)",
        },
        {
            "id": LiveAPIWorker.TRANSLATION_MODEL_ID,
            "name": "Gemini 3.5 Live Translate (Preview)",
            "mode": "translation",
            "description": "Real-time speech-to-speech translation (Preview)",
        },
    ]

    return JSONResponse(
        {
            "languages": languages_json(),
            "default_source_code": DEFAULT_SOURCE_LANG_CODE,
            "default_source_codes": source_codes,
            "default_target_code": DEFAULT_TARGET_LANG_CODE,
            "mode": current_mode,
            "modes": [
                {
                    "id": "transcription",
                    "name": "Live Transcription",
                    "model": LiveAPIWorker.TRANSCRIPTION_MODEL_ID,
                    "description": "Real-time speech-to-text transcription",
                },
                {
                    "id": "translation",
                    "name": "Live Translation",
                    "model": LiveAPIWorker.TRANSLATION_MODEL_ID,
                    "description": "Real-time speech-to-speech translation",
                },
            ],
            "model": current_model,
            "models": available_models,
            "user_name": user_name,
        }
    )


async def _stream_events_to_client(websocket: WebSocket) -> None:
    """Forward events from the worker's event queue to the WebSocket client."""
    while True:
        event = await liveapiworker.event_queue.get()
        try:
            event_type = event["type"]

            if event_type == "audio":
                await websocket.send_bytes(event["data"])

            elif event_type == "data":
                # The uid/seq/type/message/finished data contract.
                await websocket.send_text(
                    json.dumps({"kind": "data", "data": event["payload"]})
                )

            elif event_type == "live_api_status":
                await websocket.send_text(
                    json.dumps({
                        "kind": "status",
                        "live_api_status": {
                            "connected": event.get("connected", False),
                            "state": event.get("state", "disconnected"),
                        },
                    })
                )

            elif event_type == "session_cleared":
                await websocket.send_text(
                    json.dumps({
                        "kind": "session_cleared",
                        "mode": event.get("mode"),
                        "model": event.get("model"),
                        "session_uid": event.get("session_uid"),
                    })
                )

        except Exception as exc:
            print(f"[stream_events] Error sending to client: {exc}")
        finally:
            liveapiworker.event_queue.task_done()


@app.get("/")
async def get(request: Request):
    """Serve the index page."""
    if ENABLE_OAUTH:
        email = request.session.get("email")
        if not is_allowed_user(email):
            print(f"[Root] Redirecting to /login because session email '{email}' is not authorized")
            return RedirectResponse(url="/login")
        print(f"[Root] Serving index page for authorized user: {email}")
    return FileResponse(
        "static/index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Retrieve the user's session and verify authentication if OAuth is enabled
    if ENABLE_OAUTH:
        email = websocket.session.get("email")
        if not is_allowed_user(email):
            print(f"[websocket] Rejecting unauthenticated WebSocket connection for email '{email}'.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await websocket.accept()

    # New browser connection = new client session (fresh uid, seq resets to 1).
    # seq then accumulates across turns and Start/Stop until the next connect.
    liveapiworker.begin_client_session()
    liveapiworker.ensure_connected()

    # Send the current Live API connection state immediately so the client
    # can render the status indicator without waiting for the next change.
    try:
        connected = bool(getattr(liveapiworker, "live_api_connected", False))
        await websocket.send_text(
            json.dumps({
                "kind": "status",
                "live_api_status": {
                    "connected": connected,
                    "state": "connected" if connected else "disconnected",
                },
            })
        )
    except Exception as exc:
        print(f"[websocket] Failed to send initial status: {exc}")

    stream_task = asyncio.create_task(
        _stream_events_to_client(websocket), name="ws-event-stream"
    )

    try:
        while True:
            data = await websocket.receive()

            if data.get("type") == "websocket.disconnect":
                print("Client disconnected")
                break

            if "bytes" in data:
                await liveapiworker.send_audio_data(data["bytes"])

            elif "text" in data:
                message = json.loads(data["text"])
                action = message.get("action")

                if action == "start_session":
                    if ("source_language" in message or "target_language" in message
                          or "source_language_code" in message or "source_language_codes" in message
                          or "target_language_code" in message):
                        source = message.get("source_language", liveapiworker.source_language)
                        target = message.get("target_language", liveapiworker.target_language)
                        source_code = message.get(
                            "source_language_code", liveapiworker.source_language_code
                        )
                        source_codes = message.get("source_language_codes", None)
                        target_code = message.get(
                            "target_language_code", liveapiworker.target_language_code
                        )
                        await liveapiworker.set_language(
                            source, target,
                            source_code=source_code,
                            target_code=target_code,
                            source_codes=source_codes,
                        )
                    await liveapiworker.start_session()
                elif action == "stop_session":
                    await liveapiworker.stop_session()
                elif action == "set_mode":
                    mode = message.get("mode")
                    if mode:
                        await liveapiworker.set_mode(mode)
                        await websocket.send_text(
                            json.dumps({
                                "kind": "mode_updated",
                                "mode": liveapiworker.mode,
                                "model": liveapiworker.model_id,
                                "session_uid": liveapiworker.session_uid,
                            })
                        )
                elif action == "set_model":
                    model = message.get("model") or message.get("model_id")
                    if model:
                        await liveapiworker.set_model(model)
                        await websocket.send_text(
                            json.dumps({
                                "kind": "model_updated",
                                "mode": liveapiworker.mode,
                                "model": liveapiworker.model_id,
                                "session_uid": liveapiworker.session_uid,
                            })
                        )
                elif action == "set_audio_output":
                    liveapiworker.set_audio_output(bool(message.get("enabled", True)))
                elif ("source_language" in message or "target_language" in message
                      or "source_language_code" in message or "source_language_codes" in message
                      or "target_language_code" in message):
                    source = message.get("source_language", liveapiworker.source_language)
                    target = message.get("target_language", liveapiworker.target_language)
                    source_code = message.get(
                        "source_language_code", liveapiworker.source_language_code
                    )
                    source_codes = message.get("source_language_codes", None)
                    target_code = message.get(
                        "target_language_code", liveapiworker.target_language_code
                    )
                    await liveapiworker.set_language(
                        source, target,
                        source_code=source_code,
                        target_code=target_code,
                        source_codes=source_codes,
                    )
                    await websocket.send_text(
                        json.dumps({
                            "kind": "languages_updated",
                            "source_language_codes": liveapiworker.source_language_codes,
                            "target_language_code": liveapiworker.target_language_code,
                            "source_language": liveapiworker.source_language,
                            "target_language": liveapiworker.target_language,
                        })
                    )

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as exc:
        print(f"[websocket] Unexpected error: {exc}")
    finally:
        stream_task.cancel()
        await asyncio.gather(stream_task, return_exceptions=True)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
