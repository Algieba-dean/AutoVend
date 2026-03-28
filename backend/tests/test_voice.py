"""
Tests for the voice module: ASR, TTS, VoicePipeline, and voice routes.

Uses mock objects to avoid requiring actual model downloads or network
access during CI. Integration-level tests are marked with @pytest.mark.slow.
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from agent.schemas import (
    AgentResult,
    SessionState,
    Stage,
    UserProfile,
)
from agent.voice.asr import TranscriptionResult, TranscriptionSegment, WhisperASR
from agent.voice.pipeline import VoicePipeline, VoiceSessionMetrics, VoiceTurnResult
from agent.voice.tts import DEFAULT_VOICE, VOICE_EN_FEMALE, EdgeTTSService, TTSResult

# ── Helpers ─────────────────────────────────────────────────────


def _make_wav_bytes(
    duration_s: float = 1.0,
    sample_rate: int = 16000,
    frequency: float = 440.0,
) -> bytes:
    """Generate a valid WAV file (sine wave) as bytes."""
    num_samples = int(sample_rate * duration_s)
    t = np.linspace(0, duration_s, num_samples, dtype=np.float32)
    audio = (np.sin(2 * np.pi * frequency * t) * 0.5).astype(np.float32)

    buf = io.BytesIO()
    import soundfile as sf

    sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _make_pcm_bytes(
    duration_s: float = 1.0,
    sample_rate: int = 16000,
    frequency: float = 440.0,
) -> bytes:
    """Generate raw PCM 16-bit audio bytes."""
    num_samples = int(sample_rate * duration_s)
    t = np.linspace(0, duration_s, num_samples, dtype=np.float32)
    audio = (np.sin(2 * np.pi * frequency * t) * 16000).astype(np.int16)
    return audio.tobytes()


def _make_mock_transcription(
    text: str = "你好，我想买车",
    language: str = "zh",
) -> TranscriptionResult:
    """Create a mock TranscriptionResult."""
    return TranscriptionResult(
        text=text,
        language=language,
        language_probability=0.95,
        segments=[
            TranscriptionSegment(
                text=text,
                start=0.0,
                end=1.5,
                language=language,
                confidence=0.92,
            )
        ],
        duration_seconds=1.5,
        processing_time_ms=150.0,
    )


def _make_mock_tts_result(
    text: str = "欢迎来到AutoVend！",
) -> TTSResult:
    """Create a mock TTSResult."""
    return TTSResult(
        audio_bytes=b"\x00" * 1024,
        audio_format="mp3",
        text=text,
        voice=DEFAULT_VOICE,
        duration_estimate_ms=2000.0,
        processing_time_ms=300.0,
    )


def _make_mock_agent() -> MagicMock:
    """Create a mock SalesAgent that returns a predictable AgentResult."""
    mock_agent = MagicMock()
    mock_agent.process.return_value = AgentResult(
        session_state=SessionState(
            session_id="test-session",
            stage=Stage.WELCOME,
        ),
        response_text="你好！欢迎来到AutoVend智能购车助手。请问您贵姓？",
        stage_changed=False,
    )
    mock_agent.memory = MagicMock()
    return mock_agent


# ============================================================
# ASR Tests
# ============================================================


class TestWhisperASR:
    """Tests for WhisperASR service."""

    def test_init_defaults(self):
        asr = WhisperASR()
        assert asr.model_size == "base"
        assert asr.device == "cpu"
        assert asr.compute_type == "int8"
        assert asr._model is None

    def test_init_custom(self):
        asr = WhisperASR(model_size="small", device="cuda", compute_type="float16")
        assert asr.model_size == "small"
        assert asr.device == "cuda"
        assert asr.compute_type == "float16"

    @patch("agent.voice.asr.WhisperModel")
    def test_lazy_model_loading(self, mock_model_class):
        asr = WhisperASR()
        assert asr._model is None

        _ = asr.model
        mock_model_class.assert_called_once_with("base", device="cpu", compute_type="int8")
        assert asr._model is not None

    @patch("agent.voice.asr.WhisperModel")
    def test_model_loaded_once(self, mock_model_class):
        asr = WhisperASR()
        _ = asr.model
        _ = asr.model
        mock_model_class.assert_called_once()

    @patch("agent.voice.asr.WhisperModel")
    def test_transcribe_file(self, mock_model_class):
        mock_segment = MagicMock()
        mock_segment.text = " 你好我想买车 "
        mock_segment.start = 0.0
        mock_segment.end = 2.0
        mock_segment.no_speech_prob = 0.05

        mock_info = MagicMock()
        mock_info.language = "zh"
        mock_info.language_probability = 0.97
        mock_info.duration = 2.0

        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = (iter([mock_segment]), mock_info)
        mock_model_class.return_value = mock_instance

        asr = WhisperASR()
        result = asr.transcribe_file("test.wav")

        assert isinstance(result, TranscriptionResult)
        assert result.text == "你好我想买车"
        assert result.language == "zh"
        assert result.language_probability == 0.97
        assert len(result.segments) == 1
        assert result.segments[0].confidence == pytest.approx(0.95, abs=0.01)
        assert result.processing_time_ms > 0

    @patch("agent.voice.asr.WhisperModel")
    def test_transcribe_bytes_wav(self, mock_model_class):
        mock_segment = MagicMock()
        mock_segment.text = " hello "
        mock_segment.start = 0.0
        mock_segment.end = 1.0
        mock_segment.no_speech_prob = 0.1

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.99
        mock_info.duration = 1.0

        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = (iter([mock_segment]), mock_info)
        mock_model_class.return_value = mock_instance

        asr = WhisperASR()
        wav_bytes = _make_wav_bytes(duration_s=1.0)
        result = asr.transcribe_bytes(wav_bytes)

        assert result.text == "hello"
        assert result.language == "en"

    @patch("agent.voice.asr.WhisperModel")
    def test_transcribe_numpy(self, mock_model_class):
        mock_segment = MagicMock()
        mock_segment.text = " test "
        mock_segment.start = 0.0
        mock_segment.end = 0.5
        mock_segment.no_speech_prob = 0.02

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.98
        mock_info.duration = 0.5

        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = (iter([mock_segment]), mock_info)
        mock_model_class.return_value = mock_instance

        asr = WhisperASR()
        audio = np.random.randn(16000).astype(np.float32) * 0.1
        result = asr.transcribe_numpy(audio, sample_rate=16000)

        assert result.text == "test"

    @patch("agent.voice.asr.WhisperModel")
    def test_transcribe_empty_result(self, mock_model_class):
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.5
        mock_info.duration = 1.0

        mock_instance = MagicMock()
        mock_instance.transcribe.return_value = (iter([]), mock_info)
        mock_model_class.return_value = mock_instance

        asr = WhisperASR()
        result = asr.transcribe_file("silence.wav")

        assert result.text == ""
        assert len(result.segments) == 0


# ============================================================
# TTS Tests
# ============================================================


class TestEdgeTTSService:
    """Tests for EdgeTTSService."""

    def test_init_defaults(self):
        tts = EdgeTTSService()
        assert tts.voice == DEFAULT_VOICE
        assert tts.rate == "+0%"
        assert tts.volume == "+0%"
        assert tts.pitch == "+0Hz"

    def test_init_custom(self):
        tts = EdgeTTSService(
            voice=VOICE_EN_FEMALE,
            rate="+10%",
            volume="-5%",
            pitch="+5Hz",
        )
        assert tts.voice == VOICE_EN_FEMALE
        assert tts.rate == "+10%"

    def test_detect_voice_chinese(self):
        tts = EdgeTTSService()
        assert tts._detect_voice("你好，我想买车") == DEFAULT_VOICE

    def test_detect_voice_english(self):
        tts = EdgeTTSService()
        assert tts._detect_voice("Hello, I want to buy a car") == VOICE_EN_FEMALE

    def test_detect_voice_mixed(self):
        tts = EdgeTTSService()
        # More Chinese than English
        voice = tts._detect_voice("你好hello世界world测试test你好你好")
        assert voice == DEFAULT_VOICE

    def test_detect_voice_empty(self):
        tts = EdgeTTSService()
        assert tts._detect_voice("") == DEFAULT_VOICE
        assert tts._detect_voice("123 456") == DEFAULT_VOICE

    @pytest.mark.asyncio
    async def test_synthesize_async_empty(self):
        tts = EdgeTTSService()
        result = await tts.synthesize_async("")
        assert result.audio_bytes == b""
        assert result.text == ""

    @pytest.mark.asyncio
    async def test_synthesize_async_whitespace(self):
        tts = EdgeTTSService()
        result = await tts.synthesize_async("   ")
        assert result.audio_bytes == b""

    @pytest.mark.asyncio
    @patch("agent.voice.tts.edge_tts.Communicate")
    async def test_synthesize_async_success(self, mock_communicate_class):
        mock_instance = MagicMock()

        async def mock_stream():
            yield {"type": "audio", "data": b"\x00\x01\x02"}
            yield {"type": "audio", "data": b"\x03\x04\x05"}
            yield {"type": "WordBoundary", "offset": 0}

        mock_instance.stream = mock_stream
        mock_communicate_class.return_value = mock_instance

        tts = EdgeTTSService()
        result = await tts.synthesize_async("你好")

        assert isinstance(result, TTSResult)
        assert result.audio_bytes == b"\x00\x01\x02\x03\x04\x05"
        assert result.audio_format == "mp3"
        assert result.voice == DEFAULT_VOICE
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    @patch("agent.voice.tts.edge_tts.Communicate")
    async def test_synthesize_async_voice_override(self, mock_communicate_class):
        mock_instance = MagicMock()

        async def mock_stream():
            yield {"type": "audio", "data": b"\xff"}

        mock_instance.stream = mock_stream
        mock_communicate_class.return_value = mock_instance

        tts = EdgeTTSService()
        result = await tts.synthesize_async("Hello", voice=VOICE_EN_FEMALE)

        mock_communicate_class.assert_called_once_with(
            text="Hello",
            voice=VOICE_EN_FEMALE,
            rate="+0%",
            volume="+0%",
            pitch="+0Hz",
        )
        assert result.voice == VOICE_EN_FEMALE

    @pytest.mark.asyncio
    @patch("agent.voice.tts.edge_tts.Communicate")
    async def test_synthesize_to_file(self, mock_communicate_class, tmp_path):
        mock_instance = MagicMock()
        mock_instance.save = AsyncMock()
        mock_communicate_class.return_value = mock_instance

        tts = EdgeTTSService()
        out_path = tmp_path / "output.mp3"
        result = await tts.synthesize_to_file("你好", out_path)

        mock_instance.save.assert_called_once_with(str(out_path))
        assert result.audio_bytes == b""
        assert result.audio_format == "mp3"
        assert result.processing_time_ms > 0


# ============================================================
# TranscriptionResult / TTSResult dataclass tests
# ============================================================


class TestDataclasses:
    def test_transcription_result_defaults(self):
        r = TranscriptionResult()
        assert r.text == ""
        assert r.language == ""
        assert r.segments == []
        assert r.processing_time_ms == 0.0

    def test_transcription_segment(self):
        seg = TranscriptionSegment(text="hello", start=0.0, end=1.5, language="en", confidence=0.9)
        assert seg.text == "hello"
        assert seg.end == 1.5

    def test_tts_result_defaults(self):
        r = TTSResult(audio_bytes=b"", text="test", voice="v")
        assert r.audio_format == "mp3"
        assert r.processing_time_ms == 0.0

    def test_voice_turn_result_to_dict(self):
        r = VoiceTurnResult(
            user_text="hello",
            agent_response="Hi there! " * 30,  # > 200 chars
            asr_time_ms=100,
            agent_time_ms=200,
            tts_time_ms=300,
            total_time_ms=600,
            audio_bytes=b"\x00" * 500,
        )
        d = r.to_dict()
        assert d["user_text"] == "hello"
        assert len(d["agent_response"]) <= 200
        assert d["audio_size_bytes"] == 500
        assert d["total_time_ms"] == 600.0


# ============================================================
# VoiceSessionMetrics Tests
# ============================================================


class TestVoiceSessionMetrics:
    def test_initial_metrics(self):
        m = VoiceSessionMetrics()
        assert m.total_turns == 0
        assert m.avg_turn_latency_ms == 0.0

    def test_update_single_turn(self):
        m = VoiceSessionMetrics()
        turn = VoiceTurnResult(
            asr_time_ms=100,
            agent_time_ms=200,
            tts_time_ms=300,
            total_time_ms=600,
            asr_language="zh",
        )
        m.update(turn)
        assert m.total_turns == 1
        assert m.total_asr_time_ms == 100
        assert m.avg_turn_latency_ms == 600
        assert "zh" in m.languages_detected

    def test_update_multiple_turns(self):
        m = VoiceSessionMetrics()
        turn1 = VoiceTurnResult(
            asr_time_ms=100,
            agent_time_ms=200,
            tts_time_ms=300,
            total_time_ms=600,
            asr_language="zh",
        )
        turn2 = VoiceTurnResult(
            asr_time_ms=150,
            agent_time_ms=250,
            tts_time_ms=350,
            total_time_ms=750,
            asr_language="en",
        )
        m.update(turn1)
        m.update(turn2)
        assert m.total_turns == 2
        assert m.total_asr_time_ms == 250
        assert m.avg_turn_latency_ms == pytest.approx(675.0)
        assert set(m.languages_detected) == {"zh", "en"}

    def test_duplicate_language_not_added(self):
        m = VoiceSessionMetrics()
        turn = VoiceTurnResult(asr_language="zh", total_time_ms=100)
        m.update(turn)
        m.update(turn)
        assert m.languages_detected == ["zh"]

    def test_to_dict(self):
        m = VoiceSessionMetrics()
        turn = VoiceTurnResult(
            asr_time_ms=100,
            agent_time_ms=200,
            tts_time_ms=300,
            total_time_ms=600,
            asr_language="zh",
        )
        m.update(turn)
        d = m.to_dict()
        assert d["total_turns"] == 1
        assert d["languages_detected"] == ["zh"]
        assert isinstance(d["avg_turn_latency_ms"], float)


# ============================================================
# VoicePipeline Tests
# ============================================================


class TestVoicePipeline:
    """Tests for the VoicePipeline orchestration."""

    def _make_pipeline(self):
        mock_agent = _make_mock_agent()
        mock_asr = MagicMock(spec=WhisperASR)
        mock_tts = MagicMock(spec=EdgeTTSService)
        mock_tts.voice = DEFAULT_VOICE
        return VoicePipeline(agent=mock_agent, asr=mock_asr, tts=mock_tts)

    def test_init(self):
        mock_agent = _make_mock_agent()
        pipeline = VoicePipeline(agent=mock_agent)
        assert pipeline.agent is mock_agent
        assert isinstance(pipeline.asr, WhisperASR)
        assert isinstance(pipeline.tts, EdgeTTSService)

    def test_init_custom_services(self):
        pipeline = self._make_pipeline()
        assert pipeline.asr is not None
        assert pipeline.tts is not None

    @patch("agent.voice.pipeline.asyncio.run")
    def test_process_audio_file(self, mock_asyncio_run):
        pipeline = self._make_pipeline()

        pipeline.asr.transcribe_file.return_value = _make_mock_transcription()
        mock_asyncio_run.return_value = _make_mock_tts_result()

        state = SessionState(session_id="s1")
        result = pipeline.process_audio_file("test.wav", state)

        assert isinstance(result, VoiceTurnResult)
        assert result.user_text == "你好，我想买车"
        assert result.agent_response != ""
        assert result.total_time_ms > 0
        pipeline.asr.transcribe_file.assert_called_once_with("test.wav")
        pipeline.agent.process.assert_called_once()

    @patch("agent.voice.pipeline.asyncio.run")
    def test_process_audio_file_skip_tts(self, mock_asyncio_run):
        pipeline = self._make_pipeline()
        pipeline.asr.transcribe_file.return_value = _make_mock_transcription()

        state = SessionState(session_id="s2")
        result = pipeline.process_audio_file("test.wav", state, skip_tts=True)

        assert result.audio_bytes == b""
        mock_asyncio_run.assert_not_called()

    @patch("agent.voice.pipeline.asyncio.run")
    def test_process_audio_bytes(self, mock_asyncio_run):
        pipeline = self._make_pipeline()
        pipeline.asr.transcribe_bytes.return_value = _make_mock_transcription(
            text="hello", language="en"
        )
        mock_asyncio_run.return_value = _make_mock_tts_result()

        state = SessionState(session_id="s3")
        wav = _make_wav_bytes()
        result = pipeline.process_audio_bytes(wav, state)

        assert result.user_text == "hello"
        assert result.asr_language == "en"
        pipeline.asr.transcribe_bytes.assert_called_once()

    @patch("agent.voice.pipeline.asyncio.run")
    def test_process_text(self, mock_asyncio_run):
        pipeline = self._make_pipeline()
        mock_asyncio_run.return_value = _make_mock_tts_result()

        state = SessionState(session_id="s4")
        result = pipeline.process_text("我想买SUV", state)

        assert result.user_text == "我想买SUV"
        assert result.asr_time_ms == 0.0
        assert result.asr_confidence == 1.0
        pipeline.agent.process.assert_called_once()

    @patch("agent.voice.pipeline.asyncio.run")
    def test_session_metrics_tracked(self, mock_asyncio_run):
        pipeline = self._make_pipeline()
        pipeline.asr.transcribe_file.return_value = _make_mock_transcription()
        mock_asyncio_run.return_value = _make_mock_tts_result()

        state = SessionState(session_id="metrics-test")
        pipeline.process_audio_file("a.wav", state)
        pipeline.process_audio_file("b.wav", state)

        metrics = pipeline.get_session_metrics("metrics-test")
        assert metrics is not None
        assert metrics.total_turns == 2
        assert metrics.avg_turn_latency_ms > 0

    def test_get_session_metrics_nonexistent(self):
        pipeline = self._make_pipeline()
        assert pipeline.get_session_metrics("nonexistent") is None

    @patch("agent.voice.pipeline.asyncio.run")
    def test_process_with_retrieved_cars(self, mock_asyncio_run):
        pipeline = self._make_pipeline()
        pipeline.asr.transcribe_file.return_value = _make_mock_transcription()
        mock_asyncio_run.return_value = _make_mock_tts_result()

        state = SessionState(session_id="cars-test")
        cars = [{"model": "Tesla Model 3", "price": "250000"}]
        pipeline.process_audio_file("test.wav", state, retrieved_cars=cars)

        call_args = pipeline.agent.process.call_args
        agent_input = call_args[0][0]
        assert agent_input.retrieved_cars == cars


# ============================================================
# Voice Route Tests
# ============================================================


class TestVoiceRoutes:
    """Tests for voice REST endpoints (not requiring real model)."""

    @pytest.fixture
    def mock_voice_modules(self):
        """Patch voice route globals."""
        with (
            patch("app.routes.voice._asr") as mock_asr,
            patch("app.routes.voice._tts") as mock_tts,
            patch("app.routes.voice._pipeline") as mock_pipeline,
        ):
            yield mock_asr, mock_tts, mock_pipeline

    def test_voice_session_create(self):
        """Test voice session creation endpoint logic."""
        from app.routes.voice import _voice_sessions

        # Clear sessions
        _voice_sessions.clear()

        # Simulate session creation
        session_id = "test-voice-session"
        state = SessionState(session_id=session_id, profile=UserProfile())
        _voice_sessions[session_id] = state

        assert session_id in _voice_sessions
        assert _voice_sessions[session_id].stage == Stage.WELCOME

    def test_voice_session_end(self):
        """Test voice session cleanup."""
        from app.routes.voice import _voice_sessions

        session_id = "test-cleanup"
        _voice_sessions[session_id] = SessionState(session_id=session_id)

        state = _voice_sessions.pop(session_id, None)
        assert state is not None
        assert session_id not in _voice_sessions

    def test_voice_session_not_found(self):
        """Test accessing non-existent voice session."""
        from app.routes.voice import _voice_sessions

        _voice_sessions.clear()
        assert _voice_sessions.get("nonexistent") is None


# ============================================================
# Integration-style tests (still mocked, but test full flow)
# ============================================================


class TestVoiceIntegration:
    """Integration-style tests for the full voice pipeline flow."""

    @patch("agent.voice.pipeline.asyncio.run")
    def test_full_conversation_turn(self, mock_asyncio_run):
        """Test a complete voice conversation turn: ASR → Agent → TTS."""
        mock_agent = _make_mock_agent()
        mock_asr = MagicMock(spec=WhisperASR)
        mock_tts = MagicMock(spec=EdgeTTSService)
        mock_tts.voice = DEFAULT_VOICE

        mock_asr.transcribe_file.return_value = _make_mock_transcription(
            text="你好，我叫张三",
            language="zh",
        )

        mock_agent.process.return_value = AgentResult(
            session_state=SessionState(
                session_id="int-test",
                stage=Stage.PROFILE_ANALYSIS,
                profile=UserProfile(name="张三"),
            ),
            response_text="张三您好！请问您的购车预算大概是多少？",
            stage_changed=True,
        )

        mock_asyncio_run.return_value = TTSResult(
            audio_bytes=b"\x00" * 2048,
            audio_format="mp3",
            text="张三您好！请问您的购车预算大概是多少？",
            voice=DEFAULT_VOICE,
            processing_time_ms=250.0,
        )

        pipeline = VoicePipeline(agent=mock_agent, asr=mock_asr, tts=mock_tts)
        state = SessionState(session_id="int-test")

        result = pipeline.process_audio_file("user_audio.wav", state)

        # Verify ASR
        assert result.user_text == "你好，我叫张三"
        assert result.asr_language == "zh"

        # Verify Agent
        assert result.agent_response == "张三您好！请问您的购车预算大概是多少？"
        assert result.stage == "profile_analysis"
        assert result.stage_changed is True

        # Verify TTS
        assert len(result.audio_bytes) == 2048
        assert result.audio_format == "mp3"

        # Verify timing
        assert result.total_time_ms > 0
        assert result.asr_time_ms >= 0
        assert result.tts_time_ms == 250.0

    @patch("agent.voice.pipeline.asyncio.run")
    def test_multi_turn_conversation(self, mock_asyncio_run):
        """Test multiple consecutive voice turns tracking metrics."""
        mock_agent = _make_mock_agent()
        mock_asr = MagicMock(spec=WhisperASR)
        mock_tts = MagicMock(spec=EdgeTTSService)
        mock_tts.voice = DEFAULT_VOICE

        pipeline = VoicePipeline(agent=mock_agent, asr=mock_asr, tts=mock_tts)
        sid = "multi-turn-test"

        turns_data = [
            ("你好", "zh", "欢迎！", Stage.WELCOME),
            ("我叫李四", "zh", "李四您好！", Stage.PROFILE_ANALYSIS),
            ("预算20万", "zh", "好的，20万预算。", Stage.NEEDS_ANALYSIS),
        ]

        for user_text, lang, response, stage in turns_data:
            mock_asr.transcribe_file.return_value = _make_mock_transcription(
                text=user_text, language=lang
            )
            mock_agent.process.return_value = AgentResult(
                session_state=SessionState(session_id=sid, stage=stage),
                response_text=response,
                stage_changed=True,
            )
            mock_asyncio_run.return_value = TTSResult(
                audio_bytes=b"\x00" * 512,
                voice=DEFAULT_VOICE,
                processing_time_ms=200.0,
            )

            state = SessionState(session_id=sid, stage=stage)
            result = pipeline.process_audio_file("turn.wav", state)
            assert result.user_text == user_text

        metrics = pipeline.get_session_metrics(sid)
        assert metrics.total_turns == 3
        assert metrics.languages_detected == ["zh"]

    @patch("agent.voice.pipeline.asyncio.run")
    def test_bilingual_conversation(self, mock_asyncio_run):
        """Test mixed Chinese/English voice interaction."""
        mock_agent = _make_mock_agent()
        mock_asr = MagicMock(spec=WhisperASR)
        mock_tts = MagicMock(spec=EdgeTTSService)
        mock_tts.voice = DEFAULT_VOICE

        pipeline = VoicePipeline(agent=mock_agent, asr=mock_asr, tts=mock_tts)
        sid = "bilingual-test"

        # Chinese turn
        mock_asr.transcribe_file.return_value = _make_mock_transcription("你好", "zh")
        mock_asyncio_run.return_value = _make_mock_tts_result()
        state = SessionState(session_id=sid)
        pipeline.process_audio_file("zh.wav", state)

        # English turn
        mock_asr.transcribe_file.return_value = _make_mock_transcription("I want a Tesla", "en")
        mock_asyncio_run.return_value = _make_mock_tts_result()
        pipeline.process_audio_file("en.wav", state)

        metrics = pipeline.get_session_metrics(sid)
        assert set(metrics.languages_detected) == {"zh", "en"}
        assert metrics.total_turns == 2
