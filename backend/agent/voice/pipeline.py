"""
VoicePipeline — end-to-end voice conversation pipeline.

Orchestrates: Audio → ASR → SalesAgent → TTS → Audio

Supports both single-turn (file-based) and streaming modes.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.sales_agent import SalesAgent
from agent.schemas import AgentInput, AgentResult, SessionState
from agent.voice.asr import WhisperASR
from agent.voice.tts import EdgeTTSService, TTSResult

logger = logging.getLogger(__name__)


@dataclass
class VoiceTurnResult:
    """Result of one voice conversation turn."""

    # ASR
    user_text: str = ""
    asr_language: str = ""
    asr_confidence: float = 0.0
    asr_time_ms: float = 0.0

    # Agent
    agent_response: str = ""
    stage: str = ""
    stage_changed: bool = False
    agent_time_ms: float = 0.0

    # TTS
    audio_bytes: bytes = b""
    audio_format: str = "mp3"
    tts_voice: str = ""
    tts_time_ms: float = 0.0

    # Total
    total_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_text": self.user_text,
            "asr_language": self.asr_language,
            "asr_confidence": self.asr_confidence,
            "asr_time_ms": round(self.asr_time_ms, 2),
            "agent_response": self.agent_response[:200],
            "stage": self.stage,
            "stage_changed": self.stage_changed,
            "agent_time_ms": round(self.agent_time_ms, 2),
            "tts_voice": self.tts_voice,
            "tts_time_ms": round(self.tts_time_ms, 2),
            "total_time_ms": round(self.total_time_ms, 2),
            "audio_size_bytes": len(self.audio_bytes),
        }


@dataclass
class VoiceSessionMetrics:
    """Accumulated metrics for a voice session."""

    total_turns: int = 0
    total_asr_time_ms: float = 0.0
    total_agent_time_ms: float = 0.0
    total_tts_time_ms: float = 0.0
    total_pipeline_time_ms: float = 0.0
    avg_turn_latency_ms: float = 0.0
    languages_detected: List[str] = field(default_factory=list)

    def update(self, turn: VoiceTurnResult):
        self.total_turns += 1
        self.total_asr_time_ms += turn.asr_time_ms
        self.total_agent_time_ms += turn.agent_time_ms
        self.total_tts_time_ms += turn.tts_time_ms
        self.total_pipeline_time_ms += turn.total_time_ms
        self.avg_turn_latency_ms = self.total_pipeline_time_ms / self.total_turns
        if turn.asr_language and turn.asr_language not in self.languages_detected:
            self.languages_detected.append(turn.asr_language)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_turns": self.total_turns,
            "total_asr_time_ms": round(self.total_asr_time_ms, 2),
            "total_agent_time_ms": round(self.total_agent_time_ms, 2),
            "total_tts_time_ms": round(self.total_tts_time_ms, 2),
            "total_pipeline_time_ms": round(self.total_pipeline_time_ms, 2),
            "avg_turn_latency_ms": round(self.avg_turn_latency_ms, 2),
            "languages_detected": self.languages_detected,
        }


class VoicePipeline:
    """
    End-to-end voice conversation pipeline.

    Connects ASR, SalesAgent, and TTS into a unified flow::

        pipeline = VoicePipeline(agent=sales_agent)
        result = pipeline.process_audio_file("user_audio.wav", session_state)
        # result.user_text  -> transcribed text
        # result.agent_response -> agent reply text
        # result.audio_bytes -> TTS audio (MP3)

    Args:
        agent: SalesAgent instance.
        asr: WhisperASR instance. Created with defaults if None.
        tts: EdgeTTSService instance. Created with defaults if None.
    """

    def __init__(
        self,
        agent: SalesAgent,
        asr: Optional[WhisperASR] = None,
        tts: Optional[EdgeTTSService] = None,
    ):
        self.agent = agent
        self.asr = asr or WhisperASR()
        self.tts = tts or EdgeTTSService()
        self._session_metrics: Dict[str, VoiceSessionMetrics] = {}

    def process_audio_file(
        self,
        audio_path: str | Path,
        session_state: SessionState,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        skip_tts: bool = False,
    ) -> VoiceTurnResult:
        """
        Process one voice turn from an audio file.

        Pipeline: Audio File → ASR → Agent → TTS → Result

        Args:
            audio_path: Path to user's audio file.
            session_state: Current session state.
            retrieved_cars: Optional RAG retrieval results.
            skip_tts: If True, skip TTS synthesis (text-only response).

        Returns:
            VoiceTurnResult with all intermediate results.
        """
        pipeline_start = time.time()

        # Step 1: ASR
        asr_result = self.asr.transcribe_file(audio_path)

        # Step 2: Agent
        agent_result = self._run_agent(session_state, asr_result.text, retrieved_cars)

        # Step 3: TTS
        tts_result = TTSResult(audio_bytes=b"", voice=self.tts.voice)
        if not skip_tts and agent_result.response_text:
            tts_result = asyncio.run(self.tts.synthesize_async(agent_result.response_text))

        total_time = (time.time() - pipeline_start) * 1000

        turn_result = VoiceTurnResult(
            user_text=asr_result.text,
            asr_language=asr_result.language,
            asr_confidence=asr_result.language_probability,
            asr_time_ms=asr_result.processing_time_ms,
            agent_response=agent_result.response_text,
            stage=agent_result.session_state.stage.value,
            stage_changed=agent_result.stage_changed,
            agent_time_ms=(
                total_time - asr_result.processing_time_ms - tts_result.processing_time_ms
            ),
            audio_bytes=tts_result.audio_bytes,
            audio_format=tts_result.audio_format,
            tts_voice=tts_result.voice,
            tts_time_ms=tts_result.processing_time_ms,
            total_time_ms=total_time,
        )

        # Update metrics
        sid = session_state.session_id
        if sid not in self._session_metrics:
            self._session_metrics[sid] = VoiceSessionMetrics()
        self._session_metrics[sid].update(turn_result)

        logger.info(
            f"[{sid}] Voice turn: ASR={asr_result.processing_time_ms:.0f}ms "
            f"Agent={turn_result.agent_time_ms:.0f}ms "
            f"TTS={tts_result.processing_time_ms:.0f}ms "
            f"Total={total_time:.0f}ms"
        )

        return turn_result

    def process_audio_bytes(
        self,
        audio_bytes: bytes,
        session_state: SessionState,
        sample_rate: int = 16000,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        skip_tts: bool = False,
    ) -> VoiceTurnResult:
        """
        Process one voice turn from raw audio bytes.

        Args:
            audio_bytes: Raw audio data (WAV or PCM).
            session_state: Current session state.
            sample_rate: Audio sample rate.
            retrieved_cars: Optional RAG results.
            skip_tts: If True, skip TTS.

        Returns:
            VoiceTurnResult.
        """
        pipeline_start = time.time()

        # Step 1: ASR
        asr_result = self.asr.transcribe_bytes(audio_bytes, sample_rate=sample_rate)

        # Step 2: Agent
        agent_result = self._run_agent(session_state, asr_result.text, retrieved_cars)

        # Step 3: TTS
        tts_result = TTSResult(audio_bytes=b"", voice=self.tts.voice)
        if not skip_tts and agent_result.response_text:
            tts_result = asyncio.run(self.tts.synthesize_async(agent_result.response_text))

        total_time = (time.time() - pipeline_start) * 1000

        turn_result = VoiceTurnResult(
            user_text=asr_result.text,
            asr_language=asr_result.language,
            asr_confidence=asr_result.language_probability,
            asr_time_ms=asr_result.processing_time_ms,
            agent_response=agent_result.response_text,
            stage=agent_result.session_state.stage.value,
            stage_changed=agent_result.stage_changed,
            agent_time_ms=(
                total_time - asr_result.processing_time_ms - tts_result.processing_time_ms
            ),
            audio_bytes=tts_result.audio_bytes,
            audio_format=tts_result.audio_format,
            tts_voice=tts_result.voice,
            tts_time_ms=tts_result.processing_time_ms,
            total_time_ms=total_time,
        )

        sid = session_state.session_id
        if sid not in self._session_metrics:
            self._session_metrics[sid] = VoiceSessionMetrics()
        self._session_metrics[sid].update(turn_result)

        return turn_result

    def process_text(
        self,
        text: str,
        session_state: SessionState,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        skip_tts: bool = False,
    ) -> VoiceTurnResult:
        """
        Process a text message through Agent + TTS (skip ASR).

        Useful for testing the agent+TTS pipeline without audio input.

        Args:
            text: User text message.
            session_state: Current session state.
            retrieved_cars: Optional RAG results.
            skip_tts: If True, skip TTS.

        Returns:
            VoiceTurnResult.
        """
        pipeline_start = time.time()

        agent_result = self._run_agent(session_state, text, retrieved_cars)
        agent_time = (time.time() - pipeline_start) * 1000

        tts_result = TTSResult(audio_bytes=b"", voice=self.tts.voice)
        if not skip_tts and agent_result.response_text:
            tts_result = asyncio.run(self.tts.synthesize_async(agent_result.response_text))

        total_time = (time.time() - pipeline_start) * 1000

        return VoiceTurnResult(
            user_text=text,
            asr_language="",
            asr_confidence=1.0,
            asr_time_ms=0.0,
            agent_response=agent_result.response_text,
            stage=agent_result.session_state.stage.value,
            stage_changed=agent_result.stage_changed,
            agent_time_ms=agent_time,
            audio_bytes=tts_result.audio_bytes,
            audio_format=tts_result.audio_format,
            tts_voice=tts_result.voice,
            tts_time_ms=tts_result.processing_time_ms,
            total_time_ms=total_time,
        )

    def get_session_metrics(self, session_id: str) -> Optional[VoiceSessionMetrics]:
        """Get accumulated metrics for a voice session."""
        return self._session_metrics.get(session_id)

    def _run_agent(
        self,
        session_state: SessionState,
        user_text: str,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentResult:
        """Run the SalesAgent on user text."""
        agent_input = AgentInput(
            session_state=session_state,
            user_message=user_text,
            retrieved_cars=retrieved_cars or [],
        )
        return self.agent.process(agent_input)
