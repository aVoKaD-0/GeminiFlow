from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.models import User
from services.user_service import UserService
from services.chat_service import ChatService
from services.gemini_service import GeminiService
from services.context_manager import ContextManager
from services.chat_settings_service import ChatSettingsService
from utils.formatting import format_response_html_chunks
import asyncio
import mimetypes
from keyboards import get_chats_keyboard, get_cancel_keyboard, get_confirm_keyboard, get_chat_settings_keyboard, get_create_new_chat_keyboard
from states import ChatStates
import config
import logging
import uuid
from typing import Dict, Any, List
from database import async_session

logger = logging.getLogger(__name__)

router = Router()
gemini_service = GeminiService()
context_manager = ContextManager()
chat_settings_service = ChatSettingsService()

# Временное хранилище медиа-групп (альбомов), чтобы обрабатывать их одним запросом
MEDIA_GROUPS: Dict[str, Dict[str, Any]] = {}

async def _process_media_group(group_id: str, bot):
    # Небольшая задержка, чтобы дождаться всех сообщений альбома
    await asyncio.sleep(1.0)
    group = MEDIA_GROUPS.pop(group_id, None)
    if not group:
        return

    user_id: int = group["user_id"]
    tg_chat_id: int = group["tg_chat_id"]
    captions: List[str] = group.get("captions", [])
    combined_caption = " \n".join([c for c in captions if c])

    status_message = await bot.send_message(tg_chat_id, "Обрабатываю альбом...", parse_mode="HTML")

    async with async_session() as session:
        # Получаем пользователя и текущий чат
        user = await UserService.get_or_create_user(session, user_id)
        if not user.api_key_encrypted:
            await bot.send_message(tg_chat_id, "🔑 Для работы с файлами нужен API ключ. Используйте /api_key")
            return
        current_chat = await UserService.get_current_chat(session, user_id)
        if not current_chat:
            await bot.send_message(tg_chat_id, "❌ Активный чат не найден. Используйте /start для создания чата.")
            return

        history = await ChatService.get_chat_messages(session, current_chat.id)

        try:
            if group["type"] == "photo":
                # Скачиваем все изображения
                images: List[Dict[str, bytes]] = []
                for p in group.get("photos", []):
                    file = await bot.get_file(p["file_id"])
                    file_bytes = await bot.download_file(file.file_path)
                    images.append({"mime_type": "image/jpeg", "data": file_bytes.read()})

                response = await gemini_service.generate_response_with_images_batch(
                    encrypted_api_key=user.api_key_encrypted,
                    history_messages=history,
                    images=images,
                    caption=combined_caption,
                    model_name=current_chat.model_name,
                )

                # Логируем в БД
                await ChatService.add_message(session=session, chat_id=current_chat.id, user_id=user_id, role="user", content=f"[Фото x{len(images)}] {combined_caption}")
                await ChatService.add_message(session=session, chat_id=current_chat.id, user_id=user_id, role="model", content=response)

                # Ответ пользователю
                chunks = format_response_html_chunks(response)
                await status_message.edit_text(chunks[0], parse_mode="HTML")
                for chunk in chunks[1:]:
                    await status_message.edit_text(chunk, parse_mode="HTML")

            elif group["type"] == "document":
                files: List[Dict[str, bytes]] = []
                for d in group.get("documents", []):
                    file = await bot.get_file(d["file_id"])
                    file_bytes_io = await bot.download_file(file.file_path)
                    files.append({"mime_type": d.get("mime_type", "application/octet-stream"), "data": file_bytes_io.read()})

                response = await gemini_service.generate_response_with_files_batch(
                    encrypted_api_key=user.api_key_encrypted,
                    history_messages=history,
                    files=files,
                    prompt=combined_caption or "Проанализируй вложения и ответь кратко по сути.",
                    model_name=current_chat.model_name,
                )

                await ChatService.add_message(session=session, chat_id=current_chat.id, user_id=user_id, role="user", content=f"[Файлы x{len(files)}] {combined_caption}")
                await ChatService.add_message(session=session, chat_id=current_chat.id, user_id=user_id, role="model", content=response)

                chunks = format_response_html_chunks(response)
                await status_message.edit_text(chunks[0], parse_mode="HTML")
                for chunk in chunks[1:]:
                    await status_message.edit_text(chunk, parse_mode="HTML")

        except Exception as e:
            await bot.send_message(tg_chat_id, f"❌ Произошла ошибка: {str(e)}")

