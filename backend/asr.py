"""
Speech-to-text using local, open-source OpenAI Whisper.

The model is loaded once and reused across requests (loading it per-request
would be slow and memory-hungry). Model size is configurable via the
WHISPER_MODEL env var: tiny | base | small | medium | large.
"base" is a reasonable default for a demo (fast, decent accuracy).
"""
import os
import whisper

_model = None
_model_name = os.getenv("WHISPER_MODEL", "base")


def get_model():
    global _model
    if _model is None:
        _model = whisper.load_model(_model_name)
    return _model


def transcribe(audio_path: str) -> dict:
    """
    Transcribes an audio file and returns:
      {
        "text": full transcript,
        "segments": [{"start": float, "end": float, "text": str}, ...],
        "duration_seconds": float
      }
    """
    model = get_model()
    result = model.transcribe(audio_path, language="en",verbose=False)

    print("Detected language:", result["language"])
    print(result["text"])

    segments = [
        {
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        }
        for seg in result.get("segments", [])
    ]
    duration = segments[-1]["end"] if segments else 0.0

    return {
        "text": result["text"].strip(),
        "segments": segments,
        "duration_seconds": duration,
    }
