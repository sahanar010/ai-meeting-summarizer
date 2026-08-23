# Meeting Summarizer

Upload a meeting recording, get back a transcript, a plain-language summary,
the key decisions made, and a clean list of action items — each with an
owner and due date when the conversation makes that clear.

## How it works

```
audio file → Whisper (local ASR) → transcript → Claude → summary + decisions + action items
```

1. **Transcription** — [OpenAI Whisper](https://github.com/openai/whisper) runs
   locally (no audio ever leaves your machine for this step).
2. **Summarization** — the transcript is sent to Claude with a prompt that asks
   for a structured JSON response (summary / decisions / action items).
3. **Storage** — results are saved to a local SQLite database (`meetings.db`)
   so past meetings can be revisited.

## Project structure

```
meeting-summarizer/
├── backend/
│   ├── main.py          # FastAPI app & routes
│   ├── asr.py            # Whisper transcription
│   ├── summarizer.py      # Claude prompt + call
│   ├── database.py         # SQLite models
│   ├── schemas.py          # Pydantic response models
│   └── requirements.txt
├── frontend/
│   └── index.html         # Single-page upload + results UI
├── uploads/                # Temp storage during processing (auto-cleared)
├── .env.example
└── README.md
```

## Setup

### 1. Prerequisites

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) installed and on your PATH
  (Whisper needs it to decode audio)
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: [download a build](https://www.gyan.dev/ffmpeg/builds/) and add it to PATH
- An [Anthropic API key](https://console.anthropic.com/)

### 2. Install dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

The first run of `openai-whisper` will download the selected model
(~150MB for `base`) — this needs internet access once, then it's cached.

### 3. Configure environment variables

```bash
cp .env.example .env
# then edit .env and paste in your ANTHROPIC_API_KEY
```

### 4. Run the server

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** — the frontend is served directly from the backend.

## API reference

| Method | Endpoint                | Description                                  |
|--------|--------------------------|-----------------------------------------------|
| POST   | `/api/meetings`          | Upload an audio file; returns full result     |
| GET    | `/api/meetings`          | List all past meetings (most recent first)     |
| GET    | `/api/meetings/{id}`     | Fetch a single meeting                          |
| DELETE | `/api/meetings/{id}`     | Delete a meeting                                 |

Example with `curl`:

```bash
curl -X POST http://localhost:8000/api/meetings \
  -F "file=@sample_meeting.mp3"
```

Response shape:

```json
{
  "id": "a1b2c3...",
  "filename": "sample_meeting.mp3",
  "status": "done",
  "transcript": "...",
  "summary": "The team agreed to ship the v2 API by Friday...",
  "decisions": ["Ship v2 API by Friday", "Use Postgres instead of Mongo"],
  "action_items": [
    {"task": "Write migration script", "owner": "Priya", "due": "Thursday"},
    {"task": "Update API docs", "owner": "Unassigned", "due": null}
  ],
  "duration_seconds": "612.4",
  "created_at": "2026-08-23T10:15:00"
}
```

## Design notes / trade-offs

- **Synchronous processing**: for a demo, the upload endpoint blocks until
  transcription + summarization finish. For production or longer recordings,
  move this into a background task queue (Celery/RQ/arq) and let the client
  poll `GET /api/meetings/{id}` for status.
- **Model size**: `WHISPER_MODEL=base` balances speed and accuracy for a demo.
  Switch to `small` or `medium` for better accuracy on noisy/accented audio.
- **Privacy**: raw audio files are deleted from disk immediately after
  transcription — only the text transcript and derived summary are persisted.

## Evaluation checklist (per assignment brief)

- [x] ASR API integration — local Whisper
- [x] Backend to store & process data — FastAPI + SQLite
- [x] LLM for summary generation — Claude, structured JSON output
- [x] Optional frontend — upload + view summary
- [ ] Demo video — record a 2–3 min walkthrough before submitting

## License

MIT
