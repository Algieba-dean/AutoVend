"""
Voice module — ASR, TTS, and voice pipeline for AutoVend Agent.

Provides real-time speech-to-text and text-to-speech capabilities
integrated with the SalesAgent conversation pipeline.
"""

from agent.voice.asr import WhisperASR
from agent.voice.pipeline import VoicePipeline
from agent.voice.tts import EdgeTTSService

__all__ = ["WhisperASR", "EdgeTTSService", "VoicePipeline"]
