"""
NORA Chat Module

Handles Ollama API interactions with streaming support and context management.
"""

import json
import logging
import pathlib
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

MAX_FILE_TOKENS = 2000


class OllamaChat:
    """Manages Ollama API chat interactions with streaming support."""

    def __init__(self, base_url: str, model: str) -> None:
        """
        Initialize the Ollama chat client.

        Args:
            base_url: Base URL for Ollama API
            model: Default model name to use
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        logger.debug(f"OllamaChat initialized with {base_url}, model: {model}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False
    ) -> None:
        """
        Send a chat request to Ollama API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to instance model)
            stream: Whether to stream the response

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/api/chat"
        model = model or self.model
        payload = {"model": model, "messages": messages, "stream": stream}

        logger.debug(f"Sending chat request to {url} with {len(messages)} messages")

        try:
            with requests.post(url, json=payload, stream=stream, timeout=120) as resp:
                resp.raise_for_status()

                if stream:
                    self._handle_stream(resp)
                else:
                    data = resp.json()
                    print(data["message"]["content"])

        except requests.RequestException as e:
            logger.error(f"Chat request failed: {e}")
            raise

    def _handle_stream(self, response: requests.Response) -> None:
        """
        Handle streaming response from Ollama API.

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
