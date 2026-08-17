"""
Voice API routes — WebSocket and REST endpoints for voice interaction.

Provides:
- WebSocket endpoint for real-time voice streaming
- REST endpoint for single-turn voice processing (file upload)
- Voice session management
"""

import json
import logging
import uuid
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, UploadFile, WebSocket, WebSocketDisconnect

from src.agent.schemas import SessionState, UserProfile
from src.agent.voice.asr import WhisperASR
from src.agent.voice.pipeline import VoicePipeline
from src.agent.voice.tts import EdgeTTSService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

# Injected at startup
_pipeline: Optional[VoicePipeline] = None
_asr: Optional[WhisperASR] = None
_tts: Optional[EdgeTTSService] = None

# Voice session state store
_voice_sessions: Dict[str, SessionState] = {}


def set_voice_pipeline(pipeline: VoicePipeline) -> None:
    """Inject the VoicePipeline instance (called from main.py on startup)."""
    global _pipeline
    _pipeline = pipeline


def set_asr(asr: WhisperASR) -> None:
    """Inject ASR service."""
    global _asr
    _asr = asr


def set_tts(tts: EdgeTTSService) -> None:
    """Inject TTS service."""
    global _tts
    _tts = tts


def _get_pipeline() -> VoicePipeline:
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Voice pipeline not initialized.")
    return _pipeline


# ── REST: single-turn voice processing ─────────────────────────


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile):
    """
    Transcribe an uploaded audio file to text.

    Accepts WAV, MP3, FLAC, etc.
    Returns transcription result with text, language, and timing.
    """
    if _asr is None:
        raise HTTPException(status_code=503, detail="ASR service not initialized.")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    result = _asr.transcribe_bytes(audio_bytes)

    return {
        "text": result.text,
        "language": result.language,
        "language_probability": result.language_probability,
        "duration_seconds": result.duration_seconds,
        "processing_time_ms": result.processing_time_ms,
        "segments": [
            {
                "text": seg.text,
                "start": seg.start,
                "end": seg.end,
                "confidence": seg.confidence,
            }
            for seg in result.segments
        ],
    }


@router.post("/synthesize")
async def synthesize_speech(text: str, voice: Optional[str] = None):
    """
    Synthesize text to speech audio (MP3).

    Returns MP3 audio bytes as a streaming response.
    """
    if _tts is None:
        raise HTTPException(status_code=503, detail="TTS service not initialized.")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty text.")

    result = await _tts.synthesize_async(text, voice=voice)

    from fastapi.responses import Response

    return Response(
        content=result.audio_bytes,
        media_type="audio/mpeg",
        headers={
            "X-TTS-Voice": result.voice,
            "X-TTS-Processing-Time-Ms": str(result.processing_time_ms),
        },
    )


@router.post("/session")
async def create_voice_session(phone_number: str = ""):
    """Create a new voice chat session."""
    _get_pipeline()

    session_id = str(uuid.uuid4())
    profile = UserProfile(phone_number=phone_number)
    state = SessionState(session_id=session_id, profile=profile)
    _voice_sessions[session_id] = state

    return {
        "session_id": session_id,
        "message": "Voice session created.",
        "stage": state.stage.value,
    }


@router.post("/process")
async def process_voice_turn(file: UploadFile, session_id: str):
    """
    Process one voice turn: upload audio → ASR → Agent → TTS → response audio.

    Returns JSON with transcription, agent response, and base64-encoded audio.
    """
    import base64

    pipeline = _get_pipeline()

    state = _voice_sessions.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Voice session not found.")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    result = pipeline.process_audio_bytes(audio_bytes, state)

    # Update session state via agent result
    _voice_sessions[session_id] = pipeline.agent.memory  # state is updated in-place

    return {
        "session_id": session_id,
        "user_text": result.user_text,
        "agent_response": result.agent_response,
        "stage": result.stage,
        "stage_changed": result.stage_changed,
        "audio_base64": base64.b64encode(result.audio_bytes).decode() if result.audio_bytes else "",
        "audio_format": result.audio_format,
        "metrics": {
            "asr_time_ms": result.asr_time_ms,
            "agent_time_ms": result.agent_time_ms,
            "tts_time_ms": result.tts_time_ms,
            "total_time_ms": result.total_time_ms,
        },
    }


