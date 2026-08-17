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
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Ensure imageio_ffmpeg binary is in PATH
try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + ":" + os.environ.get("PATH", "")
except Exception:
    pass

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
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=300,
                speech_pad_ms=200,
            ),
        )

        segments = []
        full_text_parts = []
        for seg in segments_iter:
            if seg.text.strip():
                ts = TranscriptionSegment(
                    text=seg.text.strip(),
                    start=seg.start,
                    end=seg.end,
                    language=info.language,
                    confidence=1.0 - seg.no_speech_prob,
                )
                segments.append(ts)
                full_text_parts.append(seg.text.strip())

        # Fallback pass if VAD filtered out short / quiet audio
        if not full_text_parts:
            segments_iter_fallback, info_fallback = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=1,
                vad_filter=False,
            )
            for seg in segments_iter_fallback:
                if seg.text.strip():
                    ts = TranscriptionSegment(
                        text=seg.text.strip(),
                        start=seg.start,
                        end=seg.end,
                        language=info_fallback.language,
                        confidence=1.0 - seg.no_speech_prob,
                    )
                    segments.append(ts)
                    full_text_parts.append(seg.text.strip())
            if full_text_parts:
                info = info_fallback

        processing_time = (time.time() - start_time) * 1000

        return TranscriptionResult(
            text=" ".join(full_text_parts),
            language=info.language,
            language_probability=info.language_probability,
            segments=segments,
            duration_seconds=info.duration,
            processing_time_ms=round(processing_time, 2),
        )

    def _convert_bytes_to_wav(self, audio_bytes: bytes) -> Optional[str]:
        """Convert container audio bytes (WebM, Opus, Ogg, MP3) to a 16kHz mono WAV file using ffmpeg."""
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_exe = "ffmpeg"

        with tempfile.NamedTemporaryFile(suffix=".raw_input", delete=False) as in_tmp:
            in_tmp.write(audio_bytes)
            in_path = in_tmp.name

        out_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        out_path = out_tmp.name
        out_tmp.close()

        try:
            cmd = [
                ffmpeg_exe, "-y",
                "-i", in_path,
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                out_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            if res.returncode == 0 and Path(out_path).stat().st_size > 0:
                return out_path

            # Fallback: Treat as raw s16le PCM if container header missing
            cmd_pcm = [
                ffmpeg_exe, "-y",
                "-f", "s16le",
                "-ar", "16000",
                "-ac", "1",
                "-i", in_path,
                "-c:a", "pcm_s16le",
                out_path
            ]
            res_pcm = subprocess.run(cmd_pcm, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            if res_pcm.returncode == 0 and Path(out_path).stat().st_size > 0:
                return out_path
        except Exception as e:
            logger.debug(f"ffmpeg conversion failed: {e}")
        finally:
            Path(in_path).unlink(missing_ok=True)
        return None

    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio from raw bytes (supports WAV, WebM, MP3, FLAC, OGG, raw PCM).
        """
        if not audio_bytes:
            return TranscriptionResult()

        # 1. Try soundfile (WAV, FLAC, OGG, MP3)
        try:
            audio_data, sr = sf.read(io.BytesIO(audio_bytes))
            if audio_data.ndim > 1:
                audio_data = audio_data.mean(axis=1)
            audio_data = audio_data.astype(np.float32)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                sf.write(tmp.name, audio_data, sr, subtype="PCM_16")
                tmp_path = tmp.name

            try:
                res = self.transcribe_file(tmp_path, language=language)
                if res and res.text:
                    return res
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

        # 2. Try explicit ffmpeg conversion (WebM / Opus container)
        wav_path = self._convert_bytes_to_wav(audio_bytes)
        if wav_path:
            try:
                res = self.transcribe_file(wav_path, language=language)
                return res
            finally:
                Path(wav_path).unlink(missing_ok=True)

        # 3. Fallback: treat as raw PCM 16-bit ONLY if bytes look like raw PCM
        try:
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                sf.write(tmp.name, audio_data, sample_rate, subtype="PCM_16")
                tmp_path = tmp.name
            try:
                return self.transcribe_file(tmp_path, language=language)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"Failed to transcribe audio bytes: {e}")
            return TranscriptionResult()

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
