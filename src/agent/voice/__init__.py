"""
Voice module — ASR, TTS, and voice pipeline for AutoVend Agent.

Provides real-time speech-to-text and text-to-speech capabilities
integrated with the SalesAgent conversation pipeline.
"""

from src.agent.voice.asr import WhisperASR
from src.agent.voice.pipeline import VoicePipeline
from src.agent.voice.tts import EdgeTTSService

__all__ = ["WhisperASR", "EdgeTTSService", "VoicePipeline"]
