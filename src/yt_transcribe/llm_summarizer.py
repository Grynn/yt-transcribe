"""LLM summarization using LiteLLM."""

import os
from typing import Optional

from litellm import completion


def summarize_with_litellm(transcription: str, prompt: str, model: Optional[str] = None) -> str:
    """
    Summarize transcription using LiteLLM.

    Args:
        transcription: The text to summarize
        prompt: The summarization prompt
        model: Optional model name. If not provided, uses LITELLM_MODEL env var
               or defaults to gpt-4o-mini

    Returns:
        The summary text

    Environment variables:
        LITELLM_MODEL: Model to use (e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022', 'gemini/gemini-pro')
        OPENAI_API_KEY: Required for OpenAI models
        ANTHROPIC_API_KEY: Required for Claude models
        GEMINI_API_KEY: Required for Gemini models

    Examples:
        # OpenAI
        export LITELLM_MODEL="gpt-4o"
        export OPENAI_API_KEY="sk-..."

        # Claude
        export LITELLM_MODEL="claude-3-5-sonnet-20241022"
        export ANTHROPIC_API_KEY="sk-ant-..."

        # Gemini
        export LITELLM_MODEL="gemini/gemini-pro"
        export GEMINI_API_KEY="..."
    """
    if model is None:
        model = os.getenv("LITELLM_MODEL", "gpt-4o-mini")

    messages = [
        {
            "role": "system",
            "content": "You are a financial analyst helping investors extract actionable insights from content."
        },
        {
            "role": "user",
            "content": f"{prompt}\n\nTranscript:\n{transcription}"
        }
    ]

    try:
        response = completion(
            model=model,
            messages=messages,
            temperature=0.7,
        )

        return response.choices[0].message.content

    except Exception as e:
        raise RuntimeError(f"LiteLLM summarization failed: {e}") from e


def get_configured_model() -> str:
    """Get the currently configured LLM model."""
    return os.getenv("LITELLM_MODEL", "gpt-4o-mini")
