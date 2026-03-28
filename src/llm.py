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
logger.info("Initializing OpenAI Client for SAKURA...")
sakura_client = OpenAI(
    base_url="https://api.ai.sakura.ad.jp/v1",
    api_key=SAKURA_API_KEY,
    max_retries=0,
)


def _sanitize_history(messages):
    """Ensures message history doesn't contain orphaned tool calls/responses."""
    sanitized = []
    for i, m in enumerate(messages):
        role = m.get("role")
        if role == "tool":
            # Check if any prior message is an assistant with this tool_call_id
            valid = False
            for prev in reversed(sanitized):
                if prev.get("role") == "assistant" and "tool_calls" in prev and prev["tool_calls"]:
                    ids = [tc.get("id") if isinstance(tc, dict) else tc.id for tc in prev["tool_calls"]]
                    if m.get("tool_call_id") in ids:
                        valid = True
                        break
            if valid:
                sanitized.append(m)
        elif role == "assistant" and m.get("tool_calls"):
            # Ensure it has matching tool responses later
            has_reply = False
            for j in range(i + 1, len(messages)):
                if messages[j].get("role") == "tool":
                    has_reply = True
                    break
                elif messages[j].get("role") in ["user", "assistant"]:
                    break
            if not has_reply:
                content = m.get("content")
                if not content:
                    content = "[Action interrupted or completed]"
                # Create a fresh dict with only safe fields to avoid pyre lint errors
                sanitized.append({
                    "role": "assistant",
                    "content": content
                })
            else:
                sanitized.append(m)
        else:
            sanitized.append(m)
    return sanitized

def _build_payload_messages(messages):
    """Prepend system prompt and enforce context limits safely."""
    # First sanitize raw messages
    safe_messages = _sanitize_history([m for m in messages])
    
    payload_messages = [{"role": "system", "content": str(get_system_prompt())}]
    for m in safe_messages:
        payload_messages.append(m)
        
    max_chars = int(MODEL_LIMITS.get("context_length", 256000)) * 3
    
    current_chars = sum(len(str(m.get("content", ""))) for m in payload_messages)
    if current_chars > max_chars * 0.8:
        logger.warning(f"Context approaching model limits ({current_chars}/{max_chars}). Splitting old session context...")
        # Safely remove from the beginning (index 1), ensuring we don't break tool pairs
        while sum(len(str(m.get("content", ""))) for m in payload_messages) > max_chars * 0.6 and len(payload_messages) > 5:
            # Pop index 1 (the oldest non-system message)
            popped = payload_messages.pop(1)
            # If we just popped an assistant with tool_calls, we must pop the corresponding tool messages
            if isinstance(popped, dict) and popped.get("role") == "assistant" and popped.get("tool_calls"):
                while len(payload_messages) > 1 and isinstance(payload_messages[1], dict) and payload_messages[1].get("role") == "tool":
                    payload_messages.pop(1)
            
    # Final sanitize just to be absolutely sure after popping
    if len(payload_messages) > 1:
        sys_prompt = payload_messages[0]
        rest_messages = [m for m in payload_messages[1:]]
        final_safe = _sanitize_history(rest_messages)
        return [sys_prompt] + final_safe
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
    
    message = response.choices[0].message
    # Strip reasoning for SAKURA if present
    if provider_name == "SAKURA" and message.content and "</think>" in message.content:
        logger.info("Stripping reasoning from SAKURA response...")
        message.content = message.content.split("</think>")[-1].strip()
        
    return message


def get_ai_response(messages):
    """
    Sends the conversation history to the model and returns the assistant message.
    Primary: OpenRouter. Fallback: SAKURA. If both fail, return error string.
    """
    payload_messages = _build_payload_messages(messages)

    # 1. Try OpenRouter first (primary)
    try:
        return _call_api(
            openrouter_client, OPENROUTER_MODEL_ID, payload_messages,
            "OpenRouter", extra_body={"reasoning": {"enabled": True}}
        )
    except Exception as e:
        logger.warning(f"OpenRouter API call failed: {str(e)}. Falling back to SAKURA...")

    # 2. Fallback to SAKURA
    try:
        return _call_api(
            sakura_client, SAKURA_MODEL_ID, payload_messages, 
            "SAKURA", extra_body={"reasoning": {"enabled": True}}
        )
    except Exception as e:
        logger.error(f"SAKURA API call failed as fallback: {str(e)}", exc_info=True)

    # 3. All providers failed — return error string
    error_msg = "All LLM providers failed. Please try again later."
    logger.error(error_msg)
    return error_msg
