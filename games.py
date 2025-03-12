#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Game logic for casino games
"""

import random
import logging
from telegram import Update
from telegram.ext import ContextTypes
from crypto_payments import update_user_balance, get_user_balance
from user_data import get_user_data

logger = logging.getLogger(__name__)

async def play_even_odd(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, bet_choice, bet_amount):
    """
    Play even/odd game
    
    Args:
        update: Telegram update object
        context: Context object
        user_id: User ID
        bet_choice: 'even' or 'odd'
        bet_amount: Bet amount in TON
        
    Returns:
        dict: Result information including messages and dice value
    """
    # First subtract the bet amount from user balance
    current_balance = update_user_balance(user_id, -bet_amount)
    
    # Send dice animation
    message = await update.callback_query.message.reply_dice(emoji="🎲")
    dice_value = message.dice.value
    
    # Determine if the result is even or odd
    is_even = dice_value % 2 == 0
    result_text = "Чет" if is_even else "Нечет"
    user_won = (bet_choice == "even" and is_even) or (bet_choice == "odd" and not is_even)
    
    # Format user-friendly bet choice text
    bet_choice_text = "Чет" if bet_choice == "even" else "Нечет"
    
    # Отправляем сразу дубликат сообщения с результатом броска
    # Рассчитываем выигрыш для отображения
    display_winnings = int(bet_amount * 1.5) if user_won else 0
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🎲 Результат броска: {dice_value} ({result_text})\n"
             f"Ваша ставка: {bet_choice_text} ({bet_amount} TON)\n"
             f"Результат: {'🎉 Выигрыш! +' + str(display_winnings) + ' TON' if user_won else '😢 Проигрыш! -' + str(bet_amount) + ' TON'}\n"
             f"Текущий баланс: {get_user_balance(user_id)} TON"
    )
    
    # Update balance if user won
    winnings = 0
    if user_won:
        winnings = int(bet_amount * 1.5)  # Уменьшен коэффициент с 2 до 1.5
        update_user_balance(user_id, winnings)
    
    # Format user-friendly bet choice text
    bet_choice_text = "Чет" if bet_choice == "even" else "Нечет"
    
    # Create result message for user
    user_message = (
        f"🎲 Результат игры Чет/Нечет:\n\n"
        f"Ваша ставка: {bet_choice_text} - {bet_amount} TON\n"
        f"Выпало: {dice_value} ({result_text})\n\n"
    )
    
    if user_won:
        user_message += f"🎉 Поздравляем! Вы выиграли {winnings} TON!\n"
    else:
        user_message += f"😢 К сожалению, вы проиграли {bet_amount} TON.\n"
    
    user_message += f"\nВаш текущий баланс: {get_user_balance(user_id)} TON"
    
    # Create channel message
    username = update.callback_query.from_user.username or f"user{user_id}"
    channel_message = (
        f"🎲 Игра: Чет/Нечет\n"
        f"Игрок: @{username}\n"
        f"Ставка: {bet_choice_text} - {bet_amount} TON\n"
        f"Выпало: {dice_value} ({result_text})\n"
        f"Результат: {'Выигрыш ' + str(winnings) + ' TON' if user_won else 'Проигрыш ' + str(bet_amount) + ' TON'}"
    )
    
    logger.info(f"User {user_id} played even/odd game. Bet: {bet_choice}, Amount: {bet_amount}, Result: {dice_value}, Won: {user_won}")
    
    # Создаем детальное сообщение с информацией о ставке для дублирования
    duplicate_message = (
        f"🎮 Игра: Чет/нечет\n"
        f"🎯 Ваша ставка: {bet_choice_text} ({bet_amount} TON)\n"
        f"🎲 Выпало: {dice_value} ({result_text})\n"
        f"💰 Результат: {'Выигрыш ' + str(winnings) + ' TON' if user_won else 'Проигрыш ' + str(bet_amount) + ' TON'}\n"
        f"💵 Текущий баланс: {get_user_balance(user_id)} TON\n\n"
        f"📊 Статистика игр:\n"
        f"🎮 Всего игр: {get_user_data(user_id).get('games_played', 0) + 1}\n"
        f"🎲 Игр в режиме Чет/нечет: {get_user_data(user_id).get('even_odd_games', 0) + 1}"
    )
    
    return {
        "message": user_message,
        "channel_message": channel_message,
        "duplicate_message": duplicate_message,
        "dice_value": dice_value,
        "user_won": user_won,
        "winnings": winnings if user_won else -bet_amount
    }

async def play_higher_lower(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, bet_choice, bet_amount):
    """
    Play higher/lower game
    
    Args:
        update: Telegram update object
        context: Context object
        user_id: User ID
        bet_choice: 'higher' or 'lower'
        bet_amount: Bet amount in TON
        
    Returns:
        dict: Result information including messages and dice value
    """
    # First subtract the bet amount from user balance
    current_balance = update_user_balance(user_id, -bet_amount)
    
    # Send dice animation
    message = await update.callback_query.message.reply_dice(emoji="🎲")
    dice_value = message.dice.value
    
    # Determine if the result is higher than 3 or lower than 4
    is_higher = dice_value > 3
    result_text = "Больше 3" if is_higher else "Меньше 4"
    user_won = (bet_choice == "higher" and is_higher) or (bet_choice == "lower" and not is_higher)
    
    # Format user-friendly bet choice text
    bet_choice_text = "Больше 3" if bet_choice == "higher" else "Меньше 4"
    
    # Отправляем сразу дубликат сообщения с результатом броска
    # Рассчитываем выигрыш для отображения
    display_winnings = int(bet_amount * 1.5) if user_won else 0
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🎲 Результат броска: {dice_value} ({result_text})\n"
             f"Ваша ставка: {bet_choice_text} ({bet_amount} TON)\n"
             f"Результат: {'🎉 Выигрыш! +' + str(display_winnings) + ' TON' if user_won else '😢 Проигрыш! -' + str(bet_amount) + ' TON'}\n"
             f"Текущий баланс: {get_user_balance(user_id)} TON"
    )
    
    # Update balance if user won
    winnings = 0
    if user_won:
        winnings = int(bet_amount * 1.5)  # Уменьшен коэффициент с 2 до 1.5
        update_user_balance(user_id, winnings)
    
    # Format user-friendly bet choice text
    bet_choice_text = "Больше 3" if bet_choice == "higher" else "Меньше 4"
    
    # Create result message for user
    user_message = (
        f"📊 Результат игры Больше/Меньше:\n\n"
        f"Ваша ставка: {bet_choice_text} - {bet_amount} TON\n"
        f"Выпало: {dice_value} ({result_text})\n\n"
    )
    
    if user_won:
        user_message += f"🎉 Поздравляем! Вы выиграли {winnings} TON!\n"
    else:
        user_message += f"😢 К сожалению, вы проиграли {bet_amount} TON.\n"
    
    user_message += f"\nВаш текущий баланс: {get_user_balance(user_id)} TON"
    
    # Create channel message
    username = update.callback_query.from_user.username or f"user{user_id}"
    channel_message = (
        f"📊 Игра: Больше/Меньше\n"
        f"Игрок: @{username}\n"
        f"Ставка: {bet_choice_text} - {bet_amount} TON\n"
        f"Выпало: {dice_value} ({result_text})\n"
        f"Результат: {'Выигрыш ' + str(winnings) + ' TON' if user_won else 'Проигрыш ' + str(bet_amount) + ' TON'}"
    )
    
    logger.info(f"User {user_id} played higher/lower game. Bet: {bet_choice}, Amount: {bet_amount}, Result: {dice_value}, Won: {user_won}")
    
    # Создаем детальное сообщение с информацией о ставке для дублирования
    duplicate_message = (
        f"🎮 Игра: Больше/меньше\n"
        f"🎯 Ваша ставка: {bet_choice_text} ({bet_amount} TON)\n"
        f"🎲 Выпало: {dice_value} ({result_text})\n"
        f"💰 Результат: {'Выигрыш ' + str(winnings) + ' TON' if user_won else 'Проигрыш ' + str(bet_amount) + ' TON'}\n"
        f"💵 Текущий баланс: {get_user_balance(user_id)} TON\n\n"
        f"📊 Статистика игр:\n"
        f"🎮 Всего игр: {get_user_data(user_id).get('games_played', 0) + 1}\n"
        f"📈 Игр в режиме Больше/меньше: {get_user_data(user_id).get('higher_lower_games', 0) + 1}"
    )
    
    return {
        "message": user_message,
        "channel_message": channel_message,
        "duplicate_message": duplicate_message,
        "dice_value": dice_value,
        "user_won": user_won,
        "winnings": winnings if user_won else -bet_amount
    }
