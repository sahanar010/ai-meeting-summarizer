import json
import os
import re
import google.generativeai as genai

MODEL = "gemini-3.6-flash"

SYSTEM_PROMPT = """
You are an assistant that turns raw meeting transcripts
into action-oriented summaries for busy teams.

Respond with ONLY a JSON object matching exactly this shape:

{
  "summary": "2-4 sentence summary",
  "decisions": [],
  "action_items": [
    {
      "task": "",
      "owner": "",
      "due": null
    }
  ]
}

Never include markdown.
Never invent information.
"""

USER_PROMPT_TEMPLATE = """
Summarize this meeting transcript.

Transcript:

{transcript}
"""

def _client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in .env")

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL)

def _extract_json(text):
    cleaned = re.sub(r"^```json|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)

def summarize(transcript):
    if not transcript.strip():
        return {
            "summary": "",
            "decisions": [],
            "action_items": []
        }

    model = _client()

    response = model.generate_content(
        SYSTEM_PROMPT + "\n\n" + USER_PROMPT_TEMPLATE.format(transcript=transcript)
    )

    raw = response.text

    try:
        parsed = _extract_json(raw)
    except Exception:
        parsed = {
            "summary": raw.strip(),
            "decisions": [],
            "action_items": []
        }

    parsed.setdefault("summary", "")
    parsed.setdefault("decisions", [])
    parsed.setdefault("action_items", [])

    return parsed