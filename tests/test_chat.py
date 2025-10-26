"""Tests for NORA OllamaChat client"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from nora.core.chat import OllamaChat


class TestOllamaChat:
    """Test suite for OllamaChat"""

    def test_init_default_compatibility_mode(self):
        """Test initialization with default compatibility mode"""
        chat = OllamaChat("http://localhost:11434", "test-model")

        assert chat.base_url == "http://localhost:11434"
        assert chat.model == "test-model"
        assert chat.compatibility_mode == "chat"
        assert chat._fallback_warned is False

    def test_init_explicit_compatibility_mode(self):
        """Test initialization with explicit compatibility mode"""
        chat = OllamaChat(
            "http://localhost:11434", "test-model", compatibility_mode="generate"
        )

        assert chat.compatibility_mode == "generate"

    @patch("requests.post")
    def test_chat_endpoint_non_streaming(self, mock_post):
        """Test /api/chat endpoint without streaming"""
        # Explicitly set endpoint to skip auto-detection
        chat = OllamaChat("http://localhost:11434", "test-model", endpoint="/api/chat")

        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {"content": "Test response"},
            "done": True,
        }
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Test message"}]

        with patch("builtins.print") as mock_print:
            result = chat.chat(messages, stream=False)

        assert result["message"]["content"] == "Test response"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/chat"
        assert call_args[1]["json"]["messages"] == messages

    @patch("requests.post")
    def test_generate_endpoint_non_streaming(self, mock_post):
        """Test /api/generate endpoint without streaming"""
        # Explicitly set endpoint to /api/generate
        chat = OllamaChat(
            "http://localhost:11434", "test-model", endpoint="/api/generate"
        )

        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Test response", "done": True}
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Test message"}]

        with patch("builtins.print") as mock_print:
            result = chat.chat(messages, stream=False)

        assert result["response"] == "Test response"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        # Check that messages were converted to prompt
        assert "prompt" in call_args[1]["json"]

    @patch("requests.post")
    def test_endpoint_detection(self, mock_post):
        """Test automatic endpoint detection"""
        chat = OllamaChat("http://localhost:11434", "test-model")

        # Mock /api/chat as available (returns 200)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Detect endpoint
        detected = chat.detect_endpoint()

        assert detected == "/api/chat"
        assert chat._detected_endpoint == "/api/chat"
        # Should have tried /api/chat first with POST
        assert mock_post.call_count >= 1
        assert mock_post.call_args_list[0][0][0] == "http://localhost:11434/api/chat"

    @patch("requests.post")
    def test_endpoint_detection_fallback(self, mock_post):
        """Test endpoint detection with fallback to /api/generate"""
        chat = OllamaChat("http://localhost:11434", "test-model")

        # Mock responses: /api/chat returns 404, /api/generate succeeds
        def side_effect(*args, **kwargs):
            url = args[0]
            mock_resp = Mock()
            if "/api/chat" in url:
                mock_resp.status_code = 404
                return mock_resp
            elif "/api/generate" in url:
                mock_resp.status_code = 200
                return mock_resp
            raise requests.RequestException("Not found")

        mock_post.side_effect = side_effect

        # Detect endpoint
        detected = chat.detect_endpoint()

        assert detected == "/api/generate"
        assert chat._detected_endpoint == "/api/generate"

    @patch("requests.post")
    def test_endpoint_detection_open_webui(self, mock_post):
        """Test endpoint detection with Open-WebUI (/api/v1/generate)"""
        chat = OllamaChat("http://localhost:11434", "test-model")

        # Mock responses: first two return 404, /api/v1/generate succeeds
        def side_effect(*args, **kwargs):
            url = args[0]
            mock_resp = Mock()
            if "/api/v1/generate" in url:
                mock_resp.status_code = 200
                return mock_resp
            else:
                mock_resp.status_code = 404
                return mock_resp

        mock_post.side_effect = side_effect

        # Detect endpoint
        detected = chat.detect_endpoint()

        assert detected == "/api/v1/generate"
        assert chat._detected_endpoint == "/api/v1/generate"

    def test_manual_endpoint_override(self):
        """Test that manual endpoint setting bypasses detection"""
        chat = OllamaChat(
            "http://localhost:11434", "test-model", endpoint="/custom/endpoint"
        )

        # get_endpoint should return manual override without detection
        endpoint = chat.get_endpoint()

        assert endpoint == "/custom/endpoint"
        assert chat._detected_endpoint is None  # No detection should have happened

    def test_endpoint_caching(self):
        """Test that endpoint detection is cached"""
        chat = OllamaChat("http://localhost:11434", "test-model")
        chat._detected_endpoint = "/cached/endpoint"

        # Should return cached value without re-detection
        endpoint = chat.get_endpoint()

        assert endpoint == "/cached/endpoint"

    @patch("requests.post")
    def test_non_404_error_propagates(self, mock_post):
        """Test that errors propagate correctly"""
        chat = OllamaChat("http://localhost:11434", "test-model", endpoint="/api/chat")

        # Mock 500 error response
        mock_500_response = Mock()
        mock_500_response.status_code = 500
        mock_500_response.raise_for_status.side_effect = requests.HTTPError(
            response=mock_500_response
        )
        mock_500_response.__enter__ = Mock(return_value=mock_500_response)
        mock_500_response.__exit__ = Mock(return_value=False)
        mock_post.return_value = mock_500_response

        messages = [{"role": "user", "content": "Test message"}]

        # Should raise HTTPError
        with pytest.raises(requests.HTTPError):
            chat.chat(messages, stream=False)

    def test_message_to_prompt_conversion(self):
        """Test that messages are correctly converted to prompt format"""
        # Explicitly set endpoint to /api/generate
        chat = OllamaChat(
            "http://localhost:11434", "test-model", endpoint="/api/generate"
        )

        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"response": "I'm good", "done": True}
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_post.return_value = mock_response

            with patch("builtins.print"):
                chat.chat(messages, stream=False)

            # Get the prompt sent
            call_args = mock_post.call_args
            prompt = call_args[1]["json"]["prompt"]

            # Verify conversion
            assert "[System]: You are a helpful assistant" in prompt
            assert "Hello" in prompt
            assert "[Assistant]: Hi there!" in prompt
            assert "How are you?" in prompt

    @patch("requests.post")
    def test_streaming_chat_endpoint(self, mock_post):
        """Test streaming with /api/chat endpoint"""
        chat = OllamaChat("http://localhost:11434", "test-model", endpoint="/api/chat")

        # Mock streaming response
        mock_response = Mock()
        stream_data = [
            b'{"message": {"content": "Hello"}, "done": false}',
            b'{"message": {"content": " world"}, "done": false}',
            b'{"message": {"content": ""}, "done": true}',
        ]
        mock_response.iter_lines.return_value = stream_data
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]

        with patch("builtins.print") as mock_print:
            result = chat.chat(messages, stream=True)

        # Streaming should return the accumulated response
        assert result is not None
        assert result["message"]["content"] == "Hello world"
        # Verify print was called for output
        assert mock_print.call_count > 0

    @patch("requests.post")
    def test_streaming_generate_endpoint(self, mock_post):
        """Test streaming with /api/generate endpoint"""
        chat = OllamaChat(
            "http://localhost:11434", "test-model", endpoint="/api/generate"
        )

        # Mock streaming response
        mock_response = Mock()
        stream_data = [
            b'{"response": "Hello", "done": false}',
            b'{"response": " world", "done": false}',
            b'{"response": "", "done": true}',
        ]
        mock_response.iter_lines.return_value = stream_data
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]

        with patch("builtins.print") as mock_print:
            result = chat.chat(messages, stream=True)

        # Streaming should return the accumulated response
        assert result is not None
        assert result["response"] == "Hello world"
        # Verify print was called for output
        assert mock_print.call_count > 0
