"""
NORA Chat Module

Handles Ollama API interactions with streaming support and context management.
Supports both modern /api/chat and legacy /api/generate endpoints.
"""

import json
import logging
import pathlib
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

MAX_FILE_TOKENS = 2000


class OllamaChat:
    """Manages Ollama API chat interactions with streaming support and compatibility."""

    def __init__(self, base_url: str, model: str, compatibility_mode: str = "chat") -> None:
        """
        Initialize the Ollama chat client.

        Args:
            base_url: Base URL for Ollama API
            model: Default model name to use
            compatibility_mode: API endpoint mode - "chat" (default) or "generate"
                              - "chat": Use /api/chat (Ollama v0.3.9+)
                              - "generate": Use /api/generate (Ollama < v0.3.9)
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.compatibility_mode = compatibility_mode
        self._fallback_warned = False  # Track if we've warned about fallback
        logger.debug(f"OllamaChat initialized with {base_url}, model: {model}, mode: {compatibility_mode}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Send a chat request to Ollama API with automatic fallback.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to instance model)
            stream: Whether to stream the response

        Returns:
            Response dictionary for non-streaming, None for streaming

        Raises:
            requests.RequestException: If the API request fails
        """
        model = model or self.model

        # Try /api/chat first if in chat mode
        if self.compatibility_mode == "chat":
            try:
                return self._chat_endpoint(messages, model, stream)
            except requests.HTTPError as e:
                # If 404, try fallback to /api/generate
                if e.response.status_code == 404:
                    if not self._fallback_warned:
                        from nora.core.utils import warning
                        warning("Ollama server missing /api/chat — falling back to /api/generate compatibility mode.")
                        warning("Consider upgrading Ollama or run: nora config set ollama.compatibility generate")
                        self._fallback_warned = True
                    logger.info("Falling back to /api/generate")
                    return self._generate_endpoint(messages, model, stream)
                else:
                    raise
        else:
            # Use /api/generate directly
            return self._generate_endpoint(messages, model, stream)

    def _chat_endpoint(
        self,
        messages: List[Dict[str, str]],
        model: str,
        stream: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Use /api/chat endpoint (Ollama v0.3.9+).

        Args:
            messages: List of message dictionaries
            model: Model to use
            stream: Whether to stream

        Returns:
            Response dictionary for non-streaming, None for streaming
        """
        url = f"{self.base_url}/api/chat"
        payload = {"model": model, "messages": messages, "stream": stream}

        logger.debug(f"Sending chat request to {url} with {len(messages)} messages")

        with requests.post(url, json=payload, stream=stream, timeout=120) as resp:
            resp.raise_for_status()

            if stream:
                self._handle_stream_chat(resp)
                return None
            else:
                data = resp.json()
                print(data["message"]["content"])
                return data

    def _generate_endpoint(
        self,
        messages: List[Dict[str, str]],
        model: str,
        stream: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Use /api/generate endpoint (Ollama < v0.3.9).

        Args:
            messages: List of message dictionaries
            model: Model to use
            stream: Whether to stream

        Returns:
            Response dictionary for non-streaming, None for streaming
        """
        url = f"{self.base_url}/api/generate"

        # Convert messages to prompt format
        # Concatenate all user messages and system prompts
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"[System]: {content}")
            elif role == "user":
                prompt_parts.append(content)
            elif role == "assistant":
                prompt_parts.append(f"[Assistant]: {content}")

        prompt = "\n\n".join(prompt_parts)
        payload = {"model": model, "prompt": prompt, "stream": stream}

        logger.debug(f"Sending generate request to {url} (compatibility mode)")

        with requests.post(url, json=payload, stream=stream, timeout=120) as resp:
            resp.raise_for_status()

            if stream:
                self._handle_stream_generate(resp)
                return None
            else:
                data = resp.json()
                print(data["response"])
                return data

    def _handle_stream_chat(self, response: requests.Response) -> None:
        """
        Handle streaming response from /api/chat endpoint.

        Args:
            response: Streaming HTTP response
        """
        for line in response.iter_lines():
            if not line:
                continue

            try:
                data = json.loads(line.decode("utf-8"))
                delta = data.get("message", {}).get("content", "")
                if delta:
                    print(delta, end="", flush=True)
                if data.get("done"):
                    print()
                    break
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode streaming response: {e}")
                continue

    def _handle_stream_generate(self, response: requests.Response) -> None:
        """
        Handle streaming response from /api/generate endpoint.

        Args:
            response: Streaming HTTP response
        """
        for line in response.iter_lines():
            if not line:
                continue

            try:
                data = json.loads(line.decode("utf-8"))
                delta = data.get("response", "")
                if delta:
                    print(delta, end="", flush=True)
                if data.get("done"):
                    print()
                    break
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode streaming response: {e}")
                continue


def load_file_context(paths: Optional[List[str]]) -> str:
    """
    Load file contents for context injection.

    Args:
        paths: List of file paths to load

    Returns:
        Formatted string with file contents
    """
    if not paths:
        return ""

    ctx = []
    for p in paths:
        path = pathlib.Path(p)
        if not path.exists() or not path.is_file():
            logger.warning(f"Skipping non-existent file: {p}")
            continue

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            truncated = _trim_text(content, MAX_FILE_TOKENS)
            ctx.append(f"\n--- FILE: {path} ---\n{truncated}")
            logger.debug(f"Loaded file context: {path} ({len(content)} chars)")

        except Exception as e:
            logger.error(f"Failed to load file {p}: {e}")
            continue

    return "\n".join(ctx)


def _trim_text(text: str, limit: int) -> str:
    """
    Trim text to a maximum length.

    Args:
        text: Text to trim
        limit: Maximum character limit

    Returns:
        Trimmed text with truncation marker if needed
    """
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]..."
