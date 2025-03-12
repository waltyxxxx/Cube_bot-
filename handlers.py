#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Handler functions for the Telegram bot commands and callbacks
"""

import os
import datetime
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from user_data import (get_user_data, update_user_data, save_user_data, 
                      get_games_played, get_registration_date, get_favorite_game)
from crypto_payments import create_deposit_invoice, test_api_connection, create_fixed_invoice

logger = logging.getLogger(__name__)

# Получаем ID канала для размещения результатов из переменных окружения
RESULTS_CHANNEL_ID = os.getenv("RESULTS_CHANNEL_ID")

async def create_payment_url(user_id, bet_amount=4.0):
    """
    Создает платежный URL для CryptoBot через фиксированный инвойс
    
    Args:
        user_id: ID пользователя Telegram
        bet_amount: Сумма ставки в USD (используется только для аналитики)
        
    Returns:
        str: URL для оплаты через CryptoBot с экраном выбора монеты и произвольной суммы
    """
    logger.info(f"Создаем платёжный счет с выбором монеты для пользователя {user_id}")
    
    # ВАЖНО! Всегда используем только фиксированный инвойс IV15707697
    # который показывает сначала страницу выбора валюты, а потом страницу с вводом суммы
    # Это прямая ссылка на предварительно созданный инвойс, который настроен для работы с произвольной суммой
    fixed_invoice_url = "https://t.me/CryptoBot?start=IV15707697"
    logger.warning(f"===DEBUG=== Созданный WebApp payment_url: {fixed_invoice_url}")
    return fixed_invoice_url

    # Закомментированный оригинальный код, который можно будет использовать позже
    """
    # Конвертируем USD в TON (приблизительно)
    ton_amount = bet_amount / 6.0  # Примерное соотношение TON/USD
    
    try:
        # Создаем инвойс через API CryptoBot
        # Получаем mini_app_invoice_url, который лучше работает для отображения окна оплаты
        invoice_url = await create_deposit_invoice(user_id, ton_amount)
        if isinstance(invoice_url, str) and invoice_url.startswith("https://"):
            logger.info(f"Создан платежный URL для пользователя {user_id}: {invoice_url}")
            return invoice_url
        else:
            logger.error(f"Ошибка при создании платежного URL: {invoice_url}")
            # В случае ошибки создаем минимальный инвойс
            fallback_url = await create_deposit_invoice(user_id, 0.1)
            if isinstance(fallback_url, str) and fallback_url.startswith("https://"):
                return fallback_url
            return "https://t.me/CryptoBot"
    except Exception as e:
        logger.error(f"Исключение при создании платежного URL: {e}")
        return "https://t.me/CryptoBot"
    """

async def send_channel_bet_message(context, user, game_type=None, bet_choice=None, bet_amount=4.0):
    """
    Отправляет сообщение о ставке в игровой канал в новом формате
    
    Args:
        context: Context объект
        user: Объект пользователя
        game_type: Тип игры ('even_odd', 'higher_lower', 'bowling') или None для универсального сообщения
        bet_choice: Выбор пользователя ('even', 'odd', 'higher', 'lower', 'win', 'lose') или None
        bet_amount: Сумма ставки в USD (по умолчанию 4.0)
    
    Returns:
        Message: Объект отправленного сообщения
    """
    # Если game_type и bet_choice указаны, конвертируем их в русские названия
    # В противном случае используем универсальное сообщение
    if game_type and bet_choice:
        # Преобразование названий в русский
        game_type_ru = {
            "higher_lower": "Больше / Меньше",
            "even_odd": "Чет / Нечет",
            "bowling": "Боулинг"
        }.get(game_type, game_type)
        
        bet_choice_ru = {
            "even": "Чет", 
            "odd": "Нечет", 
            "higher": "Больше", 
            "lower": "Меньше",
            "win": "Победа",
            "lose": "Поражение"
        }.get(bet_choice, bet_choice)
    
    # Получаем ссылку для платежа с возможностью выбора ПРОИЗВОЛЬНОЙ суммы
    logger.warning(f"🔴🔴🔴 СОЗДАНИЕ ССЫЛКИ ДЛЯ ПЛАТЕЖА С ПРОИЗВОЛЬНОЙ СУММОЙ для пользователя {user.id}")
    
    # Используем минимальную сумму 0.1 TON, реальную сумму введет пользователь 
    # в интерфейсе CryptoBot благодаря параметру allow_custom_amount="true"
    payment_url = await create_payment_url(user.id, 0.1)
    
    # Отправляем в канал сообщение с одной кнопкой для ставки напрямую в чате CryptoBot
    channel_message = await context.bot.send_message(
        chat_id=RESULTS_CHANNEL_ID,
        text=(
            f"🎮 *НОВАЯ СТАВКА* 🔥\n\n"
            f"👤 Игрок: {user.first_name}\n\n"
            f"📝 *В комментарии к платежу укажите:*\n\n"
            f"*Режим и исход:*\n"
            f"• 🎳 Боулинг: `бол - победа` или `бол - поражение`\n"
            f"• 🎲 Чет/Нечет: `чет` или `нечет`\n"
            f"• 📊 Больше/Меньше: `больше` или `меньше`\n\n"
            f"👇 *Введите удобную для вас сумму от 0.1 до 10 TON* при оплате через CryptoBot:"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Сделать ставку", url=payment_url)],
            [InlineKeyboardButton("📋 Инструкция", callback_data="instruction")]
        ])
    )
    
    return channel_message

# Main menu keyboard
def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Профиль", callback_data="profile"),
            InlineKeyboardButton("ИГРАТЬ", callback_data="play")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Game selection keyboard
def get_game_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎲 Чет/нечет", callback_data="game_even_odd")],
        [InlineKeyboardButton("📊 Больше/меньше", callback_data="game_higher_lower")],
        [InlineKeyboardButton("🎳 Боулинг", callback_data="game_bowling")],
        [InlineKeyboardButton("🧪 Тест API", callback_data="test_api")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    user = update.effective_user
    user_id = user.id
    
    # Initialize user data if first time
    user_data = get_user_data(user_id)
    if not user_data:
        user_data = {
            "user_id": user_id,
            "username": user.username or "Anonymous",
            "registration_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "games_played": 0,
            "favorite_game": None,
            "balance": 0,
            "even_odd_games": 0,
            "higher_lower_games": 0,
            "last_activity": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        update_user_data(user_id, user_data)
        save_user_data()
    
    # Check if command contains game mode parameter
    if update.message and update.message.text:
        command_parts = update.message.text.split()
        if len(command_parts) > 1:
            game_param = command_parts[1]
            if game_param.startswith("IV"):
                # Это инвойс от CryptoBot, игнорируем
                pass
    
    # Standard welcome message
    await update.effective_message.reply_text(
        "Приветствуем вас в нашем захватывающем казино! 🎰💥 Погрузитесь в мир азарта и удачи прямо сейчас!",
        reply_markup=get_main_keyboard()
    )

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle profile button click."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    games_played = get_games_played(user_id)
    registration_date = get_registration_date(user_id)
    favorite_game = get_favorite_game(user_id)
    
    games_text = f"🎮 Количество сыгранных игр: {games_played}" if games_played > 0 else "🎮 Вы еще не сыграли ни одной игры!"
    favorite_text = f"❤️ Любимый режим: {favorite_game}" if favorite_game else "❤️ У вас еще нет любимого режима игры."
    
    profile_text = (
        "👤 Ваш профиль:\n\n"
        f"{games_text}\n\n"
        f"📅 Дата регистрации: {registration_date}\n\n"
        f"{favorite_text}"
    )
    
    await query.edit_message_text(
        text=profile_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
        ])
    )

async def play_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle play button click."""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID канала из переменной окружения - для логов
    channel_id = RESULTS_CHANNEL_ID
    
    # Используем фиксированную ссылку на ваш публичный канал
    fixed_channel_url = "https://t.me/test5363627"
    
    # Используем фиксированную ссылку на канал
    channel_url = fixed_channel_url
    
    # Подробный лог для отладки
    logger.warning(f"===DEBUG=== RESULTS_CHANNEL_ID={channel_id}, type={type(channel_id)}")
    logger.warning(f"===DEBUG=== Используем фиксированную ссылку на канал: {channel_url}")
    
    # Отправляем сообщение в игровой канал
    user = query.from_user
    payment_url = await create_payment_url(user.id, 4.0)
    
    # Подробно логируем URL платежа для отладки
    logger.warning(f"===DEBUG PLAY HANDLER=== Созданный payment_url: {payment_url}")
    logger.warning(f"===DEBUG PLAY HANDLER=== Тип payment_url: {type(payment_url)}")
    
    # Проверяем валидность URL перед использованием
    valid_url = isinstance(payment_url, str) and payment_url.startswith("https://")
    
    if not valid_url:
        logger.error(f"Невалидный payment_url: {payment_url}. Используем резервный URL.")
        payment_url = "https://t.me/CryptoBot"
    
    # Отправляем универсальное сообщение о ставке в канал
    # Пользователь сам выберет режим игры при оплате через комментарий
    message = await send_channel_bet_message(context, user)
    
    # Сохраняем ID сообщения в контексте для потенциального использования позже
    if not context.user_data.get("bets"):
        context.user_data["bets"] = {}
    
    bet_id = f"{user.id}_{int(datetime.datetime.now().timestamp())}"
    context.user_data["bets"][bet_id] = {
        "game_type": "user_choice",  # Пользователь выберет при оплате
        "bet_choice": "user_choice", # Пользователь выберет при оплате
        "message_id": message.message_id if message else None,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Новое сообщение с кнопкой "Перейти в канал"
    await query.edit_message_text(
        text="💎 Хочешь испытать удачу?\n\n💰 Сообщение со ставкой отправлено в канал! Нажмите на кнопку для перехода в канал и оплаты ставки.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Перейти в канал", url=channel_url)],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
        ])
    )
    
    # Инструкция удалена по запросу

