from __future__ import annotations

import json
import logging
from typing import Dict, List, Union

import openai
from openai import OpenAI
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)

from ami_meeting_svc import config

logger = logging.getLogger(__name__)


class OpenAIService:
    """Wrapper around OpenAI client with retry and JSON mode support.

    Constructor is test-friendly: accepts an explicit client, api_key, model_name.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        client: OpenAI | None = None,
    ) -> None:
        try:
            self._model_name = model_name or config.OPENAI_MODEL_NAME
            if client is not None:
                self._client = client
                return

            api_key_to_use = api_key or config.OPENAI_API_KEY
            if not api_key_to_use:
                raise RuntimeError("OPENAI API key is not configured")

            # Initialize OpenAI client
            self._client = OpenAI(api_key=api_key_to_use)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise

    @retry(
        retry=retry_if_exception_type((
            openai.RateLimitError,
            openai.APIConnectionError,
            openai.APITimeoutError,
        )),
        wait=wait_exponential(min=1, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _create_chat_completion(self, messages: List[Dict[str, str]], json_mode: bool) -> object:
        """Call the OpenAI chat completion endpoint with retries.

        Tenacity handles retry on transient network and rate limit errors.
        """
        try:
            client = self._client.with_options(timeout=60)
            kwargs = {"model": self._model_name, "messages": messages}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**kwargs)
            return response
        except Exception as e:
            logger.error(e, exc_info=True)
            raise

    def get_completion(
        self, prompt: str, system_message: str | None = None, json_mode: bool = False
    ) -> Union[str, Dict]:
        """Public method to get a completion from the OpenAI chat API.

        If json_mode is True, will request and parse a JSON object.
        Returns either the raw string content or a parsed dictionary.
        """
        try:
            messages: List[Dict[str, str]] = []
            if system_message is not None:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            response = self._create_chat_completion(messages, json_mode=json_mode)

            # Extract content: response.choices[0].message.content
            try:
                content = response.choices[0].message.content
            except Exception as e:
                logger.error("Unexpected response shape: %s", e, exc_info=True)
                raise

            if not json_mode:
                return content

            # json_mode: parse content
            try:
                parsed = json.loads(content)
                return parsed
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON response: %s", e, exc_info=True)
                raise
        except Exception as e:
            logger.error(e, exc_info=True)
            raise
