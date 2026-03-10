"""Anthropic API client wrapper and prompt templates."""

from __future__ import annotations

import anthropic

from shared.config import ANTHROPIC_API_KEY, LLM_MODEL_FAST, LLM_MODEL_REASONING


def get_client() -> anthropic.Anthropic:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file or environment variables."
        )
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def complete(
    prompt: str,
    *,
    system: str = "",
    model: str | None = None,
    max_tokens: int = 1024,
) -> str:
    """Send a single-turn completion request and return the text response."""
    client = get_client()
    model = model or LLM_MODEL_FAST

    messages = [{"role": "user", "content": prompt}]
    kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    return response.content[0].text


def generate_recommendation(check: str, object_name: str, context: str) -> str:
    """Generate a human-readable recommendation for a Scout finding."""
    prompt = (
        f"You are a Power BI semantic model expert. A lint check found an issue.\n\n"
        f"Check: {check}\n"
        f"Object: {object_name}\n"
        f"Context: {context}\n\n"
        f"Write a specific, actionable recommendation in 1-2 sentences. "
        f"Include a concrete example value if applicable. "
        f"Keep it under 200 characters when possible."
    )
    return complete(prompt, max_tokens=256)


def generate_description(object_type: str, object_name: str, context: str) -> str:
    """Generate a proposed description for a table, column, or measure."""
    prompt = (
        f"You are a Power BI semantic model expert.\n\n"
        f"Generate a description for this {object_type} that Copilot will use to "
        f"understand its purpose. Front-load the most important information in the "
        f"first 200 characters.\n\n"
        f"Object: {object_name}\n"
        f"Context: {context}\n\n"
        f"Return only the description text, nothing else."
    )
    return complete(prompt, max_tokens=512)


def generate_synonyms(column_name: str, table_name: str, context: str) -> list[str]:
    """Generate synonym suggestions for a column."""
    prompt = (
        f"You are a Power BI semantic model expert.\n\n"
        f"Suggest 3-5 synonyms for the column '{column_name}' in table '{table_name}'. "
        f"These synonyms help Copilot match natural language questions to the right column.\n\n"
        f"Context: {context}\n\n"
        f"Return only a comma-separated list of synonyms, nothing else."
    )
    result = complete(prompt, max_tokens=128)
    return [s.strip() for s in result.split(",") if s.strip()]


def generate_narrative_summary(history_data: str) -> str:
    """Generate a natural-language summary of scan history trends (Historian)."""
    prompt = (
        f"You are a Power BI semantic model readiness analyst.\n\n"
        f"Given the following scan history data, write a 2-3 sentence executive summary "
        f"highlighting trends, improvements, and remaining gaps.\n\n"
        f"{history_data}\n\n"
        f"Be specific about categories and scores. Do not use emojis."
    )
    return complete(prompt, model=LLM_MODEL_REASONING, max_tokens=512)
