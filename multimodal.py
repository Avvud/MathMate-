"""
multimodal.py — Multimodal Input Processing for MathMate v2.1
Handles: Voice (Groq Whisper STT), Image (Groq Vision LLM)
Vision failures → friendly error message, never silent text fallback.
"""

import os
import base64
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

WHISPER_MODEL = "whisper-large-v3"
VISION_MODEL  = "meta-llama/llama-4-scout-17b-16e-instruct"


def _client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set in .env")
    return Groq(api_key=api_key)


# ──────────────────────────────────────────────────────────
#  VOICE → TEXT
# ──────────────────────────────────────────────────────────

def voice_to_text(audio_bytes: bytes, filename: str = "audio.wav") -> tuple[str, bool]:
    """
    Transcribe audio using Groq Whisper.
    Returns (transcript, success).
    On failure returns (friendly_error_message, False).
    """
    try:
        resp = _client().audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=(filename, audio_bytes),
            response_format="text",
        )
        transcript = (resp if isinstance(resp, str) else resp.text).strip()
        if not transcript:
            return "I couldn't catch that — the audio seemed empty. Try speaking a bit louder and closer to the mic.", False
        return transcript, True

    except Exception as e:
        err = str(e)
        if "413" in err or "too large" in err.lower():
            return "⚠️ That audio clip is too large (max ~25 MB). Please try a shorter recording.", False
        if "rate" in err.lower() or "429" in err:
            return "⚠️ The transcription service is busy right now. Wait a moment and try again.", False
        return f"⚠️ Voice transcription failed — please try again or type your question instead.\n\n_(Details: {err})_", False


# ──────────────────────────────────────────────────────────
#  IMAGE → DESCRIPTION
# ──────────────────────────────────────────────────────────

def image_to_description(image_bytes: bytes, mime_type: str = "image/jpeg") -> tuple[str, bool]:
    """
    Describe all mathematical content in an image using Groq Vision LLM.
    Returns (description, success).
    On failure returns (friendly_error_message, False) — never a silent fallback.
    """
    try:
        b64      = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64}"

        resp = _client().chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Carefully describe ALL mathematical content visible in this image. "
                            "Include every equation, expression, number, variable, working step, "
                            "diagram label, and written text exactly as it appears. "
                            "Preserve the order of steps. Do NOT interpret or solve — only describe what is written."
                        ),
                    },
                ],
            }],
            max_tokens=1024,
        )

        description = resp.choices[0].message.content.strip()
        if not description:
            return (
                "⚠️ I couldn't read anything from that image. "
                "Please make sure it's clear, well-lit, and shows the full working. "
                "You can also type out what you wrote instead.",
                False,
            )
        return description, True

    except Exception as e:
        err = str(e)
        if "413" in err or "too large" in err.lower():
            return (
                "⚠️ That image is too large to process. "
                "Please compress it or take a closer, cropped photo and try again.",
                False,
            )
        if "unsupported" in err.lower() or "format" in err.lower():
            return (
                "⚠️ That image format isn't supported. Please use JPG, PNG, or WEBP.",
                False,
            )
        if "rate" in err.lower() or "429" in err:
            return (
                "⚠️ The image analysis service is busy. Please wait a moment and try again.",
                False,
            )
        return (
            "⚠️ Image analysis failed. Please try again, or describe your working in the text box below.\n\n"
            f"_(Technical details: {err})_",
            False,
        )


# ──────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────

def detect_image_type(description: str) -> str:
    """
    Heuristically classify an image as student handwriting or a textbook page.
    Returns 'IMAGE_HANDWRITTEN' or 'IMAGE_TEXTBOOK'.
    """
    textbook_signals = [
        "printed", "textbook", "exercise", "ncert", "page number",
        "typed text", "diagram", "figure", "solved example",
        "definition", "theorem", "note:", "solution:", "answer:",
    ]
    hits = sum(1 for s in textbook_signals if s in description.lower())
    return "IMAGE_TEXTBOOK" if hits >= 2 else "IMAGE_HANDWRITTEN"


def mime_from_filename(filename: str) -> str:
    """Infer MIME type from uploaded image filename."""
    ext = filename.rsplit(".", 1)[-1].lower()
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
    }.get(ext, "image/jpeg")
