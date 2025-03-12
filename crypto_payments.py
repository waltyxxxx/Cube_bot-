#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CryptoBot payment integration
"""

import os
import uuid
import json
import logging
import aiohttp
from user_data import get_user_data, update_user_data, save_user_data

logger = logging.getLogger(__name__)

# Get environment variables
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")
RESULTS_CHANNEL_ID = os.getenv("RESULTS_CHANNEL_ID")

# CryptoBot API URL
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"

# Track transactions
TRANSACTIONS = {}

async def create_fixed_invoice(coin_id="TON"):
    """
    Создает инвойс для выбора монеты оплаты через API CryptoBot.
    
    Используется только фиксированный инвойс IV15707697 для отображения
    интерфейса выбора валюты и произвольной суммы.

    Args:
        coin_id: Идентификатор монеты (TON, BTC, etc) - не используется
        
    Returns:
        str: URL для выбора криптовалюты и суммы оплаты
    """
    # Просто возвращаем фиксированный инвойс IV15707697, который
    # показывает страницу выбора монеты, а затем страницу ввода суммы
    # точно как на предоставленных пользователем скриншотах
    logger.warning(f"🧿 Используем только фиксированный инвойс IV15707697 для выбора монеты")
    return "https://t.me/CryptoBot?start=IV15707697"

async def create_deposit_invoice(user_id, amount, use_cryptobot_user=False, cryptobot_user_id=None):
    """
    Create a deposit invoice using CryptoBot API
    
    Args:
        user_id: Telegram user ID
        amount: Amount to deposit in TON
        use_cryptobot_user: Whether to use CryptoBot user ID for direct transfer
        cryptobot_user_id: CryptoBot user ID for direct transfer
    """
    logger.info(f"Создание счета на пополнение для пользователя {user_id} на сумму {amount} TON")
    
    # Используем только фиксированный инвойс IV15707697, который показывает
    # сначала страницу выбора валюты, а затем страницу ввода произвольной суммы
    fixed_invoice_url = "https://t.me/CryptoBot?start=IV15707697"
    logger.warning(f"💰 Используем фиксированный инвойс: {fixed_invoice_url}")
    return fixed_invoice_url

async def create_withdrawal(user_id, amount, wallet_address, use_cryptobot_user=False, cryptobot_user_id=None):
    """
    Create a withdrawal request using CryptoBot API
    
    Args:
        user_id: Telegram user ID
        amount: Amount to withdraw in TON
        wallet_address: External TON wallet address, or "cryptobot" for direct CryptoBot transfer
        use_cryptobot_user: Whether to use CryptoBot user ID for direct transfer
        cryptobot_user_id: CryptoBot user ID for direct transfer
    """
    logger.info(f"Создание запроса на вывод для пользователя {user_id} на сумму {amount} TON")
    
    # Проверка достаточности средств
    current_balance = get_user_balance(user_id)
    if current_balance < amount:
        return {
            "success": False,
            "message": f"Недостаточно средств. Ваш баланс: {current_balance} TON"
        }
    
    # Проверяем наличие токена CryptoBot
    if not CRYPTOBOT_TOKEN:
        logger.error("CryptoBot token not found.")
        return {
            "success": False,
            "message": "Ошибка: Токен CryptoBot недоступен. Обратитесь к администратору."
        }
    
    # Генерируем уникальный ID транзакции
    transaction_id = str(uuid.uuid4())
    
    # Формируем URL запроса
    url = f"{CRYPTOBOT_API_URL}/transfer"
    
    # Комиссия на вывод (можно настраивать)
    # При выводе на CryptoBot нет комиссии
    fee = 0 if use_cryptobot_user else 0.1  # TON
    net_amount = amount - fee
    
    # Готовим данные для запроса
    if use_cryptobot_user and cryptobot_user_id:
        # Прямой перевод другому пользователю CryptoBot
        payload = {
            "user_id": str(cryptobot_user_id),
            "asset": "TON",
            "amount": str(net_amount),
            "spend_id": f"withdrawal_{user_id}_{transaction_id}",
            "comment": f"Вывод средств из Casino Bot: {net_amount} TON",
            "disable_send_notification": "false"
        }
    else:
        # Перевод на внешний кошелек
        payload = {
            "asset": "TON",
            "amount": str(net_amount),
            "wallet_address": wallet_address,
            "comment": f"Withdrawal for user {user_id}"
        }
    
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN,
        "Content-Type": "application/json"
    }
    
    # Сохраняем информацию о транзакции
    TRANSACTIONS[transaction_id] = {
        "user_id": user_id,
        "type": "withdrawal",
        "amount": amount,
        "net_amount": net_amount,
        "fee": fee,
        "wallet": wallet_address if not use_cryptobot_user else f"CryptoBot: {cryptobot_user_id}",
        "status": "pending"
    }
    
    try:
        # Списываем средства заранее
        update_user_balance(user_id, -amount)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("ok"):
                    transfer_data = result.get("result", {})
                    transfer_id = transfer_data.get("transfer_id")
                    
                    # Обновляем информацию о транзакции
                    TRANSACTIONS[transaction_id]["transfer_id"] = transfer_id
                    TRANSACTIONS[transaction_id]["status"] = "completed"
                    
                    logger.info(f"Успешно создан вывод #{transfer_id} для пользователя {user_id}")
                    
                    if use_cryptobot_user:
                        return {
                            "success": True,
                            "message": f"{net_amount} TON успешно отправлены на ваш CryptoBot аккаунт.",
                            "transaction_id": transaction_id
                        }
                    else:
                        return {
                            "success": True,
                            "message": f"{net_amount} TON успешно отправлены на кошелек {wallet_address}.\nКомиссия: {fee} TON",
                            "transaction_id": transaction_id
                        }
                else:
                    error_msg = result.get("error", {}).get("message", "Unknown error")
                    logger.error(f"CryptoBot API error: {error_msg}")
                    
                    # Возвращаем средства пользователю
                    update_user_balance(user_id, amount)
                    
                    # Обновляем статус транзакции
                    TRANSACTIONS[transaction_id]["status"] = "failed"
                    TRANSACTIONS[transaction_id]["error"] = error_msg
                    
                    return {
                        "success": False,
                        "message": f"Ошибка при создании вывода: {error_msg}"
                    }
    except Exception as e:
        logger.error(f"Exception during withdrawal creation: {e}")
        
        # Возвращаем средства пользователю
        update_user_balance(user_id, amount)
        
        # Обновляем статус транзакции
        TRANSACTIONS[transaction_id]["status"] = "failed"
        TRANSACTIONS[transaction_id]["error"] = str(e)
        
        return {
            "success": False,
            "message": f"Ошибка соединения с сервисом: {str(e)}"
        }

async def check_transaction_status(transaction_id):
    """Check status of a transaction"""
    if transaction_id in TRANSACTIONS:
        return TRANSACTIONS[transaction_id]
    return None

async def get_transaction_history(user_id, limit=10):
    """Get transaction history for a user"""
    user_transactions = []
    
    for tx_id, tx_data in TRANSACTIONS.items():
        if tx_data.get("user_id") == user_id:
            tx_info = tx_data.copy()
            tx_info["transaction_id"] = tx_id
            user_transactions.append(tx_info)
    
    # Sort by timestamp if available, otherwise just return the most recent (limited)
    return user_transactions[:limit]

def get_user_balance(user_id):
    """Get user balance from user data"""
    user_data = get_user_data(user_id)
    if user_data:
        return user_data.get("balance", 0)
    return 0

def update_user_balance(user_id, amount_change):
    """Update user balance by adding/subtracting amount"""
    user_data = get_user_data(user_id)
    if user_data:
        # Ensure we don't go below zero
        user_data["balance"] = max(0, user_data.get("balance", 0) + amount_change)
        update_user_data(user_id, user_data)
        save_user_data()
        
        # Log the balance change
        if amount_change > 0:
            logger.info(f"Пополнение баланса пользователя {user_id} на {amount_change} TON. Новый баланс: {user_data['balance']} TON")
        else:
            logger.info(f"Списание с баланса пользователя {user_id} на {abs(amount_change)} TON. Новый баланс: {user_data['balance']} TON")
            
        return user_data["balance"]
    return 0

# This function would be called by a webhook handler when CryptoBot sends payment confirmation
async def process_payment_update(update_data):
    """Process payment update from CryptoBot"""
    try:
        if update_data.get("update_type") == "invoice_paid":
            invoice = update_data.get("payload", {})
            hidden_message = invoice.get("hidden_message", "")
            payment_comment = invoice.get("comment", "")
            
            # Логируем комментарий платежа для отладки
            logger.info(f"Получен платеж с комментарием: {payment_comment}")
            
            user_id = None
            transaction_id = None
            
            # Определяем тип игры и выбор пользователя из комментария
            game_type = None
            bet_choice = None
            
            # Обработка комментария для определения режима игры и выбора
            if payment_comment:
                payment_comment = payment_comment.lower().strip()
                
                # Боулинг
                if "бол" in payment_comment:
                    game_type = "bowling"
                    if "победа" in payment_comment or "выигрыш" in payment_comment:
                        bet_choice = "win"
                    elif "проигрыш" in payment_comment or "поражение" in payment_comment:
                        bet_choice = "lose"
                
                # Чет/нечет
                elif "чет" in payment_comment:
                    game_type = "even_odd"
                    if payment_comment.strip() == "чет":
                        bet_choice = "even"
                    elif payment_comment.strip() == "нечет":
                        bet_choice = "odd"
                
                # Больше/меньше
                elif "больше" in payment_comment or "меньше" in payment_comment:
                    game_type = "higher_lower"
                    if "больше" in payment_comment:
                        bet_choice = "higher"
                    elif "меньше" in payment_comment:
                        bet_choice = "lower"
            
            # Логируем определенный тип игры и выбор
            logger.info(f"Определен тип игры: {game_type}, выбор ставки: {bet_choice}")
            
            # Extract user_id and transaction_id from hidden_message
            if "user_id:" in hidden_message:
                parts = hidden_message.split(",")
                for part in parts:
                    if part.startswith("user_id:"):
                        user_id = int(part.replace("user_id:", "").strip())
                    elif part.startswith("txid:"):
                        transaction_id = part.replace("txid:", "").strip()
            
            if user_id:
                amount = float(invoice.get("amount", 0))
                asset = invoice.get("asset", "TON")
                invoice_id = invoice.get("invoice_id", "unknown")
                
                # Update user balance
                update_user_balance(user_id, amount)
                logger.info(f"Updated balance for user {user_id} with +{amount} {asset}")
                
                # Update transaction if exists
                if transaction_id and transaction_id in TRANSACTIONS:
                    TRANSACTIONS[transaction_id]["status"] = "completed"
                    TRANSACTIONS[transaction_id]["amount"] = amount
                    TRANSACTIONS[transaction_id]["asset"] = asset
                    TRANSACTIONS[transaction_id]["invoice_id"] = invoice_id
                
                # Return payment information
                return {
                    "success": True,
                    "user_id": user_id,
                    "amount": amount,
                    "asset": asset,
                    "game_type": game_type,
                    "bet_choice": bet_choice
                }
            else:
                logger.warning(f"Payment received but user_id not found. Hidden message: {hidden_message}")
                return {
                    "success": False,
                    "message": "User ID not found in payment"
                }
        else:
            logger.info(f"Non-invoice update received: {update_data.get('update_type')}")
            return {
                "success": False,
                "message": "Not an invoice_paid update"
            }
    except Exception as e:
        logger.error(f"Error processing payment update: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

async def check_payment_status(invoice_id):
    """Check status of a payment by invoice ID"""
    if not CRYPTOBOT_TOKEN:
        logger.error("CryptoBot token not found.")
        return {
            "success": False,
            "message": "CryptoBot token not available"
        }
    
    url = f"{CRYPTOBOT_API_URL}/getInvoices"
    params = {"invoice_ids": [invoice_id]}
    
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN,
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("ok"):
                    invoices = result.get("result", {}).get("items", [])
                    if invoices:
                        invoice = invoices[0]
                        return {
                            "success": True,
                            "status": invoice.get("status"),
                            "paid": invoice.get("paid"),
                            "amount": invoice.get("amount"),
                            "asset": invoice.get("asset")
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Invoice not found"
                        }
                else:
                    error_msg = result.get("error", {}).get("message", "Unknown error")
                    return {
                        "success": False,
                        "message": f"API error: {error_msg}"
                    }
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

async def test_api_connection():
    """Test connection to CryptoBot API"""
    if not CRYPTOBOT_TOKEN:
        logger.error("CryptoBot token not found.")
        return {
            "success": False,
            "message": "CryptoBot token not available"
        }
    
    url = f"{CRYPTOBOT_API_URL}/getMe"
    
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN,
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("ok"):
                    app_info = result.get("result", {})
                    return {
                        "success": True,
                        "app_id": app_info.get("app_id"),
                        "name": app_info.get("name"),
                        "payment_processing_bot_username": app_info.get("payment_processing_bot_username")
                    }
                else:
                    error_msg = result.get("error", {}).get("message", "Unknown error")
                    error_code = result.get("error", {}).get("code", None)
                    return {
                        "success": False,
                        "message": error_msg,
                        "code": error_code
                    }
    except Exception as e:
        logger.error(f"Error testing API connection: {e}")
        return {
            "success": False,
            "message": f"Connection error: {str(e)}"
        }

def validate_ton_wallet(address):
    """Validate TON wallet address format"""
    # Базовая валидация TON-адреса
    if not address:
        return False
    
    # TON addresses are typically base64 and start with "EQ" or "UQ"
    if address.startswith("EQ") or address.startswith("UQ"):
        # Check min length
        if len(address) >= 48:
            return True
    
    return False

async def create_invoice_for_transfer(user_id, amount, cryptobot_user_id):
    """
    Create an invoice request for transfer from user's CryptoBot account
    
    Args:
        user_id: Telegram user ID
        amount: Amount to request in TON
        cryptobot_user_id: CryptoBot user ID to request from
    """
    # Просто возвращаем фиксированный инвойс, как и для обычных платежей
    return "https://t.me/CryptoBot?start=IV15707697"