async def game_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle game selection."""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"Выбран режим игры: {query.data}")
    
    # Получаем тип игры из callback_data
    parts = query.data.split("_", 1)  # Разделяем только по первому символу '_'
    
    if len(parts) != 2:
        logger.error(f"Неверный формат callback_data: {query.data}")
        return
    
    prefix, game_type = parts
    
    # Отправляем в канал универсальное сообщение о ставке
    user = query.from_user
    
    # Отправляем универсальное сообщение о ставке, без привязки к конкретному типу игры
    # Пользователь сам выберет режим игры при оплате через комментарий
    await send_channel_bet_message(context, user, None, None)
    
    # Возвращаемся в главное меню
    await query.edit_message_text(
        text="✅ Ваша ставка принята! Переходите в канал, чтобы сделать ставку.",
        reply_markup=get_main_keyboard()
    )

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle cancel button click or unknown text messages."""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data == "back_to_main":
            await query.edit_message_text(
                text="Приветствуем вас в нашем захватывающем казино! 🎰💥 Погрузитесь в мир азарта и удачи прямо сейчас!",
                reply_markup=get_main_keyboard()
            )
    elif update.message:
        await update.message.reply_text(
            "Пожалуйста, используйте кнопки для взаимодействия с ботом.",
            reply_markup=get_main_keyboard()
        )