@router.callback_query(F.data == "manage_chats")
async def manage_chats(callback: CallbackQuery, user: User, session, has_premium: bool, **kwargs):
    chats = await ChatService.get_user_chats(session, user.telegram_id)
    current_chat = await UserService.get_current_chat(session, user.telegram_id)
    current_chat_id = current_chat.id if current_chat else None
    
    text = f"""💬 <b>Управление чатами</b>

📊 <b>Статистика:</b>
• Чатов: {len(chats)}/{config.PREMIUM_CHAT_LIMIT if has_premium else config.FREE_CHAT_LIMIT}
• Статус: {"Premium" if has_premium else "Free"}
• Активный чат: {current_chat.title if current_chat else "Не выбран"}

Выберите чат или создайте новый:"""

    await callback.message.edit_text(
        text,
        reply_markup=get_chats_keyboard(chats, current_chat_id, has_premium),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("chats"))
async def chats(callback: CallbackQuery, user: User, session, **kwargs):
    await manage_chats(callback, user, session, **kwargs)


# @router.callback_query(F.data.startswith("select_chat:"))
# async def select_chat(callback: CallbackQuery, user: User, session, **kwargs):
#     chat_id_str = callback.data.split(":")[1]
#     try:
#         chat_id: uuid.uuid4(chat_id_str)
#         chat = await ChatService.get_chat(session, chat_id, user.telegram_id)
        
#         if chat:
#             await UserService.set_current_chat(session, user.telegram_id, chat_id)
#             await callback.answer(f"✅ Выбран чат: {chat.title}")
            
#             # Update keyboard
#             chats = await ChatService.get_user_chats(session, user.telegram_id)
#             has_premium = await UserService.has_premium_access(session, user.telegram_id)
            
#             text = f"""💬 <b>Управление чатами</b>

# 📊 <b>Статистика:</b>
# • Чатов: {len(chats)}/{config.PREMIUM_CHAT_LIMIT if has_premium else config.FREE_CHAT_LIMIT}
# • Статус: {"Premium" if has_premium else "Free"}
# • Активный чат: {chat.title}

# Выберите чат или создайте новый:"""

#             await callback.message.edit_text(
#                 text,
#                 reply_markup=get_chats_keyboard(chats, chat_id, has_premium),
#                 parse_mode="HTML"
#             )
#         else:
#             await callback.answer("❌ Чат не найден", show_alert=True)
    
#     except ValueError:
#         await callback.answer("❌ Неверный ID чата", show_alert=True)

