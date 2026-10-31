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

from src.agent.sales_agent import SalesAgent
from src.agent.schemas import AgentInput, AgentResult, SessionState
from src.agent.voice.asr import WhisperASR
from src.agent.voice.tts import EdgeTTSService, TTSResult

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
    session_state: Optional[SessionState] = None

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

    def _synthesize_speech(self, text: str) -> TTSResult:
        """Synthesize TTS audio safely in both sync and async runtime contexts."""
        if not text:
            return TTSResult(audio_bytes=b"", voice=self.tts.voice)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            return self.tts.synthesize(text)
        else:
            coro = self.tts.synthesize_async(text)
            try:
                return asyncio.run(coro)
            except RuntimeError:
                if asyncio.iscoroutine(coro):
                    coro.close()
                return self.tts.synthesize(text)
            finally:
                # If asyncio.run was patched in unit tests and did not await coro, close it cleanly
                if asyncio.iscoroutine(coro) and getattr(coro, "cr_frame", None) is not None:
                    coro.close()

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
        """
        pipeline_start = time.time()

        # Step 1: ASR
        asr_result = self.asr.transcribe_file(audio_path)

        # Step 2: Agent
        agent_result = self._run_agent(session_state, asr_result.text, retrieved_cars)

        # Step 3: TTS
        tts_result = TTSResult(audio_bytes=b"", voice=self.tts.voice)
        if not skip_tts and agent_result.response_text:
            tts_result = self._synthesize_speech(agent_result.response_text)

        total_time = (time.time() - pipeline_start) * 1000
        asr_ms = (
            float(asr_result.processing_time_ms)
            if isinstance(asr_result.processing_time_ms, (int, float))
            else 0.0
        )
        tts_ms = (
            float(tts_result.processing_time_ms)
            if isinstance(tts_result.processing_time_ms, (int, float))
            else 0.0
        )
        agent_time = max(0.0, total_time - asr_ms - tts_ms)

        turn_result = VoiceTurnResult(
            user_text=str(asr_result.text) if asr_result.text is not None else "",
            asr_language=str(asr_result.language) if asr_result.language else "zh",
            asr_confidence=float(asr_result.language_probability)
            if isinstance(asr_result.language_probability, (int, float))
            else 0.0,
            asr_time_ms=asr_ms,
            agent_response=str(agent_result.response_text) if agent_result.response_text else "",
            stage=agent_result.session_state.stage.value,
            stage_changed=agent_result.stage_changed,
            agent_time_ms=agent_time,
            session_state=agent_result.session_state,
            audio_bytes=tts_result.audio_bytes
            if isinstance(tts_result.audio_bytes, bytes)
            else b"",
            audio_format=str(tts_result.audio_format) if tts_result.audio_format else "mp3",
            tts_voice=str(tts_result.voice) if tts_result.voice else "",
            tts_time_ms=tts_ms,
            total_time_ms=total_time,
        )

        # Update metrics
        sid = session_state.session_id
        if sid not in self._session_metrics:
            self._session_metrics[sid] = VoiceSessionMetrics()
        self._session_metrics[sid].update(turn_result)

        logger.info(
            f"[{sid}] Voice turn: ASR={asr_ms:.0f}ms "
            f"Agent={agent_time:.0f}ms "
            f"TTS={tts_ms:.0f}ms "
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
        """
        pipeline_start = time.time()

        # Step 1: ASR
        asr_result = self.asr.transcribe_bytes(audio_bytes, sample_rate=sample_rate)

        # Step 2: Agent
        agent_result = self._run_agent(session_state, asr_result.text, retrieved_cars)

        # Step 3: TTS
        tts_result = TTSResult(audio_bytes=b"", voice=self.tts.voice)
        if not skip_tts and agent_result.response_text:
            tts_result = self._synthesize_speech(agent_result.response_text)

        total_time = (time.time() - pipeline_start) * 1000
        asr_ms = (
            float(asr_result.processing_time_ms)
            if isinstance(asr_result.processing_time_ms, (int, float))
            else 0.0
        )
        tts_ms = (
            float(tts_result.processing_time_ms)
            if isinstance(tts_result.processing_time_ms, (int, float))
            else 0.0
        )
        agent_time = max(0.0, total_time - asr_ms - tts_ms)

        turn_result = VoiceTurnResult(
            user_text=str(asr_result.text) if asr_result.text is not None else "",
            asr_language=str(asr_result.language) if asr_result.language else "zh",
            asr_confidence=float(asr_result.language_probability)
            if isinstance(asr_result.language_probability, (int, float))
            else 0.0,
            asr_time_ms=asr_ms,
            agent_response=str(agent_result.response_text) if agent_result.response_text else "",
            stage=agent_result.session_state.stage.value,
            stage_changed=agent_result.stage_changed,
            agent_time_ms=agent_time,
            session_state=agent_result.session_state,
            audio_bytes=tts_result.audio_bytes
            if isinstance(tts_result.audio_bytes, bytes)
            else b"",
            audio_format=str(tts_result.audio_format) if tts_result.audio_format else "mp3",
            tts_voice=str(tts_result.voice) if tts_result.voice else "",
            tts_time_ms=tts_ms,
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
        """
        pipeline_start = time.time()

        agent_result = self._run_agent(session_state, text, retrieved_cars)
        agent_time = (time.time() - pipeline_start) * 1000

        tts_result = TTSResult(audio_bytes=b"", voice=self.tts.voice)
        if not skip_tts and agent_result.response_text:
            tts_result = self._synthesize_speech(agent_result.response_text)

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
            session_state=agent_result.session_state,
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

    async def process_text_stream_tts(
        self,
        text: str,
        session_state: SessionState,
        retrieved_cars: Optional[List[Dict[str, Any]]] = None,
        already_observed: bool = False,
    ):
        """
        Stream LLM tokens and synthesize TTS on complete sentences on-the-fly.

        Yields tuples:
        - ("metadata", {"stage": str, "stage_changed": bool, "session_state": SessionState})
        - ("sentence", {"text": sentence_str, "audio_bytes": bytes, "time_ms": float})
        - ("done", {"full_text": str, "total_time_ms": float})
        """
        import re

        start_time = time.time()

        # Step 1: Observe turn unless caller already observed (e.g. before retrieval)
        observed_state = (
            session_state if already_observed else self.agent.observe(session_state, text)
        )

        # Step 2: Stream response from agent
        sentence_buffer = ""
        full_text_parts = []
        old_stage = session_state.stage

        punctuation_regex = re.compile(r"([。！？!?\n;；]|(?<=[\u4e00-\u9fa5]{10})[，,])")

        for item in self.agent.respond_stream(observed_state, retrieved_cars=retrieved_cars):
            kind = item[0]
            if kind == "metadata":
                meta = item[1]
                stage_changed = meta["session_state"].stage != old_stage
                yield (
                    "metadata",
                    {
                        "stage": meta["session_state"].stage.value,
                        "stage_changed": stage_changed,
                        "session_state": meta["session_state"],
                    },
                )
            elif kind == "delta":
                token = item[1]
                sentence_buffer += token
                full_text_parts.append(token)

                # Check for sentence split boundary
                parts = punctuation_regex.split(sentence_buffer)
                if len(parts) > 1:
                    completed_sentence = "".join(parts[:-1]).strip()
                    sentence_buffer = parts[-1]

                    if completed_sentence:
                        tts_res = await self.tts.synthesize_async(completed_sentence)
                        yield (
                            "sentence",
                            {
                                "text": completed_sentence,
                                "audio_bytes": tts_res.audio_bytes,
                                "time_ms": tts_res.processing_time_ms,
                            },
                        )

        # Process remaining sentence tail
        remaining = sentence_buffer.strip()
        if remaining:
            tts_res = await self.tts.synthesize_async(remaining)
            yield (
                "sentence",
                {
                    "text": remaining,
                    "audio_bytes": tts_res.audio_bytes,
                    "time_ms": tts_res.processing_time_ms,
                },
            )

        total_time = (time.time() - start_time) * 1000
        yield ("done", {"full_text": "".join(full_text_parts), "total_time_ms": total_time})
