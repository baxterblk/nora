"""
NORA Chat Module

Handles Ollama API interactions with streaming support and context management.
Supports both modern /api/chat and legacy /api/generate endpoints.
"""

import json
import logging
import pathlib
from typing import Any, Dict, List, Optional, Union, Generator

import requests  # type: ignore

logger = logging.getLogger(__name__)

MAX_FILE_TOKENS = 2000


class OllamaChat:
    """Manages Ollama API chat interactions with streaming support and compatibility."""

    # Candidate endpoints to probe during auto-detection
    ENDPOINT_CANDIDATES = [
        "/api/chat",  # Native Ollama v0.3.9+
        "/api/generate",  # Native Ollama < v0.3.9
        "/api/v1/generate",  # Open-WebUI
        "/v1/chat/completions",  # OpenAI-compatible proxies
    ]

    def __init__(
        self,
        base_url: str,
        model: str,
        compatibility_mode: str = "chat",
        endpoint: Optional[str] = None,
    ) -> None:
        """
        Initialize the Ollama chat client.

        Args:
            base_url: Base URL for Ollama API
            model: Default model name to use
            compatibility_mode: API endpoint mode - "chat" (default) or "generate"
                              - "chat": Use /api/chat (Ollama v0.3.9+)
                              - "generate": Use /api/generate (Ollama < v0.3.9)
            endpoint: Explicit endpoint path (e.g., "/api/chat"). If None, will auto-detect.
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.compatibility_mode = compatibility_mode
        self.endpoint = endpoint  # Manual override or None for auto-detect
        self._detected_endpoint: Optional[str] = None  # Cached detection result
        self._fallback_warned = False  # Track if we've warned about fallback
        logger.debug(
            f"OllamaChat initialized with {base_url}, model: {model}, "
            f"mode: {compatibility_mode}, endpoint: {endpoint or 'auto-detect'}"
        )

    def detect_endpoint(self) -> Optional[str]:
        """
        Auto-detect the correct API endpoint by probing candidates.

        Tries multiple endpoint paths in order and returns the first one that responds.
        Uses POST requests with minimal test payloads to accurately detect working endpoints.
        Caches the result to avoid repeated detection.

        Returns:
            Detected endpoint path or None if all candidates fail
        """
        if self._detected_endpoint:
            return self._detected_endpoint

        logger.info("Auto-detecting API endpoint...")

        for candidate in self.ENDPOINT_CANDIDATES:
            url = f"{self.base_url}{candidate}"
            try:
                # Determine if this is a chat-style or generate-style endpoint
                is_chat_style = "chat" in candidate or "completions" in candidate

                # Prepare minimal test payload
                if is_chat_style:
                    # Chat-style endpoints expect messages array
                    payload = {
                        "model": self.model,
                        "messages": [{"role": "user", "content": "test"}],
                        "stream": False,
                    }
                else:
                    # Generate-style endpoints expect prompt string
                    payload = {"model": self.model, "prompt": "test", "stream": False}

                # Send test request with timeout
                # Increased to 30s to handle slow Ollama servers
                # Some servers take 20-25s for first request after idle
                r = requests.post(url, json=payload, timeout=30)

                # 404 means endpoint doesn't exist - try next candidate
                # Any other status (even errors like 400/500) means endpoint exists
                if r.status_code != 404:
                    self._detected_endpoint = candidate
                    logger.info(
                        f"Detected endpoint: {candidate} (status: {r.status_code})"
                    )
                    return candidate
                else:
                    logger.debug(
                        f"Endpoint {candidate} returned 404, trying next candidate"
                    )

            except requests.RequestException as e:
                logger.debug(f"Endpoint {candidate} failed: {e}")
                continue

        logger.warning("No valid endpoint detected, falling back to /api/chat")
        self._detected_endpoint = "/api/chat"
        return self._detected_endpoint

    def get_endpoint(self) -> str:
        """
        Get the endpoint to use for requests.

        Returns explicit endpoint if set, otherwise performs auto-detection.

        Returns:
            Endpoint path to use
        """
        if self.endpoint:
            return self.endpoint

        if self._detected_endpoint:
            return self._detected_endpoint

        return self.detect_endpoint() or "/api/chat"

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
    ) -> Union[Optional[Dict[str, Any]], Generator[str, None, None]]:
        """
        Send a chat request to Ollama API with automatic endpoint detection.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to instance model)
            stream: Whether to stream the response

        Returns:
            Response dictionary. For streaming mode, this contains the
            accumulated response after the stream is complete.
        """
        model = model or self.model

        # Get the endpoint to use (manual override, cached detection, or auto-detect)
        endpoint_path = self.get_endpoint()

        # Determine if this is a chat-style or generate-style endpoint
        is_chat_style = "chat" in endpoint_path or "completions" in endpoint_path

        if is_chat_style:
            return self._chat_endpoint(messages, model, stream, endpoint_path)
        else:
            return self._generate_endpoint(messages, model, stream, endpoint_path)

    def _chat_endpoint(
        self,
        messages: List[Dict[str, str]],
        model: str,
        stream: bool,
        endpoint_path: str,
    ) -> Union[Optional[Dict[str, Any]], Generator[str, None, None]]:
        """
        Use chat-style endpoint (Ollama /api/chat or OpenAI-compatible).

        Args:
            messages: List of message dictionaries
            model: Model to use
            stream: Whether to stream
            endpoint_path: The endpoint path to use

        Returns:
            Response dictionary.
        """
        url = f"{self.base_url}{endpoint_path}"
        payload = {"model": model, "messages": messages, "stream": stream}

        logger.debug(f"Sending chat request to {url} with {len(messages)} messages")

        with requests.post(url, json=payload, stream=stream, timeout=120) as resp:
            resp.raise_for_status()

            if stream:
                return self._handle_stream_chat(resp)
            else:
                data = resp.json()
                # Handle both Ollama and OpenAI-style responses
                if "message" in data:
                    print(data["message"]["content"])
                elif "choices" in data:
                    print(data["choices"][0]["message"]["content"])
                return data

    def _generate_endpoint(
        self,
        messages: List[Dict[str, str]],
        model: str,
        stream: bool,
        endpoint_path: str,
    ) -> Union[Optional[Dict[str, Any]], Generator[str, None, None]]:
        """
        Returns:
            Response dictionary.
        """
        url = f"{self.base_url}{endpoint_path}"

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

        logger.debug(f"Sending generate request to {url}")

        with requests.post(url, json=payload, stream=stream, timeout=120) as resp:
            resp.raise_for_status()

            if stream:
                return self._handle_stream_generate(resp)
            else:
                data = resp.json()
                print(data["response"])
                return data

    def _handle_stream_chat(self, response: requests.Response) -> Generator[str, None, None]:
        """
        Handle streaming response from /api/chat endpoint.

        Args:
            response: Streaming HTTP response

        Yields:
            Response chunks
        """
        for line in response.iter_lines():
            if not line:
                continue

            try:
                data = json.loads(line.decode("utf-8"))
                delta = data.get("message", {}).get("content", "")
                if delta:
                    yield delta
                if data.get("done"):
                    break
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode streaming response: {e}")
                continue

    def _handle_stream_generate(self, response: requests.Response) -> Generator[str, None, None]:
        """
        Handle streaming response from /api/generate endpoint.

        Args:
            response: Streaming HTTP response

        Yields:
            Response chunks
        """
        for line in response.iter_lines():
            if not line:
                continue

            try:
                data = json.loads(line.decode("utf-8"))
                delta = data.get("response", "")
                if delta:
                    yield delta
                if data.get("done"):
                    break
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode streaming response: {e}")
                continue

    def summarize(self, text: str, model: str = "llama3:8b") -> Optional[str]:
        """
        Summarize a given text using the Ollama API.

        Args:
            text: The text to summarize.
            model: The model to use for summarization.

        Returns:
            The summarized text or None if summarization fails.
        """
        messages = [
            {"role": "system", "content": "Summarize the following text:"},
            {"role": "user", "content": text},
        ]
        try:
            response = self.chat(messages, model=model, stream=False)
            if response and "message" in response:
                return response["message"]["content"]
            elif response and "response" in response:
                return response["response"]
            return None
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return None


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
