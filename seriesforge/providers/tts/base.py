"""TTS (Text-to-Speech) provider abstraction."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel


class TTSResult(BaseModel):
    """Result from TTS generation."""
    audio_url: str
    audio_path: Optional[str] = None
    duration_seconds: float = 0
    text: str = ""
    voice_id: str = ""
    metadata: Dict[str, Any] = {}


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""
    
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_format: str = "mp3",
    ) -> TTSResult:
        """Synthesize speech from text."""
        pass
    
    @abstractmethod
    async def list_voices(self) -> list:
        """List available voices."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass


class ElevenLabsProvider(TTSProvider):
    """ElevenLabs TTS provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
    
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_format: str = "mp3",
    ) -> TTSResult:
        """Synthesize speech using ElevenLabs."""
        import httpx
        
        url = f"{self.base_url}/text-to-speech/{voice_id}/stream"
        
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers={"xi-api-key": self.api_key},
                timeout=60,
            )
            
            # Save audio to file
            audio_path = f"/tmp/audio_{voice_id[:8]}.mp3"
            with open(audio_path, 'wb') as f:
                f.write(response.content)
            
            return TTSResult(
                audio_url="",  # ElevenLabs returns binary, not URL
                audio_path=audio_path,
                text=text,
                voice_id=voice_id,
                duration_seconds=len(text) / 15,  # Rough estimate
            )
    
    async def list_voices(self) -> list:
        """List available ElevenLabs voices."""
        import httpx
        
        url = f"{self.base_url}/voices"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"xi-api-key": self.api_key},
            )
            
            data = response.json()
            return [
                {
                    "voice_id": v["voice_id"],
                    "name": v["name"],
                    "category": v.get("category", "premade"),
                }
                for v in data.get("voices", [])
            ]
    
    def get_name(self) -> str:
        return "elevenlabs"


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None
    
    @property
    def client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client
    
    async def synthesize(
        self,
        text: str,
        voice_id: str = "alloy",
        output_format: str = "mp3",
    ) -> TTSResult:
        """Synthesize speech using OpenAI TTS."""
        response = await self.client.audio.speech.create(
            model="tts-1",
            voice=voice_id,
            input=text,
            response_format=output_format,
        )
        
        audio_path = f"/tmp/audio_{voice_id}.mp3"
        with open(audio_path, 'wb') as f:
            f.write(response.content)
        
        return TTSResult(
            audio_url="",
            audio_path=audio_path,
            text=text,
            voice_id=voice_id,
            duration_seconds=len(text) / 15,
        )
    
    async def list_voices(self) -> list:
        """List OpenAI TTS voices."""
        return [
            {"voice_id": "alloy", "name": "Alloy"},
            {"voice_id": "echo", "name": "Echo"},
            {"voice_id": "fable", "name": "Fable"},
            {"voice_id": "onyx", "name": "Onyx"},
            {"voice_id": "nova", "name": "Nova"},
            {"voice_id": "shimmer", "name": "Shimmer"},
        ]
    
    def get_name(self) -> str:
        return "openai"


def create_tts_provider(name: str, config: Dict[str, Any]) -> TTSProvider:
    """Factory function to create TTS provider."""
    if name == "elevenlabs":
        return ElevenLabsProvider(api_key=config.get("api_key", ""))
    elif name == "openai":
        return OpenAITTSProvider(api_key=config.get("api_key", ""))
    else:
        raise ValueError(f"Unknown TTS provider: {name}")
