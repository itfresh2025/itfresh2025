"""Text-to-Speech service using gTTS + ffmpeg."""

import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def text_to_ogg(text: str, lang: str = "ru") -> bytes:
    """Convert text to OGG Opus voice message for Telegram."""
    from gtts import gTTS

    # Ограничить длину
    if len(text) > 3000:
        text = text[:3000] + "... продолжение в тексте выше."

    with tempfile.TemporaryDirectory() as tmpdir:
        mp3_path = os.path.join(tmpdir, "speech.mp3")
        ogg_path = os.path.join(tmpdir, "speech.ogg")

        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(mp3_path)

        subprocess.run(
            ["ffmpeg", "-i", mp3_path,
             "-c:a", "libopus", "-b:a", "64k",
             "-ar", "48000", ogg_path, "-y", "-loglevel", "error"],
            check=True,
        )

        with open(ogg_path, "rb") as f:
            return f.read()
