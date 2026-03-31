"""LLM provider abstraction layer."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Chat message for LLM interaction."""
    role: str  # system, user, assistant
    content: str


class ChatResponse(BaseModel):
    """Response from LLM chat."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatResponse:
        """Send chat messages and get response."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self._client = None
    
    @property
    def client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client
    
    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatResponse:
        """Send chat to OpenAI."""
        formatted_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]
        
        kwargs = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        response = await self.client.chat.completions.create(**kwargs)
        
        return ChatResponse(
            content=response.choices[0].message.content,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
        )
    
    def get_name(self) -> str:
        return "openai"


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model
        self._client = None
    
    @property
    def client(self):
        """Lazy load Anthropic client."""
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client
    
    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatResponse:
        """Send chat to Anthropic."""
        # Convert system message
        system_msg = None
        user_messages = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                user_messages.append({"role": m.role, "content": m.content})
        
        kwargs = {
            "model": self.model,
            "messages": user_messages,
            "temperature": temperature,
        }
        if system_msg:
            kwargs["system"] = system_msg
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        response = await self.client.messages.create(**kwargs)
        
        return ChatResponse(
            content=response.content[0].text,
            model=self.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            } if response.usage else None,
        )
    
    def get_name(self) -> str:
        return "anthropic"


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider - access to 100+ models through one API key."""
    
    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        self.api_key = api_key
        self.model = model
        self._client = None
    
    @property
    def client(self):
        """Lazy load OpenRouter client (OpenAI-compatible)."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1",
            )
        return self._client
    
    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatResponse:
        """Send chat to OpenRouter."""
        formatted_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]
        
        kwargs = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        response = await self.client.chat.completions.create(**kwargs)
        
        return ChatResponse(
            content=response.choices[0].message.content,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
        )
    
    def get_name(self) -> str:
        return "openrouter"


def create_provider(name: str, config: Dict[str, Any]) -> LLMProvider:
    """Factory function to create LLM provider.
    
    Supported providers:
    - openai: GPT-4o, o1, etc.
    - anthropic: Claude 3.5 Sonnet, Opus
    - openrouter: 100+ models (anthropic/claude-3.5-sonnet, openai/gpt-4o, etc.)
    """
    if name == "openai":
        return OpenAIProvider(
            api_key=config.get("api_key", ""),
            model=config.get("model", "gpt-4o"),
        )
    elif name == "anthropic":
        return AnthropicProvider(
            api_key=config.get("api_key", ""),
            model=config.get("model", "claude-3-5-sonnet-20241022"),
        )
    elif name == "openrouter":
        return OpenRouterProvider(
            api_key=config.get("api_key", ""),
            model=config.get("model", "anthropic/claude-3.5-sonnet"),
        )
    else:
        raise ValueError(f"Unknown LLM provider: {name}")
