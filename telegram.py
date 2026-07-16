from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from Managers import ContextManager
import soundfile as sf
import numpy as np
from scipy.signal import resample_poly

import asyncio

import dotenv

usersToAllow: dict[str, list[list[str, str]]] = {}  # Dictionary to store users that require approval

class InlineKeyboard:
    def __init__(self, buttons: dict[str: str]):
        self.buttons = buttons

    def get_keyboard(self):
        keyboard = InlineKeyboardMarkup(resize_keyboard=True)
        for button in list(self.buttons.keys()):
            keyboard.add(InlineKeyboardButton(button, callback_data=self.buttons[button]))
        return keyboard

class ReplyKeyboard:
    def __init__(self, buttons: list[str]):
        self.buttons = buttons

    def get_keyboard(self):
        keyboard = InlineKeyboardMarkup(resize_keyboard=True)
        for button in self.buttons:
            keyboard.add(InlineKeyboardButton(button, callback_data=button))
        return keyboard

class PermissionMiddleware(BaseMiddleware):
    def __call__(self, handler, event, data):
        contextManager: ContextManager = data["contextManager"]
        allowed_users = contextManager.config.Telegram.allowed_users
        required_perm = getattr(handler, "required_permission", False)
        
        if required_perm and str(event.from_user.id) not in allowed_users:
            asyncio.create_task(event.answer("You are not authorized to use this bot. Please type (ALLOW {event.from_user.id}) in terminal or allowed chat to request access."))
            for user_id in allowed_users:
                msg = asyncio.create_task(data["bot"].send_message(chat_id=user_id, text=f"User {event.from_user.username} (ID: {event.from_user.id}) is requesting access to the bot.", reply_markup=InlineKeyboard({"ALLOW": f"ALLOW {event.from_user.id}", "DENY": f"DENY {event.from_user.id}"}).get_keyboard()))
                usersToAllow[event.from_user.id].append([msg.chat.id, msg.message_id])
            return  # Stop further processing of the event
        else:
            return handler(event, data)

def permission_required(permission: bool):
    def decorator(func):
        func.required_permission = permission
        return func
    return decorator


dotenv.load_dotenv()

bot = Bot(token=dotenv.getenv("TELEGRAM_API_TOKEN"))

dp = Dispatcher(bot)

dp.message.middleware(PermissionMiddleware())

@permission_required(False)
@dp.message_handler(commands=["start"])
async def start(message, contextManager: ContextManager):
    allowed_users = contextManager.config.Telegram.allowed_users
    if str(message.from_user.id) not in allowed_users:
        usersToAllow[message.from_user.id] = []
        await message.answer(f"You are not authorized to use this bot. Please type (ALLOW {message.from_user.id}) in terminal or allowed chat to request access.")
        for (user_id) in allowed_users:
            msg = await bot.send_message(chat_id=user_id, text=f"User {message.from_user.username} (ID: {message.from_user.id}) is requesting access to the bot.", reply_markup=InlineKeyboard({"ALLOW": f"ALLOW {message.from_user.id}", "DENY": f"DENY {message.from_user.id}"}).get_keyboard())
            usersToAllow[message.from_user.id].append([msg.chat.id, msg.message_id])
        return
    else:
        await message.answer("Welcome! Type your command or click the button to interact with assistant on your device.", reply_markup=ReplyKeyboard(["Previous track", "Pause", "Resume", "Next track"]).get_keyboard())

@permission_required(True)
@dp.callback_query_handler(lambda c: c.data.startswith("ALLOW") or c.data.startswith("DENY"))
async def process_callback(callback_query, contextManager: ContextManager):
    allowed_users = contextManager.config.Telegram.allowed_users
    action, user_id = callback_query.data.split()

    if action == "ALLOW" and str(user_id) not in allowed_users and callback_query.from_user.id in allowed_users:
        allowed_users.append(user_id)
        contextManager.write_config({"Telegram": {"TrustedUsersID": allowed_users}})
        for chat_id, message_id in usersToAllow.get(int(user_id), []):
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"Access request from user {user_id} has been granted by {callback_query.from_user.username if callback_query.from_user.id != chat_id else 'you'}.")
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
        del usersToAllow[int(user_id)]
        await bot.send_message(chat_id=user_id, text="Your access request has been approved. You can now use the bot. Wellcome!")
    elif action == "DENY" and str(user_id) not in allowed_users and callback_query.from_user.id in allowed_users:
        for chat_id, message_id in usersToAllow.get(int(user_id), []):
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"Access request from user {user_id} has been denied by {callback_query.from_user.username if callback_query.from_user.id != chat_id else 'you'}.")
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
        await bot.send_message(chat_id=user_id, text="Your access request has been denied. You cannot use the bot.")

@dp.message_handler(types=["text"])
@permission_required(True)
async def handle_message(message, contextManager: ContextManager):
    allowed_users = contextManager.config.Telegram.allowed_users
    if str(message.from_user.id) not in allowed_users:
        await message.answer("You are not authorized to use this bot. Please type (ALLOW {message.from_user.id}) in terminal or allowed chat to request access.")
        for user_id in allowed_users:
            msg = await bot.send_message(chat_id=user_id, text=f"User {message.from_user.username} (ID: {message.from_user.id}) is requesting access to the bot.", reply_markup=InlineKeyboard({"ALLOW": f"ALLOW {message.from_user.id}", "DENY": f"DENY {message.from_user.id}"}).get_keyboard())
            usersToAllow[message.from_user.id].append([msg.chat.id, msg.message_id])
        return

    text = message.text.strip()
    contextManager.context.libraries.logger.trace(f"Telegram message received from {message.from_user.username} (ID: {message.from_user.id}): {text}")
    contextManager.context.ConfidenceQueue.put(text)

@permission_required(True)
@dp.message_handler(types=["voice"])
async def handle_voice(message, contextManager: ContextManager):
    allowed_users = contextManager.config.Telegram.allowed_users
    if str(message.from_user.id) not in allowed_users:
        await message.answer("You are not authorized to use this bot. Please type (ALLOW {message.from_user.id}) in terminal or allowed chat to request access.")
        for user_id in allowed_users:
            msg = await bot.send_message(chat_id=user_id, text=f"User {message.from_user.username} (ID: {message.from_user.id}) is requesting access to the bot.", reply_markup=InlineKeyboard({"ALLOW": f"ALLOW {message.from_user.id}", "DENY": f"DENY {message.from_user.id}"}).get_keyboard())
            usersToAllow[message.from_user.id].append([msg.chat.id, msg.message_id])
        return

    voice = message.voice
    voice_path = f"PluginSystem/Cache/TelegramVoice/{voice.file_id}.ogg"
    await bot.download_file_by_id(voice.file_id, destination=voice_path)
    
    audio, sr = sf.read(voice_path, dtype="int16")

    # если стерео -> моно
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1).astype(np.int16)

    # ресемплинг в 16kHz
    if sr != 16000:
        audio = resample_poly(audio, 16000, sr).astype(np.int16)
    
    contextManager.context.libraries.logger.trace(f"Telegram voice received from {message.from_user.username} (ID: {message.from_user.id}): {voice.file_id}")
    contextManager.context.ConfidenceQueue.put(voice.file_id)

def TelegramThread(contextManager: ContextManager):
    dp["contextManager"] = contextManager
    # Создаем новый event loop для текущего потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Запускаем поллинг внутри этого loop
        loop.run_until_complete(dp.start_polling(bot, skip_updates=True))
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()