@router.callback_query(F.data.startswith("select_chat:"))
async def switch_chat(callback: CallbackQuery, user: User, session, has_premium: bool, **kwargs):
    """Переключение между чатами."""
    try:
        chat_id_str = callback.data.split(":")[1]
        chat_id = uuid.UUID(chat_id_str)

        # Проверяем, что чат существует и принадлежит пользователю
        chat = await ChatService.get_chat(session, chat_id, user.telegram_id)
        if not chat:
            logger.error(f"Ошибка переключения чата: {chat_id}")
            await callback.answer("❌ Ошибка переключения чата.", show_alert=True)
            return

        # Делаем выбранный чат текущим
        await UserService.set_current_chat(session, user.telegram_id, chat_id)

        # Получаем информацию о новом активном чате и его настройках
        chat_info = await chat_settings_service.get_chat_info(session, chat_id, user.telegram_id)
        if not chat_info:
            logger.error(f"Ошибка получения информации о чате: {chat_id}")
            await callback.answer("❌ Ошибка получения информации о чате.", show_alert=True)
            return

        # Формируем текст сообщения с информацией о чате
        info_text = (
            f"💬 <b>Текущий чат:</b> {chat_info['title']}\n"
            f"🤖 <b>Модель:</b> {chat_info['model_name']}\n"
            f"🌡️ <b>Температура:</b> {chat_info['temperature']}\n"
            # f"💬 <b>Сообщений:</b> {chat_info['message_count']}\n" # Если добавили подсчет
            f"🎭 <b>Личность:</b> {chat_info['system_prompt'][:50]}{'...' if len(chat_info['system_prompt']) > 50 else 'Не задан'}\n"
            f"🎲 <b>Top-P:</b> {chat_info['top_p'] if chat_info['top_p'] is not None else 'Не задан'}\n"
            f"🎲 <b>Top-K:</b> {chat_info['top_k'] if chat_info['top_k'] is not None else 'Не задан'}\n"
            "\n"
            "📎 <b>Поддерживаемые вложения</b>:\n"
            "• Изображения: JPEG, PNG, WebP\n"
            "• Документы: PDF, TXT/MD, JSON, CSV\n"
            "• Не принимаются: архивы (ZIP/RAR), исполняемые\n\n"
            "Начинайте общение!"
        )


        # Отправляем новое сообщение с информацией и кнопками настроек
        # Вместо редактирования старого сообщения
        await callback.message.delete() # Удаляем предыдущее сообщение с кнопками чатов
        await callback.message.answer(info_text, reply_markup=get_chat_settings_keyboard(chat_id), parse_mode="HTML")
        await callback.answer() # Простой ответ на callback

    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка при переключении чата: {e}")
        await callback.answer("❌ Неверный формат данных.", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при переключении чата: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)

