import logging
import os
from src.logger_utils import JsonRingBufferHandler

# Configure logging before importing other modules to ensure we catch their initialization logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add JSON Ring Buffer Handler for workspace/log.json
log_json_path = os.path.join(os.path.dirname(__file__), "workspace", "log.json")
json_handler = JsonRingBufferHandler(log_json_path, capacity=25)
json_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(json_handler)

logger = logging.getLogger(__name__)

from src.bot import create_bot

def main():
    logger.info("======================================")
    logger.info("Starting JumangoClaw Application...")
    logger.info("======================================")
    
    try:
        bot = create_bot()
        logger.info("Bot successfully created.")
        
        logger.info("Testing connection to Telegram servers...")
        bot_info = bot.get_me()
        logger.info(f"Successfully connected! Authorized as @{bot_info.username} (ID: {bot_info.id})")
        
        logger.info("Starting infinity polling API requests...")
        bot.infinity_polling(logger_level=logging.INFO)
        
    except Exception as e:
        logger.critical(f"Application failed to start: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
