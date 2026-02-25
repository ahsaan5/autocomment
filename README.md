# Facebook Comment Auto-Responder

This app receives Facebook Page comment webhooks and auto-replies using a knowledge base you provide from:

- `.txt` files
- website URLs

## Features

- FastAPI webhook server for Facebook Page comments
- Upload knowledge from text file (`/knowledge/upload-txt`)
- Ingest knowledge from website URL (`/knowledge/add-url`)
- Simple built-in lexical retrieval for relevant context
- Optional OpenAI-powered response generation (fallback to template when no API key)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Environment variables

- `FB_VERIFY_TOKEN` - token used by Facebook webhook verification
- `FB_PAGE_ACCESS_TOKEN` - page access token used to post replies
- `OPENAI_API_KEY` - optional, enables better reply generation
- `OPENAI_MODEL` - optional model name (default: `gpt-4o-mini`)

## API

### 1) Upload text file knowledge

`POST /knowledge/upload-txt` (multipart file field: `file`)

### 2) Add knowledge from URL

`POST /knowledge/add-url`

```json
{ "url": "https://example.com/faq" }
```

### 3) Webhook verification

`GET /webhook?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...`

### 4) Facebook webhook receiver

`POST /webhook`

The app listens for `feed` changes where `item == comment`, creates a reply from your KB, and posts back using the Graph API.


## Testing

### Automated tests

```bash
python -m pytest -q
```

### Manual local API test

1. Start the app:

```bash
uvicorn app.main:app --reload --port 8000
```

2. Upload a TXT knowledge file:

```bash
curl -X POST http://127.0.0.1:8000/knowledge/upload-txt \
  -F "file=@faq.txt"
```

3. Add website knowledge:

```bash
curl -X POST http://127.0.0.1:8000/knowledge/add-url \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/faq"}'
```

4. Simulate a Facebook comment webhook event:

```bash
curl -X POST http://127.0.0.1:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "object":"page",
    "entry":[{
      "changes":[{
        "field":"feed",
        "value":{
          "item":"comment",
          "comment_id":"123_456",
          "message":"How long is shipping?"
        }
      }]
    }]
  }'
```

If `FB_PAGE_ACCESS_TOKEN` is not set, webhook processing still runs but posting to Facebook will fail with a logged error (expected for local dry-runs).

## Facebook setup notes

1. Create a Meta app and add the **Webhooks** product.
2. Subscribe your Page to `feed` events.
3. Set callback URL to your deployed `/webhook` endpoint.
4. Use the same `FB_VERIFY_TOKEN` value in both app settings and env var.
5. Generate a long-lived Page access token and set `FB_PAGE_ACCESS_TOKEN`.

## Limitations / next steps

- Add dedup logic to avoid double-replies
- Add moderation filters
- Replace lexical retrieval with embeddings + vector DB for higher quality
- Add UI dashboard for KB upload & logs
