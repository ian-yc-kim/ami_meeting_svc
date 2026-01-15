import json
import pytest
from unittest.mock import MagicMock

import openai
from ami_meeting_svc.services.ai_service import OpenAIService


def _make_mock_response(content: str):
    resp = MagicMock()
    choice = MagicMock()
    msg = MagicMock()
    msg.content = content
    choice.message = msg
    resp.choices = [choice]
    return resp


def test_text_response_success():
    mock_client = MagicMock()
    mock_client.with_options.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_mock_response("hello world")

    svc = OpenAIService(client=mock_client)
    out = svc.get_completion("hi")

    assert out == "hello world"
    mock_client.with_options.assert_called_once()
    mock_client.chat.completions.create.assert_called_once()
    # ensure response_format not passed for plain text
    _, kwargs = mock_client.chat.completions.create.call_args
    assert "response_format" not in kwargs


def test_json_response_success():
    mock_client = MagicMock()
    mock_client.with_options.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_mock_response('{"a": 1}')

    svc = OpenAIService(client=mock_client)
    out = svc.get_completion("give json", json_mode=True)

    assert isinstance(out, dict)
    assert out["a"] == 1
    mock_client.chat.completions.create.assert_called_once()
    _, kwargs = mock_client.chat.completions.create.call_args
    assert kwargs.get("response_format") == {"type": "json_object"}


def test_retry_succeeds_after_transient_errors():
    mock_client = MagicMock()
    mock_client.with_options.return_value = mock_client

    success = _make_mock_response("recovered")
    # create transient RateLimitError instances
    err1 = openai.RateLimitError.__new__(openai.RateLimitError)
    err2 = openai.RateLimitError.__new__(openai.RateLimitError)

    mock_client.chat.completions.create.side_effect = [err1, err2, success]

    svc = OpenAIService(client=mock_client)
    out = svc.get_completion("please retry")

    assert out == "recovered"
    assert mock_client.chat.completions.create.call_count == 3


def test_failure_after_max_retries():
    mock_client = MagicMock()
    mock_client.with_options.return_value = mock_client

    err = openai.RateLimitError.__new__(openai.RateLimitError)
    mock_client.chat.completions.create.side_effect = [err, err, err, err, err]

    svc = OpenAIService(client=mock_client)
    with pytest.raises(openai.RateLimitError):
        svc.get_completion("never works")

    assert mock_client.chat.completions.create.call_count == 5
