# main.py
# FastAPI app that exposes:
# - POST /slack/command  (Slack slash command receiver)
# - GET  /admin          (simple admin page to view recent logs)

import os
import hmac
import hashlib
import time
from fastapi import FastAPI, Request, Header, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader
from slugify import slugify  # not required; but optional for IDs
from db import log_entry, fetch_recent
from rag_pipeline import query_kg_and_answer

app = FastAPI()

SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

# Basic Slack request verification
def verify_slack_request(body: bytes, timestamp: str, signature: str) -> bool:
    """
    Verify Slack request using signing secret.
    """
    if not SLACK_SIGNING_SECRET:
        # If secret not set, skip verification (development)
        return True
    # Reject if too old
    if abs(time.time() - float(timestamp)) > 60 * 5:
        return False
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    my_sig = "v0=" + hmac.new(SLACK_SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(my_sig, signature)

@app.post("/slack/command")
async def slack_command(request: Request, x_slack_signature: str = Header(None), x_slack_request_timestamp: str = Header(None)):
    """
    Receives Slack slash command payload (application/x-www-form-urlencoded).
    Slack sends fields including 'user_id', 'text', 'command', etc.
    """
    body = await request.body()
    # verify Slack signature
    if not verify_slack_request(body, x_slack_request_timestamp, x_slack_signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")
    form = await request.form()
    user_id = form.get("user_id")
    text = form.get("text") or ""  # the user's query
    # Immediately ack with a simple response to Slack (short)
    # We will return an "in-channel" response with typing shown by Slack (or you can use delayed responses with response_url)
    # For now: synchronous quick answer
    try:
        result = query_kg_and_answer(text, k=4)
        answer = result["answer"]
        sources = result["sources"]
        # build Slack-friendly blocks (simple)
        attachments = {
            "response_type": "in_channel",
            "text": answer + "\n\nSources:\n" + "\n".join([f"- {s['id']} : {s['title']}" for s in sources])
        }
        # Log to SQLite
        log_entry(user_id=user_id, command_text=text, response_text=answer, sources=sources)
        return JSONResponse(content=attachments)
    except Exception as e:
        # log error minimally
        log_entry(user_id=user_id, command_text=text, response_text=f"ERROR: {str(e)}", sources=[])
        raise HTTPException(status_code=500, detail=str(e))

# admin page to view recent logs
env = Environment(loader=FileSystemLoader("templates"))

@app.get("/admin", response_class=HTMLResponse)
def admin_view():
    logs = fetch_recent(200)
    template = env.get_template("admin.html")
    return template.render(logs=logs)
