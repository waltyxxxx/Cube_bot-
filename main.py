#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main entry point for the Telegram casino bot
"""

import logging
from bot import create_bot

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        # Create and run the bot
        bot = create_bot()
        bot.run_polling()
        logger.info("Bot started successfully")
    except Exception as e:
        logger.error(f"Error occurred: {e}")
