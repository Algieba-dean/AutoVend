"""
ASR (Automatic Speech Recognition) service using faster-whisper.

Provides speech-to-text capabilities with support for:
- File-based transcription (WAV, MP3, etc.)
- Byte-buffer transcription (for streaming)
- Multi-language support (zh/en auto-detect)
- Configurable model sizes (tiny/base/small/medium/large-v3)
"""

import io
import logging
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Default model: "base" balances speed vs accuracy for real-time use
DEFAULT_MODEL_SIZE = "base"
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"


@dataclass
class TranscriptionSegment:
    """A single transcription segment with timing info."""

    text: str = ""
    start: float = 0.0
    end: float = 0.0
    language: str = ""
    confidence: float = 0.0


@dataclass
class TranscriptionResult:
    """Full transcription result."""

    text: str = ""
    language: str = ""
    language_probability: float = 0.0
    segments: List[TranscriptionSegment] = field(default_factory=list)
    duration_seconds: float = 0.0
    processing_time_ms: float = 0.0


class WhisperASR:
    """
    Speech-to-text service using faster-whisper (CTranslate2 backend).

    Usage::

        asr = WhisperASR(model_size="base")
        result = asr.transcribe_file("audio.wav")
        print(result.text)

        result = asr.transcribe_bytes(audio_bytes, sample_rate=16000)
        print(result.text)
    """

    def __init__(
        self,
        model_size: str = DEFAULT_MODEL_SIZE,
        device: str = DEFAULT_DEVICE,
        compute_type: str = DEFAULT_COMPUTE_TYPE,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Optional[WhisperModel] = None

    @property
    def model(self) -> WhisperModel:
        """Lazy-load the Whisper model on first use."""
        if self._model is None:
            logger.info(
                f"Loading Whisper model: size={self.model_size}, "
                f"device={self.device}, compute_type={self.compute_type}"
            )
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("Whisper model loaded successfully.")
        return self._model

    def transcribe_file(
        self,
        audio_path: str | Path,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file (WAV, MP3, FLAC, etc.)
            language: Optional language code ('zh', 'en'). Auto-detect if None.

        Returns:
            TranscriptionResult with full text and segments.
        """
        audio_path = str(audio_path)
        start_time = time.time()

        segments_iter, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=300,
                speech_pad_ms=200,
            ),
        )

        segments = []
        full_text_parts = []
        for seg in segments_iter:
            ts = TranscriptionSegment(
                text=seg.text.strip(),
                start=seg.start,
                end=seg.end,
                language=info.language,
                confidence=1.0 - seg.no_speech_prob,
            )
            segments.append(ts)
            full_text_parts.append(seg.text.strip())

        processing_time = (time.time() - start_time) * 1000

        return TranscriptionResult(
            text=" ".join(full_text_parts),
            language=info.language,
            language_probability=info.language_probability,
            segments=segments,
            duration_seconds=info.duration,
            processing_time_ms=round(processing_time, 2),
        )

    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio from raw bytes.

        Args:
            audio_bytes: Raw audio bytes (PCM 16-bit or WAV format).
            sample_rate: Sample rate of the audio.
            language: Optional language code.

        Returns:
            TranscriptionResult.
        """
        # Try to read as WAV/FLAC first; fall back to raw PCM
        try:
            audio_data, sr = sf.read(io.BytesIO(audio_bytes))
            if audio_data.ndim > 1:
                audio_data = audio_data.mean(axis=1)
            audio_data = audio_data.astype(np.float32)
        except Exception:
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            audio_data /= 32768.0
            sr = sample_rate

        # Write to temp WAV for faster-whisper (it requires a file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, audio_data, sr, subtype="PCM_16")
            tmp_path = tmp.name

        try:
            return self.transcribe_file(tmp_path, language=language)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def transcribe_numpy(
        self,
        audio_array: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio from a numpy array.

        Args:
            audio_array: Float32 numpy array, mono, values in [-1, 1].
            sample_rate: Sample rate.
            language: Optional language code.

        Returns:
            TranscriptionResult.
        """
        if audio_array.ndim > 1:
            audio_array = audio_array.mean(axis=1)
        audio_array = audio_array.astype(np.float32)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, audio_array, sample_rate, subtype="PCM_16")
            tmp_path = tmp.name

        try:
            return self.transcribe_file(tmp_path, language=language)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
