"""
Meeting Summarizer — FastAPI backend.

Endpoints:
  POST /api/meetings           Upload an audio file, transcribe + summarize it
  GET  /api/meetings           List all meetings (most recent first)
  GET  /api/meetings/{id}      Get a single meeting
  DELETE /api/meetings/{id}    Delete a meeting

Processing is synchronous for simplicity (fine for a demo / small files).
For production use, move transcription+summarization into a background
task queue (Celery, RQ, arq) and poll /api/meetings/{id} for status.
"""
import json
import os
import shutil
import uuid
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import init_db, get_db, Meeting
from schemas import MeetingResponse
import asr
import summarizer

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".webm", ".ogg", ".flac"}
MAX_FILE_SIZE_MB = 200

app = FastAPI(title="Meeting Summarizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


def _meeting_to_dict(m: Meeting) -> dict:
    return {
        "id": m.id,
        "filename": m.filename,
        "status": m.status,
        "error": m.error,
        "transcript": m.transcript,
        "summary": m.summary,
        "decisions": json.loads(m.decisions) if m.decisions else [],
        "action_items": json.loads(m.action_items) if m.action_items else [],
        "duration_seconds": m.duration_seconds,
        "created_at": m.created_at.isoformat(),
    }


@app.post("/api/meetings", response_model=MeetingResponse)
async def create_meeting(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    meeting_id = str(uuid.uuid4())
    dest_path = UPLOAD_DIR / f"{meeting_id}{ext}"

    with dest_path.open("wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    size_mb = dest_path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(400, f"File too large ({size_mb:.1f}MB). Max {MAX_FILE_SIZE_MB}MB.")

    meeting = Meeting(id=meeting_id, filename=file.filename, status="processing")
    db.add(meeting)
    db.commit()

    try:
        transcription = asr.transcribe(str(dest_path))
        result = summarizer.summarize(transcription["text"])

        meeting.transcript = transcription["text"]
        meeting.duration_seconds = str(transcription["duration_seconds"])
        meeting.summary = result["summary"]
        meeting.decisions = json.dumps(result["decisions"])
        meeting.action_items = json.dumps(result["action_items"])
        meeting.status = "done"
    except Exception as e:  # noqa: BLE001 — surface any failure to the client
        meeting.status = "failed"
        meeting.error = str(e)
    finally:
        db.commit()
        db.refresh(meeting)
        dest_path.unlink(missing_ok=True)  # don't keep raw audio around

    return _meeting_to_dict(meeting)


@app.get("/api/meetings", response_model=list[MeetingResponse])
def list_meetings(db: Session = Depends(get_db)):
    meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).all()
    return [_meeting_to_dict(m) for m in meetings]


@app.get("/api/meetings/{meeting_id}", response_model=MeetingResponse)
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    return _meeting_to_dict(meeting)


@app.delete("/api/meetings/{meeting_id}")
def delete_meeting(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    db.delete(meeting)
    db.commit()
    return {"deleted": True}


# Serve the frontend as static files at /
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
