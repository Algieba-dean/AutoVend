"""
TTS (Text-to-Speech) service using edge-tts.

Edge-TTS uses Microsoft Edge's free online TTS service.
No API key required. Supports high-quality neural voices for 40+ languages.

Features:
- Chinese (zh-CN) and English (en-US) neural voices
- Configurable voice, rate, volume, pitch
- Async synthesis to bytes or file
- Streaming synthesis support
"""

import asyncio
import io
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import edge_tts

logger = logging.getLogger(__name__)

# High-quality Chinese/English neural voices
VOICE_ZH_FEMALE = "zh-CN-XiaoxiaoNeural"
VOICE_ZH_MALE = "zh-CN-YunxiNeural"
VOICE_EN_FEMALE = "en-US-AriaNeural"
VOICE_EN_MALE = "en-US-GuyNeural"

DEFAULT_VOICE = VOICE_ZH_FEMALE
DEFAULT_RATE = "+0%"
DEFAULT_VOLUME = "+0%"
DEFAULT_PITCH = "+0Hz"


@dataclass
class TTSResult:
    """Result of a TTS synthesis operation."""

    audio_bytes: bytes
    audio_format: str = "mp3"
    text: str = ""
    voice: str = ""
    duration_estimate_ms: float = 0.0
    processing_time_ms: float = 0.0


class EdgeTTSService:
    """
    Text-to-speech service using Microsoft Edge TTS (free, no API key).

    Usage::

        tts = EdgeTTSService()
        result = tts.synthesize("你好，欢迎来到AutoVend！")
        with open("output.mp3", "wb") as f:
            f.write(result.audio_bytes)

        # Or save directly
        tts.synthesize_to_file("Hello!", "output.mp3")
    """

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        rate: str = DEFAULT_RATE,
        volume: str = DEFAULT_VOLUME,
        pitch: str = DEFAULT_PITCH,
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch

    def synthesize(self, text: str, voice: Optional[str] = None) -> TTSResult:
        """
        Synthesize text to audio bytes (synchronous wrapper).

        Args:
            text: Text to synthesize.
            voice: Override voice. If None, uses default.

        Returns:
            TTSResult with MP3 audio bytes.
        """
        return (
            asyncio.get_event_loop().run_until_complete(self.synthesize_async(text, voice))
            if asyncio.get_event_loop().is_running()
            else asyncio.run(self.synthesize_async(text, voice))
        )

    async def synthesize_async(
        self,
        text: str,
        voice: Optional[str] = None,
    ) -> TTSResult:
        """
        Synthesize text to audio bytes (async).

        Args:
            text: Text to synthesize.
            voice: Override voice.

        Returns:
            TTSResult with MP3 audio bytes.
        """
        if not text or not text.strip():
            return TTSResult(
                audio_bytes=b"",
                text=text,
                voice=voice or self.voice,
            )

        selected_voice = voice or self._detect_voice(text)
        start_time = time.time()

        communicate = edge_tts.Communicate(
            text=text,
            voice=selected_voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )

        audio_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])

        audio_bytes = audio_buffer.getvalue()
        processing_time = (time.time() - start_time) * 1000

        # Rough duration estimate: ~150 chars/min for Chinese, ~180 words/min for English
        char_count = len(text)
        duration_estimate = (char_count / 5.0) * 1000  # ~200ms per char

        return TTSResult(
            audio_bytes=audio_bytes,
            audio_format="mp3",
            text=text,
            voice=selected_voice,
            duration_estimate_ms=duration_estimate,
            processing_time_ms=round(processing_time, 2),
        )

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str | Path,
        voice: Optional[str] = None,
    ) -> TTSResult:
        """
        Synthesize text and save to file.

        Args:
            text: Text to synthesize.
            output_path: Output file path.
            voice: Override voice.

        Returns:
            TTSResult (audio_bytes will be empty to save memory).
        """
        selected_voice = voice or self._detect_voice(text)
        start_time = time.time()

        communicate = edge_tts.Communicate(
            text=text,
            voice=selected_voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )

        await communicate.save(str(output_path))
        processing_time = (time.time() - start_time) * 1000

        return TTSResult(
            audio_bytes=b"",
            audio_format="mp3",
            text=text,
            voice=selected_voice,
            processing_time_ms=round(processing_time, 2),
        )

    def _detect_voice(self, text: str) -> str:
        """Auto-detect language and select appropriate voice."""
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        total_alpha = sum(1 for c in text if c.isalpha())

        if total_alpha == 0:
            return self.voice

        chinese_ratio = chinese_chars / max(total_alpha, 1)
        if chinese_ratio > 0.3:
            return self.voice  # Default is Chinese
        return VOICE_EN_FEMALE

    @staticmethod
    async def list_voices(language: Optional[str] = None) -> list:
        """List available voices, optionally filtered by language."""
        voices = await edge_tts.list_voices()
        if language:
            voices = [v for v in voices if v["Locale"].startswith(language)]
        return voices
