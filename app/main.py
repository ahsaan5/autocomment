from __future__ import annotations

import os
from typing import Any

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from openai import OpenAI
from pydantic import BaseModel

from app.kb import KnowledgeBase

app = FastAPI(title="Facebook Comment Auto-Responder")
kb = KnowledgeBase()

VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN", "dev-verify-token")
PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


class UrlInput(BaseModel):
    url: str


def extract_url_text(url: str) -> str:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.stripped_strings)


def generate_reply(question: str) -> str:
    context = kb.context_for(question)
    if not context:
        return "Thanks for your comment. Could you share more detail so we can help you better?"

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        snippet = context[:280]
        return f"Thanks for reaching out. Based on our info: {snippet}"

    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful customer support assistant for a Facebook page. Keep answers concise and grounded in the provided knowledge base context.",
            },
            {
                "role": "user",
                "content": f"Knowledge base context:\n{context}\n\nComment: {question}",
            },
        ],
        temperature=0.2,
    )
    return completion.choices[0].message.content or "Thanks for your message!"


def post_comment_reply(comment_id: str, message: str) -> None:
    if not PAGE_ACCESS_TOKEN:
        raise RuntimeError("FB_PAGE_ACCESS_TOKEN is not configured")

    endpoint = f"https://graph.facebook.com/v20.0/{comment_id}/comments"
    payload = {"message": message, "access_token": PAGE_ACCESS_TOKEN}
    response = requests.post(endpoint, data=payload, timeout=20)
    response.raise_for_status()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "documents": str(len(kb.documents))}


@app.post("/knowledge/upload-txt")
async def upload_text(file: UploadFile = File(...)) -> dict[str, Any]:
    data = await file.read()
    text = data.decode("utf-8", errors="ignore")
    chunks = kb.add_text(text, source=file.filename or "uploaded-txt")
    return {"chunks_added": chunks, "total_chunks": len(kb.documents)}


@app.post("/knowledge/add-url")
def add_url(payload: UrlInput) -> dict[str, Any]:
    try:
        text = extract_url_text(payload.url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    chunks = kb.add_text(text, source=payload.url)
    return {"chunks_added": chunks, "total_chunks": len(kb.documents)}


@app.get("/webhook")
def verify_webhook(request: Request) -> str:
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge or ""
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def facebook_webhook(payload: dict[str, Any]) -> dict[str, str]:
    if payload.get("object") != "page":
        return {"status": "ignored"}

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if change.get("field") != "feed" or value.get("item") != "comment":
                continue

            comment_id = value.get("comment_id")
            message = value.get("message", "")
            if not comment_id or not message:
                continue

            reply = generate_reply(message)
            try:
                post_comment_reply(comment_id, reply)
            except Exception as exc:  # noqa: BLE001
                print(f"Failed replying to {comment_id}: {exc}")

    return {"status": "processed"}
