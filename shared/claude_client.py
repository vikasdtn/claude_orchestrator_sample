"""Claude client for LLM interactions via Bedrock."""

import json
import logging
import os
from typing import Any

import boto3

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for invoking Claude models via AWS Bedrock."""

    def __init__(
        self,
        model_id: str | None = None,
        region: str | None = None,
        max_tokens: int = 4096,
    ):
        self.model_id = model_id or os.environ.get(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"
        )
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.max_tokens = max_tokens
        self._client = None

    @property
    def client(self):
        """Lazy initialization of Bedrock runtime client."""
        if self._client is None:
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
            )
        return self._client

    def invoke(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Invoke Claude with a prompt and return the response text."""
        messages = [{"role": "user", "content": prompt}]
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        
        if system_prompt:
            body["system"] = system_prompt

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            
            response_body = json.loads(response["body"].read())
            return response_body["content"][0]["text"]
            
        except Exception as e:
            logger.error(f"Claude invocation failed: {e}")
            raise

    def invoke_with_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Invoke Claude with tool definitions and return structured response."""
        messages = [{"role": "user", "content": prompt}]
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": temperature,
            "messages": messages,
            "tools": tools,
        }
        
        if system_prompt:
            body["system"] = system_prompt

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            
            response_body = json.loads(response["body"].read())
            return self._parse_tool_response(response_body)
            
        except Exception as e:
            logger.error(f"Claude tool invocation failed: {e}")
            raise

    def _parse_tool_response(self, response: dict) -> dict[str, Any]:
        """Parse Claude's response to extract tool calls and text."""
        result = {
            "text": "",
            "tool_calls": [],
            "stop_reason": response.get("stop_reason"),
        }
        
        for content in response.get("content", []):
            if content["type"] == "text":
                result["text"] += content["text"]
            elif content["type"] == "tool_use":
                result["tool_calls"].append({
                    "id": content["id"],
                    "name": content["name"],
                    "input": content["input"],
                })
        
        return result

    def invoke_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Invoke Claude and parse response as JSON."""
        full_prompt = f"{prompt}\n\nRespond with valid JSON only, no other text."
        
        response_text = self.invoke(
            prompt=full_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )
        
        # Extract JSON from response (handle markdown code blocks)
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        return json.loads(text.strip())
