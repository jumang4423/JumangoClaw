import logging
import json
from openai import OpenAI
from src.config import OPENROUTER_API_KEY, get_system_prompt, MODEL_ID, MODEL_LIMITS
from src.tools import BASH_TOOL_SCHEMA, SEND_FILE_TOOL_SCHEMA, ADD_CRON_TOOL_SCHEMA, DELETE_CRON_TOOL_SCHEMA

logger = logging.getLogger(__name__)

logger.info("Initializing OpenAI Client for OpenRouter...")
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def get_ai_response(messages):
    """
    Sends the conversation history to the model and returns the assistant message.
    """
    logger.info(f"Sending request to OpenRouter model '{MODEL_ID}'...")
    
    # Prepend the dynamically generated system prompt to the messages list
    payload_messages = [{"role": "system", "content": get_system_prompt()}] + messages
    
    # Enforce context limits natively based on dynamic fetched limits
    max_chars = MODEL_LIMITS.get("context_length", 256000) * 3  # Roughly 3~4 chars per token safely
    current_chars = sum(len(str(m.get("content", ""))) for m in payload_messages)
    
    if current_chars > max_chars * 0.8:
        logger.warning(f"Context approaching model limits ({current_chars}/{max_chars}). Splitting old session context...")
        while sum(len(str(m.get("content", ""))) for m in payload_messages) > max_chars * 0.6 and len(payload_messages) > 5:
            payload_messages.pop(2)

    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=payload_messages,
            tools=[BASH_TOOL_SCHEMA, SEND_FILE_TOOL_SCHEMA, ADD_CRON_TOOL_SCHEMA, DELETE_CRON_TOOL_SCHEMA],
            extra_body={"reasoning": {"enabled": True}}
        )
        logger.info("Successfully received response from OpenRouter.")
        return response.choices[0].message
    except Exception as e:
        logger.error(f"Error during OpenRouter API call: {str(e)}", exc_info=True)
        raise