@router.get("/session/{session_id}/metrics")
async def get_voice_metrics(session_id: str):
    """Get accumulated voice session metrics."""
    pipeline = _get_pipeline()
    metrics = pipeline.get_session_metrics(session_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="No metrics for this session.")
    return metrics.to_dict()


@router.delete("/session/{session_id}")
async def end_voice_session(session_id: str):
    """End a voice session."""
    state = _voice_sessions.pop(session_id, None)
    if state is None:
        raise HTTPException(status_code=404, detail="Voice session not found.")
    return {"message": "Voice session ended.", "session_id": session_id}


# ── WebSocket: real-time voice streaming ────────────────────────


@router.websocket("/ws/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time voice interaction.

    Protocol:
    - Client sends binary audio chunks (WAV/PCM 16kHz 16-bit mono)
    - Client sends JSON control messages: {"type": "end_turn"} to signal end of speech
    - Server responds with JSON: {"type": "transcription", "text": ...}
    - Server responds with JSON: {"type": "response", "text": ..., "stage": ...}
    - Server responds with binary: TTS audio chunk (MP3)
    """
    pipeline = _get_pipeline()
    await websocket.accept()

    # Create or get session state
    if session_id not in _voice_sessions:
        _voice_sessions[session_id] = SessionState(session_id=session_id)

    audio_buffer = bytearray()

    logger.info(f"[{session_id}] Voice WebSocket connected.")

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                # Binary: accumulate audio data
                audio_buffer.extend(message["bytes"])

            elif "text" in message:
                # JSON control message
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON."})
                    continue

                msg_type = data.get("type", "")

                if msg_type == "start_turn":
                    # Speech started: clear old ambient silence buffer
                    audio_buffer.clear()
                    logger.info(f"[{session_id}] User speech started — audio buffer cleared.")

                elif msg_type == "end_turn":
                    # Process accumulated audio
                    if audio_buffer:
                        state = _voice_sessions[session_id]
                        logger.info(f"[{session_id}] Processing turn: {len(audio_buffer)} bytes audio.")

                        # ASR
                        asr_result = _asr.transcribe_bytes(bytes(audio_buffer), language="zh")
                        logger.info(f"[{session_id}] ASR result: '{asr_result.text}' ({asr_result.processing_time_ms}ms)")

                        await websocket.send_json(
                            {
                                "type": "transcription",
                                "text": asr_result.text,
                                "language": asr_result.language,
                                "processing_time_ms": asr_result.processing_time_ms,
                            }
                        )

                        # Agent + Streaming Sentence TTS processing
                        if asr_result.text.strip():
                            async for item in pipeline.process_text_stream_tts(asr_result.text, state):
                                kind = item[0]
                                if kind == "metadata":
                                    meta = item[1]
                                    await websocket.send_json({
                                        "type": "stage_update",
                                        "stage": meta["stage"],
                                        "stage_changed": meta["stage_changed"],
                                    })
                                elif kind == "sentence":
                                    chunk_data = item[1]
                                    sent_text = chunk_data["text"]
                                    audio_bytes = chunk_data["audio_bytes"]

                                    # Stream text chunk
                                    await websocket.send_json({
                                        "type": "response_chunk",
                                        "text": sent_text,
                                    })

                                    # Stream binary audio chunk for this sentence
                                    if audio_bytes:
                                        await websocket.send_json({
                                            "type": "tts_chunk",
                                            "format": "mp3",
                                            "size": len(audio_bytes),
                                            "text": sent_text,
                                        })
                                        await websocket.send_bytes(audio_bytes)

                                elif kind == "done":
                                    done_data = item[1]
                                    await websocket.send_json({
                                        "type": "response_done",
                                        "text": done_data["full_text"],
                                        "total_time_ms": done_data["total_time_ms"],
                                    })

                    # Clear buffer for next turn
                    audio_buffer.clear()

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "end_session":
                    break

    except WebSocketDisconnect:
        logger.info(f"[{session_id}] Voice WebSocket disconnected.")
    except Exception as e:
        logger.error(f"[{session_id}] Voice WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        logger.info(f"[{session_id}] Voice WebSocket closed.")
