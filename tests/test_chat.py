"""Tests for NORA OllamaChat client"""

import pytest
from unittest.mock import patch, Mock, MagicMock
import requests
import json

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
        chat = OllamaChat("http://localhost:11434", "test-model", compatibility_mode="generate")

        assert chat.compatibility_mode == "generate"

    @patch('requests.post')
    def test_chat_endpoint_non_streaming(self, mock_post):
        """Test /api/chat endpoint without streaming"""
        chat = OllamaChat("http://localhost:11434", "test-model", compatibility_mode="chat")

        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {"content": "Test response"},
            "done": True
        }
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Test message"}]

        with patch('builtins.print') as mock_print:
            result = chat.chat(messages, stream=False)

        assert result["message"]["content"] == "Test response"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/chat"
        assert call_args[1]["json"]["messages"] == messages

    @patch('requests.post')
    def test_generate_endpoint_non_streaming(self, mock_post):
        """Test /api/generate endpoint without streaming"""
        chat = OllamaChat("http://localhost:11434", "test-model", compatibility_mode="generate")

        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Test response",
            "done": True
        }
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Test message"}]

        with patch('builtins.print') as mock_print:
            result = chat.chat(messages, stream=False)

        assert result["response"] == "Test response"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        # Check that messages were converted to prompt
        assert "prompt" in call_args[1]["json"]

    @patch('requests.post')
    def test_404_fallback_to_generate(self, mock_post):
        """Test automatic fallback from /api/chat to /api/generate on 404"""
        chat = OllamaChat("http://localhost:11434", "test-model", compatibility_mode="chat")

        # First call: /api/chat returns 404
        mock_404_response = Mock()
        mock_404_response.status_code = 404
        mock_404_response.raise_for_status.side_effect = requests.HTTPError(response=mock_404_response)
        mock_404_response.__enter__ = Mock(return_value=mock_404_response)
        mock_404_response.__exit__ = Mock(return_value=False)

        # Second call: /api/generate succeeds
        mock_success_response = Mock()
        mock_success_response.json.return_value = {
            "response": "Fallback response",
            "done": True
        }
        mock_success_response.__enter__ = Mock(return_value=mock_success_response)
        mock_success_response.__exit__ = Mock(return_value=False)

        # Set up mock to return 404 first, then success
        mock_post.side_effect = [mock_404_response, mock_success_response]

        messages = [{"role": "user", "content": "Test message"}]

        with patch('builtins.print') as mock_print:
            with patch('nora.core.utils.warning') as mock_warning:
                result = chat.chat(messages, stream=False)

        # Verify fallback occurred
        assert result["response"] == "Fallback response"
        assert mock_post.call_count == 2

        # Check first call was /api/chat
        first_call = mock_post.call_args_list[0]
        assert first_call[0][0] == "http://localhost:11434/api/chat"

        # Check second call was /api/generate
        second_call = mock_post.call_args_list[1]
        assert second_call[0][0] == "http://localhost:11434/api/generate"

        # Verify warning was issued
        assert mock_warning.call_count == 2  # Two warning messages
        warning_messages = [call[0][0] for call in mock_warning.call_args_list]
        assert any("/api/chat" in msg for msg in warning_messages)
        assert any("nora config set" in msg for msg in warning_messages)

    @patch('requests.post')
    def test_404_fallback_warns_only_once(self, mock_post):
        """Test that 404 fallback warning appears only once per session"""
        chat = OllamaChat("http://localhost:11434", "test-model", compatibility_mode="chat")

        # Mock 404 response
        mock_404_response = Mock()
        mock_404_response.status_code = 404
        mock_404_response.raise_for_status.side_effect = requests.HTTPError(response=mock_404_response)
        mock_404_response.__enter__ = Mock(return_value=mock_404_response)
        mock_404_response.__exit__ = Mock(return_value=False)

        # Mock success response
        mock_success_response = Mock()
        mock_success_response.json.return_value = {
            "response": "Fallback response",
            "done": True
        }
        mock_success_response.__enter__ = Mock(return_value=mock_success_response)
        mock_success_response.__exit__ = Mock(return_value=False)

        # Both calls trigger 404 then success
        mock_post.side_effect = [
            mock_404_response, mock_success_response,  # First chat call
            mock_404_response, mock_success_response   # Second chat call
        ]

        messages = [{"role": "user", "content": "Test message"}]

        with patch('builtins.print'):
            with patch('nora.core.utils.warning') as mock_warning:
                # First chat call - should warn
                chat.chat(messages, stream=False)
                first_warning_count = mock_warning.call_count

                # Reset mock to count new warnings
                mock_warning.reset_mock()

                # Second chat call - should NOT warn again
                chat.chat(messages, stream=False)
                second_warning_count = mock_warning.call_count

        # First call should have warnings
        assert first_warning_count == 2
        # Second call should have no warnings
        assert second_warning_count == 0
        # Verify _fallback_warned flag was set
        assert chat._fallback_warned is True

    @patch('requests.post')
    def test_non_404_error_propagates(self, mock_post):
        """Test that non-404 errors are not caught by fallback"""
        chat = OllamaChat("http://localhost:11434", "test-model", compatibility_mode="chat")

        # Mock 500 error response
        mock_500_response = Mock()
        mock_500_response.status_code = 500
        mock_500_response.raise_for_status.side_effect = requests.HTTPError(response=mock_500_response)
        mock_500_response.__enter__ = Mock(return_value=mock_500_response)
        mock_500_response.__exit__ = Mock(return_value=False)
        mock_post.return_value = mock_500_response

        messages = [{"role": "user", "content": "Test message"}]

        # Should raise HTTPError, not fallback
        with pytest.raises(requests.HTTPError):
            chat.chat(messages, stream=False)

    def test_message_to_prompt_conversion(self):
        """Test that messages are correctly converted to prompt format"""
        chat = OllamaChat("http://localhost:11434", "test-model", compatibility_mode="generate")

        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"response": "I'm good", "done": True}
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_post.return_value = mock_response

            with patch('builtins.print'):
                chat.chat(messages, stream=False)

            # Get the prompt sent
            call_args = mock_post.call_args
            prompt = call_args[1]["json"]["prompt"]

            # Verify conversion
            assert "[System]: You are a helpful assistant" in prompt
            assert "Hello" in prompt
            assert "[Assistant]: Hi there!" in prompt
            assert "How are you?" in prompt

    @patch('requests.post')
    def test_streaming_chat_endpoint(self, mock_post):
        """Test streaming with /api/chat endpoint"""
        chat = OllamaChat("http://localhost:11434", "test-model", compatibility_mode="chat")

        # Mock streaming response
        mock_response = Mock()
        stream_data = [
            b'{"message": {"content": "Hello"}, "done": false}',
            b'{"message": {"content": " world"}, "done": false}',
            b'{"message": {"content": ""}, "done": true}'
        ]
        mock_response.iter_lines.return_value = stream_data
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]

        with patch('builtins.print') as mock_print:
            result = chat.chat(messages, stream=True)

        # Streaming returns None
        assert result is None
        # Verify print was called for output
        assert mock_print.call_count > 0

    @patch('requests.post')
    def test_streaming_generate_endpoint(self, mock_post):
        """Test streaming with /api/generate endpoint"""
        chat = OllamaChat("http://localhost:11434", "test-model", compatibility_mode="generate")

        # Mock streaming response
        mock_response = Mock()
        stream_data = [
            b'{"response": "Hello", "done": false}',
            b'{"response": " world", "done": false}',
            b'{"response": "", "done": true}'
        ]
        mock_response.iter_lines.return_value = stream_data
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]

        with patch('builtins.print') as mock_print:
            result = chat.chat(messages, stream=True)

        # Streaming returns None
        assert result is None
        # Verify print was called for output
        assert mock_print.call_count > 0