async def instruction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки инструкция"""
    query = update.callback_query
    await query.answer()
    
    # Создаем платежный URL для пользователя через прямую ссылку на CryptoBot WebApp
    user_id = query.from_user.id
    
    # Инструкция удалена по запросу
    instruction_text = "Для продолжения нажмите кнопку 'Сделать ставку' ниже и выберите удобную вам сумму (от 0.1 до 10 TON)"
    
    # Создаем платежный URL для прямой оплаты в чате CryptoBot с произвольной суммой
    logger.warning(f"🔴🔴🔴 СОЗДАНИЕ ССЫЛКИ В ИНСТРУКЦИИ для пользователя {user_id}")
    payment_url = await create_payment_url(user_id, 0.1)  # Используем минимальную сумму
    
    # Подробно логируем URL платежа для отладки
    logger.warning(f"===DEBUG=== Созданный WebApp payment_url: {payment_url}")
    
    # Создаем клавиатуру с кнопкой для ставки
    await query.edit_message_text(
        text=instruction_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Сделать ставку", url=payment_url)],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
        ])
    )

async def send_welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /welcome для отправки приветственного сообщения в канал"""
    # Проверяем, что команда отправлена из канала или группы
    if update.effective_chat.type in ['group', 'supergroup', 'channel']:
        try:
            # Создаем ссылку для платежа
            payment_url = await create_payment_url(context._application.bot.id)
            
            # Отправляем приветственное сообщение с кнопкой для ставки
            welcome_message = "Приветствую! *Скорее лутай кеш* ↓↓↓↓"
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=welcome_message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Сделать ставку", url=payment_url)]
                ])
            )
            logger.info(f"Отправлено приветственное сообщение в канал/группу {update.effective_chat.id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке приветственного сообщения: {e}")
            await update.message.reply_text(f"Ошибка при отправке приветственного сообщения: {e}")
    else:
        # Если команду вызвали в приватном чате с ботом
        await update.message.reply_text(
            "Эта команда предназначена для использования только в группах и каналах."
        )

