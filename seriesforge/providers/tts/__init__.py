"""TTS providers package."""

from seriesforge.providers.tts.base import (
    TTSProvider,
    TTSResult,
    ElevenLabsProvider,
    OpenAITTSProvider,
    create_tts_provider,
)

__all__ = [
    "TTSProvider",
    "TTSResult",
    "ElevenLabsProvider",
    "OpenAITTSProvider",
    "create_tts_provider",
]