@router.callback_query(F.data == "create_chat")
async def request_chat_title(callback: CallbackQuery, state: FSMContext, user: User, session, **kwargs):
    can_create = await UserService.can_create_chat(session, user.telegram_id)
    
    if not can_create:
        await callback.answer("🔒 Достигнут лимит чатов. Приобретите Premium для создания дополнительных чатов.", show_alert=True)
        return
    
    await state.set_state(ChatStates.waiting_for_title)
    
    await callback.message.edit_text(
        "💬 <b>Создание нового чата</b>\n\nВведите название для нового чата:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ChatStates.waiting_for_title)
async def create_new_chat(message: Message, state: FSMContext, user: User, session, has_premium: bool, **kwargs):
    title = message.text.strip()
    
    if not title or len(title) > 50:
        await message.answer("❌ Название должно быть от 1 до 50 символов.")
        return
    
    can_create = await UserService.can_create_chat(session, user.telegram_id)
    if not can_create:
        await message.answer("❌ Достигнут лимит чатов.")
        await state.clear()
        return
    
    # Determine model based on subscription
    model_name = "gemini-2.5-flash" if not has_premium else "gemini-2.5-pro"
    
    try:
        chat = await ChatService.create_chat(session, user.telegram_id, title, model_name)
        await UserService.set_current_chat(session, user.telegram_id, chat.id)
        
        await message.answer(
            text=f"✅ Чат '{title}' создан и активирован!\n"
            f"🤖 Модель: {model_name}\n\n"
            "Можете начинать общение!",
            reply_markup=get_create_new_chat_keyboard(chat.id)
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании чата: {str(e)}")
        await state.clear()

@router.callback_query(F.data.startswith("rename_chat:"))
async def request_rename(callback: CallbackQuery, state: FSMContext, **kwargs):
    chat_id_str = callback.data.split(":")[1]
    await state.update_data(rename_chat_id=chat_id_str)
    await state.set_state(ChatStates.waiting_for_rename)
    
    await callback.message.edit_text(
        "✏️ <b>Переименование чата</b>\n\nВведите новое название:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ChatStates.waiting_for_rename)
async def rename_chat(message: Message, state: FSMContext, user: User, session, **kwargs):
    title = message.text.strip()
    
    if not title or len(title) > 50:
        await message.answer("❌ Название должно быть от 1 до 50 символов.")
        return
    
    data = await state.get_data()
    chat_id_str = data.get("rename_chat_id")
    
    try:
        chat_id = uuid.UUID(chat_id_str)
        success = await ChatService.rename_chat(session, chat_id, user.telegram_id, title)
        
        if success:
            await message.answer(f"✅ Чат переименован в '{title}'")
        else:
            await message.answer("❌ Чат не найден")
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный ID чата")
        await state.clear()

@router.callback_query(F.data.startswith("delete_chat:"))
async def confirm_delete_chat(callback: CallbackQuery, **kwargs):
    chat_id_str = callback.data.split(":")[1]
    
    await callback.message.edit_text(
        "🗑 <b>Удаление чата</b>\n\n⚠️ Все сообщения будут безвозвратно удалены.\n\nВы уверены?",
        reply_markup=get_confirm_keyboard(f"delete_chat:{chat_id_str}"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm:delete_chat:"))
async def delete_chat(callback: CallbackQuery, user: User, session, **kwargs):
    chat_id_str = callback.data.split(":")[2]
    
    try:
        chat_id = uuid.UUID(chat_id_str)
        success = await ChatService.delete_chat(session, chat_id, user.telegram_id)
        
        if success:
            # If this was the current chat, reset current chat
            current_chat = await UserService.get_current_chat(session, user.telegram_id)
            if not current_chat:
                # Set first available chat as current
                chats = await ChatService.get_user_chats(session, user.telegram_id)
                if chats:
                    await UserService.set_current_chat(session, user.telegram_id, chats[0].id)
            
            await callback.answer("✅ Чат удален")
            
            # Return to chat management
            chats = await ChatService.get_user_chats(session, user.telegram_id)
            current_chat = await UserService.get_current_chat(session, user.telegram_id)
            has_premium = await UserService.has_premium_access(session, user.telegram_id)
            current_chat_id = current_chat.id if current_chat else None
            
            text = f"""💬 <b>Управление чатами</b>

📊 <b>Статистика:</b>
• Чатов: {len(chats)}/{config.PREMIUM_CHAT_LIMIT if has_premium else config.FREE_CHAT_LIMIT}
• Статус: {"Premium" if has_premium else "Free"}
• Активный чат: {current_chat.title if current_chat else "Не выбран"}

Выберите чат или создайте новый:"""

            await callback.message.edit_text(
                text,
                reply_markup=get_chats_keyboard(chats, current_chat_id, has_premium),
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Чат не найден", show_alert=True)
    
    except ValueError:
        await callback.answer("❌ Неверный ID чата", show_alert=True)

# Handle regular messages (chat with Gemini)
@router.message(F.text & ~F.text.startswith('/'))
async def handle_message(message: Message, user: User, session, **kwargs):
    # Check if user has API key
    if not user.api_key_encrypted:
        await message.answer(
            "🔑 Для общения с Gemini необходимо добавить API ключ.\n\n"
            "Используйте /start для настройки."
        )
        return
    
    # Get current chat
    current_chat = await UserService.get_current_chat(session, user.telegram_id)
    if not current_chat:
        await message.answer("❌ Активный чат не найден. Используйте /start для создания чата.")
        return
    
    # Send typing indicator
    status_message = await message.answer("🤖 <b>[Gemini Flow]</b> Печатает...", parse_mode="HTML")
    
    try:
        # Add user message to database
        await ChatService.add_message(session=session, chat_id=current_chat.id, user_id=user.telegram_id, role="user", content=message.text)
        
        # Get chat history
        messages = await ChatService.get_chat_messages(session, current_chat.id)
        
        # Prepare context (with summarization if needed)
        prepared_messages = await context_manager.prepare_context(messages, user.api_key_encrypted, current_chat.model_name)
        
        # Generate response
        response = await gemini_service.generate_response(
            user.api_key_encrypted, 
            prepared_messages, 
            current_chat.model_name
        )
        
        # Add AI response to database
        await ChatService.add_message(session=session, chat_id=current_chat.id, user_id=user.telegram_id, role="model", content=response)
        
        # Красиво отформатируем (HTML) и разобьём на чанки
        chunks = format_response_html_chunks(response)
        # Первый чанк редактируем в статусном сообщении
        await status_message.edit_text(chunks[0], parse_mode="HTML")
        # Остальные — отдельными сообщениями
        for chunk in chunks[1:]:
            await message.answer(chunk, parse_mode="HTML")
        
    except ValueError as e:
        await status_message.edit_text(f"❌ {str(e)}", parse_mode=None)
    except Exception as e:
        # Отключаем парсинг HTML/Markdown на время вывода ошибки, чтобы избежать конфликта с угловыми скобками
        await status_message.edit_text(f"❌ Произошла ошибка: {str(e)}", parse_mode=None)

@router.message(F.photo)
async def handle_photo(message: Message, user: User, session, has_premium: bool, **kwargs):
    # Обработка альбомов: группируем по media_group_id и выполняем 1 запрос
    if getattr(message, "media_group_id", None):
        group_id = message.media_group_id
        grp = MEDIA_GROUPS.setdefault(group_id, {"type": "photo", "photos": [], "captions": [], "user_id": user.telegram_id, "tg_chat_id": message.chat.id})
        # Проверка лимита на размер отдельного фото
        largest = message.photo[-1]
        size_limit_mb = config.FILE_SIZE_LIMIT_PREMIUM_MB if has_premium else config.FILE_SIZE_LIMIT_FREE_MB
        if getattr(largest, "file_size", None) and largest.file_size > size_limit_mb * 1024 * 1024:
            await message.answer(f"❌ Одно из фото слишком большое (> {size_limit_mb} MB).")
            return
        grp["photos"].append({"file_id": largest.file_id})
        if message.caption:
            grp["captions"].append(message.caption)
        # Стартуем отложенную обработку, если впервые увидели группу
        if "_scheduled" not in grp:
            grp["_scheduled"] = True
            asyncio.create_task(_process_media_group(group_id, message.bot))
        return
    # Проверка API-ключа
    if not user.api_key_encrypted:
        await message.answer(
            "🔑 Для работы с изображениями нужен API ключ. Используйте /api_key",
        )
        return
    # Текущий чат
    current_chat = await UserService.get_current_chat(session, user.telegram_id)
    if not current_chat:
        await message.answer("❌ Активный чат не найден. Используйте /start для создания чата.")
        return

    # Проверка размера фото (берём самый крупный вариант)
    largest_photo = message.photo[-1]
    size_limit_mb = config.FILE_SIZE_LIMIT_PREMIUM_MB if has_premium else config.FILE_SIZE_LIMIT_FREE_MB
    if getattr(largest_photo, "file_size", None) and largest_photo.file_size > size_limit_mb * 1024 * 1024:
        await message.answer(f"❌ Фото слишком большое (> {size_limit_mb} MB).")
        return

    status_message = await message.answer("🖼 Обрабатываю фото...", parse_mode="HTML")
    try:
        # История сообщений
        history = await ChatService.get_chat_messages(session, current_chat.id)

        # Скачиваем максимальный по размеру вариант фото
        file = await message.bot.get_file(largest_photo.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        image_bytes = file_bytes.read()

        caption = message.caption or "Опиши это изображение кратко и точно."

        # Отправляем в Gemini
        response = await gemini_service.generate_response_with_image(
            encrypted_api_key=user.api_key_encrypted,
            history_messages=history,
            image_bytes=image_bytes,
            mime_type="image/jpeg",
            caption=caption,
            model_name=current_chat.model_name,
        )

        # Сохраняем сообщения в БД
        await ChatService.add_message(
            session=session,
            chat_id=current_chat.id,
            user_id=user.telegram_id,
            role="user",
            content=f"[Фото] {caption}"
        )
        await ChatService.add_message(
            session=session,
            chat_id=current_chat.id,
            user_id=user.telegram_id,
            role="model",
            content=response
        )

        chunks = format_response_html_chunks(response)
        await status_message.edit_text(chunks[0], parse_mode="HTML")
        for chunk in chunks[1:]:
            await message.answer(chunk, parse_mode="HTML")
    except Exception as e:
        await status_message.edit_text(f"❌ Произошла ошибка: {str(e)}", parse_mode=None)

@router.message(F.document)
async def handle_document(message: Message, user: User, session, has_premium: bool, **kwargs):
    # Обработка медиа-групп с документами: один запрос на альбом
    if getattr(message, "media_group_id", None):
        group_id = message.media_group_id
        grp = MEDIA_GROUPS.setdefault(group_id, {"type": "document", "documents": [], "captions": [], "user_id": user.telegram_id, "tg_chat_id": message.chat.id})
        doc = message.document
        size_limit_mb = config.FILE_SIZE_LIMIT_PREMIUM_MB if has_premium else config.FILE_SIZE_LIMIT_FREE_MB
        if getattr(doc, "file_size", None) and doc.file_size > size_limit_mb * 1024 * 1024:
            await message.answer(f"❌ Один из файлов слишком большой (> {size_limit_mb} MB).")
            return
        grp["documents"].append({"file_id": doc.file_id, "mime_type": doc.mime_type or "application/octet-stream"})
        if message.caption:
            grp["captions"].append(message.caption)
        if "_scheduled" not in grp:
            grp["_scheduled"] = True
            asyncio.create_task(_process_media_group(group_id, message.bot))
        return
    # Проверка ключа
    if not user.api_key_encrypted:
        await message.answer("🔑 Для работы с файлами нужен API ключ. Используйте /api_key")
        return

    current_chat = await UserService.get_current_chat(session, user.telegram_id)
    if not current_chat:
        await message.answer("❌ Активный чат не найден. Используйте /start для создания чата.")
        return

    # Проверка размера документа
    doc = message.document
    size_limit_mb = config.FILE_SIZE_LIMIT_PREMIUM_MB if has_premium else config.FILE_SIZE_LIMIT_FREE_MB
    if getattr(doc, "file_size", None) and doc.file_size > size_limit_mb * 1024 * 1024:
        await message.answer(f"❌ Файл слишком большой (> {size_limit_mb} MB).")
        return

    status_message = await message.answer("📄 Обрабатываю файл...", parse_mode="HTML")
    try:
        history = await ChatService.get_chat_messages(session, current_chat.id)

        file = await message.bot.get_file(doc.file_id)
        file_bytes_io = await message.bot.download_file(file.file_path)
        file_bytes = file_bytes_io.read()

        # Определяем mime-type
        mime_type = doc.mime_type or mimetypes.guess_type(doc.file_name or "")[0] or "application/octet-stream"
        prompt = message.caption or "Проанализируй вложенный файл и ответь кратко по сути."

        response = await gemini_service.generate_response_with_file(
            encrypted_api_key=user.api_key_encrypted,
            history_messages=history,
            file_bytes=file_bytes,
            mime_type=mime_type,
            prompt=prompt,
            model_name=current_chat.model_name,
        )

        # Сохраняем в БД
        await ChatService.add_message(
            session=session,
            chat_id=current_chat.id,
            user_id=user.telegram_id,
            role="user",
            content=f"[Файл] {doc.file_name or ''} — {prompt}"
        )
        await ChatService.add_message(
            session=session,
            chat_id=current_chat.id,
            user_id=user.telegram_id,
            role="model",
            content=response
        )

        chunks = format_response_html_chunks(response)
        await status_message.edit_text(chunks[0], parse_mode="HTML")
        for chunk in chunks[1:]:
            await message.answer(chunk, parse_mode="HTML")
    except Exception as e:
        await status_message.edit_text(f"❌ Произошла ошибка: {str(e)}", parse_mode=None)
@router.callback_query(F.data == "cancel")
async def cancel_chat_action(callback: CallbackQuery, state: FSMContext, user: User, session, **kwargs):
    await state.clear()
    
    # Return to chat management
    chats = await ChatService.get_user_chats(session, user.telegram_id)
    current_chat = await UserService.get_current_chat(session, user.telegram_id)
    has_premium = await UserService.has_premium_access(session, user.telegram_id)
    current_chat_id = current_chat.id if current_chat else None
    
    text = f"""💬 <b>Управление чатами</b>

📊 <b>Статистика:</b>
• Чатов: {len(chats)}/{config.PREMIUM_CHAT_LIMIT if has_premium else config.FREE_CHAT_LIMIT}
• Статус: {"Premium" if has_premium else "Free"}
• Активный чат: {current_chat.title if current_chat else "Не выбран"}

Выберите чат или создайте новый:"""

    await callback.message.edit_text(
        text,
        reply_markup=get_chats_keyboard(chats, current_chat_id, has_premium),
        parse_mode="HTML"
    )
    await callback.answer("❌ Действие отменено")