async def test_api_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для тестирования API CryptoBot"""
    # Проверяем тип обновления (сообщение или callback query)
    is_callback = False
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        # Это callback query (кнопка)
        is_callback = True
        message = await query.edit_message_text("🔄 Тестирование подключения к CryptoBot API...")
    else:
        # Это обычная команда
        message = await update.message.reply_text("🔄 Тестирование подключения к CryptoBot API...")
    
    # Тестируем API подключение
    api_result = await test_api_connection()
    
    # Логируем результат для отладки
    logger.info(f"API test result: {api_result}")
    
    if api_result.get("success"):
        await message.edit_text(
            f"✅ Успешное подключение к CryptoBot API!\n\n"
            f"App ID: {api_result.get('app_id')}\n"
            f"Name: {api_result.get('name')}\n\n"
            f"Создаем тестовый платеж..."
        )
        
        # Создаем тестовый платежный URL на небольшую сумму
        user_id = update.effective_user.id
        amount = 0.1  # минимальная сумма для теста
        
        # Создаем инвойс через API с произвольной суммой
        logger.warning(f"🔴🔴🔴 СОЗДАНИЕ ТЕСТОВОГО ИНВОЙСА с произвольной суммой для пользователя {user_id}")
        # Используем минимальную сумму TON, пользователь выберет нужную сумму
        payment_url = await create_payment_url(user_id, 0.1)
        
        # Проверяем успешность создания платежного URL
        if isinstance(payment_url, str) and payment_url.startswith("https://"):
            test_success_text = (
                f"✅ Тестовый платежный URL создан успешно!\n\n"
                f"Сумма: {amount} TON\n\n"
                f"Вы можете оплатить его для полного тестирования процесса:"
            )
            
            # Инструкция удалена по запросу
            test_instructions = "Нажмите кнопку 'Оплатить тестовый счет' для проверки работоспособности"
            
            # В зависимости от типа обновления (кнопка или команда) отправляем ответ
            if is_callback:
                # Для кнопки используем edit_message_text с клавиатурой
                await message.edit_text(
                    text=test_success_text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Оплатить тестовый счет", url=payment_url)],
                        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
                    ])
                )
                
                # Отправляем инструкции как отдельное сообщение
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text=test_instructions,
                    parse_mode="Markdown"
                )
            else:
                # Для команды используем обычный reply
                await update.message.reply_text(
                    text=test_success_text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Оплатить тестовый счет", url=payment_url)]
                    ])
                )
                
                # Добавляем инструкции по проверке через видео как отдельное сообщение
                await update.message.reply_text(
                    text=test_instructions,
                    parse_mode="Markdown"
                )
        else:
            # В случае ошибки выводим детальную информацию
            error_message = payment_url if isinstance(payment_url, str) else "Неизвестная ошибка"
            error_text = f"❌ Ошибка при создании платежного URL:\n\n{error_message}"
            
            if is_callback:
                await message.edit_text(
                    text=error_text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
                    ])
                )
            else:
                await message.edit_text(error_text)
            
            # Логируем ошибку для отладки
            logger.error(f"Error creating test payment URL: {error_message}")
    else:
        error_text = f"❌ Ошибка подключения к CryptoBot API:\n\n{api_result.get('message')}"
        
        if is_callback:
            await message.edit_text(
                text=error_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
                ])
            )
        else:
            await message.edit_text(error_text)

async def chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle bot being added to or removed from a chat"""
    chat_member = update.my_chat_member
    chat_id = chat_member.chat.id
    
    if chat_member.new_chat_member.status in ["administrator", "member"]:
        logger.info(f"Бот добавлен в чат {chat_id}")
        
        # Отправляем приветственное сообщение при добавлении в группу или канал
        try:
            welcome_message = (
                "Приветствую! *Скорее лутай кеш* ↓↓↓↓"
            )
            
            # Проверяем, является ли чат каналом или группой
            chat_type = update.effective_chat.type
            logger.info(f"Тип чата: {chat_type}")
            
            # Получаем ссылку для платежа
            payment_url = await create_payment_url(context._application.bot.id)
            
            # Отправляем приветственное сообщение с кнопкой для ставки
            await context.bot.send_message(
                chat_id=chat_id,
                text=welcome_message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Сделать ставку", url=payment_url)]
                ])
            )
            logger.info(f"Отправлено приветственное сообщение в чат {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке приветственного сообщения: {e}")
    
    elif chat_member.new_chat_member.status in ["left", "kicked"]:
        logger.info(f"Бот удален из чата {chat_id}")