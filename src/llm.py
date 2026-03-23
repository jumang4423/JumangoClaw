import logging
import json
import time
from openai import OpenAI
from src.config import (
    OPENROUTER_API_KEY, SAKURA_API_KEY,
    get_system_prompt, OPENROUTER_MODEL_ID, SAKURA_MODEL_ID, MODEL_LIMITS
)
from src.tools import (
    BASH_TOOL_SCHEMA, SEND_FILE_TOOL_SCHEMA, 
    ADD_CRON_TOOL_SCHEMA, DELETE_CRON_TOOL_SCHEMA,
    ADD_ONESHOT_TOOL_SCHEMA, DELETE_ONESHOT_TOOL_SCHEMA
)

logger = logging.getLogger(__name__)

TOOLS = [
    BASH_TOOL_SCHEMA, SEND_FILE_TOOL_SCHEMA, 
    ADD_CRON_TOOL_SCHEMA, DELETE_CRON_TOOL_SCHEMA,
    ADD_ONESHOT_TOOL_SCHEMA, DELETE_ONESHOT_TOOL_SCHEMA
]

# OpenRouter client
logger.info("Initializing OpenAI Client for OpenRouter...")
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    max_retries=0,
)

# SAKURA client (primary)
sakura_client = None
if SAKURA_API_KEY:
    logger.info("Initializing OpenAI Client for SAKURA...")
    sakura_client = OpenAI(
        base_url="https://api.ai.sakura.ad.jp/v1",
        api_key=SAKURA_API_KEY,
        max_retries=0,
    )


def _build_payload_messages(messages):
    """Prepend system prompt and enforce context limits."""
    payload_messages = [{"role": "system", "content": get_system_prompt()}] + messages
    max_chars = MODEL_LIMITS.get("context_length", 256000) * 3
    current_chars = sum(len(str(m.get("content", ""))) for m in payload_messages)
    if current_chars > max_chars * 0.8:
        logger.warning(f"Context approaching model limits ({current_chars}/{max_chars}). Splitting old session context...")
        while sum(len(str(m.get("content", ""))) for m in payload_messages) > max_chars * 0.6 and len(payload_messages) > 5:
            payload_messages.pop(2)
    return payload_messages


def _call_api(client, model_id, payload_messages, provider_name, extra_body=None):
    """Make a single API call and return the response message."""
    logger.info(f"Sending request to {provider_name} model '{model_id}'...")
    kwargs = dict(
        model=model_id,
        messages=payload_messages,
        tools=TOOLS,
    )
    if extra_body:
        kwargs["extra_body"] = extra_body
    response = client.chat.completions.create(**kwargs)
    logger.info(f"Successfully received response from {provider_name}.")
    return response.choices[0].message


def get_ai_response(messages):
    """
    Sends the conversation history to the model and returns the assistant message.
    Primary: SAKURA. Fallback: OpenRouter (2 retries). If all fail, return error string.
    """
    payload_messages = _build_payload_messages(messages)

    # 1. Try SAKURA first (primary)
    if sakura_client and SAKURA_MODEL_ID:
        try:
            return _call_api(
                sakura_client, SAKURA_MODEL_ID, payload_messages, 
                "SAKURA", extra_body={"reasoning": {"enabled": True}}
            )
        except Exception as e:
            logger.warning(f"SAKURA API call failed: {str(e)}. Falling back to OpenRouter...")

    # 2. Fallback to OpenRouter (2 attempts)
    for attempt in range(2):
        try:
            return _call_api(
                openrouter_client, OPENROUTER_MODEL_ID, payload_messages,
                "OpenRouter", extra_body={"reasoning": {"enabled": True}}
            )
        except Exception as e:
            if attempt < 1:
                logger.warning(f"OpenRouter API call failed (attempt {attempt + 1}/2): {str(e)}. Waiting 60s before retrying...")
                time.sleep(60)
            else:
                logger.error(f"OpenRouter API call failed after 2 attempts: {str(e)}", exc_info=True)

    # 3. All providers failed — return error string
    error_msg = "All LLM providers failed. Please try again later."
    logger.error(error_msg)
    return error_msg
