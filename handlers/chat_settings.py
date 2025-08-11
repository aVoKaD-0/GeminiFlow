# handlers/chat_settings.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.models import User, Chat
from services.chat_settings_service import chat_settings_service
from keyboards import (
    get_chat_settings_keyboard,
    get_model_selection_keyboard,
    get_temperature_keyboard,
    get_advanced_settings_keyboard,
    get_system_prompt_presets_keyboard,
    get_chats_keyboard # Импортируем для возврата
)
import logging
import uuid

logger = logging.getLogger(__name__)

router = Router()

# Определим FSM состояния для ввода настроек
class ChatSettingsStates(StatesGroup):
    waiting_for_temperature = State()
    waiting_for_advanced_settings = State()
    waiting_for_system_prompt = State()
    # waiting_for_custom_prompt = State() # Можно объединить с waiting_for_system_prompt

# --- Основное меню настроек ---
@router.callback_query(F.data.startswith("chat_settings:"))
async def handle_chat_settings_menu(callback: CallbackQuery, user: User, session, has_premium: bool, **kwargs):
    """Обработка выбора пункта в основном меню настроек чата."""
    try:
        parts = callback.data.split(":")
        action = parts[1]
        chat_id_str = parts[2]
        chat_id = uuid.UUID(chat_id_str)

        if action == "model":
            # Получаем доступные модели
            available_models = await chat_settings_service.get_available_models(session, has_premium)
            if not available_models:
                await callback.answer("❌ Не удалось загрузить список моделей.", show_alert=True)
                return
            await callback.message.edit_text("🤖 <b>Выберите модель:</b>", reply_markup=get_model_selection_keyboard(available_models, chat_id), parse_mode="HTML")

        elif action == "temperature":
            await callback.message.edit_text(
                "🌡️ <b>Температура</b>\n\n"
                "Контролирует случайность генерации:\n"
                "• <b>0.0</b> - Максимально предсказуемый, консервативный текст.\n"
                "• <b>0.5</b> - Хороший баланс между креативностью и связностью.\n"
                "• <b>1.0</b> - Баланс креативности и связности (по умолчанию).\n"
                "• <b>1.5+</b> - Более креативный и случайный, но может быть менее связным.\n\n"
                "Выберите значение или введите его (от 0.0 до 2.0):",
                reply_markup=get_temperature_keyboard(chat_id),
                parse_mode="HTML"
            )

        elif action == "system":
             await callback.message.edit_text(
                "🎭 <b>Личность (System Prompt)</b>\n\n"
                "Определите роль ассистента. Это сильно влияет на стиль и содержание ответов.\n"
                "Примеры: 'Ты — саркастичный ассистент.', 'Ты — эксперт по Python.'",
                reply_markup=get_system_prompt_presets_keyboard(chat_id),
                parse_mode="HTML"
            )

        elif action == "advanced":
            await callback.message.edit_text(
                "⚙️ <b>Продвинутые настройки</b>\n\n"
                "<b>Top-P (Nucleus Sampling):</b>\n"
                "Выбирает из самых вероятных токенов, сумма вероятностей которых превышает P. Используйте вместо температуры.\n\n"
                "<b>Top-K:</b>\n"
                "Ограничивает выбор следующего слова K наиболее вероятными вариантами. Используйте вместо температуры.\n\n"
                "Введите значения в формате: <code>Top-P,Top-K</code> (например, <code>0.9,40</code>).\n"
                "Оставьте поле пустым или введите <code>None,None</code>, чтобы сбросить настройки.",
                reply_markup=get_advanced_settings_keyboard(chat_id),
                parse_mode="HTML"
            )
        # elif action == "download":
        #     # Реализация скачивания чата
        #     pass
        else:
            await callback.answer("Неизвестное действие.", show_alert=True)

    except (ValueError, IndexError) as e:
        await callback.answer("❌ Неверный формат данных.", show_alert=True)
    except Exception as e:
        # logger.error(f"Ошибка в handle_chat_settings_menu: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)


# --- Выбор модели ---
@router.callback_query(F.data.startswith("model_select:"))
async def select_model(callback: CallbackQuery, user: User, session, has_premium: bool, **kwargs):
    """Выбор модели для чата."""
    try:
        parts = callback.data.split(":")
        idx_str = parts[1]
        chat_id_str = parts[2]
        chat_id = uuid.UUID(chat_id_str)

        # Получаем модели и маппим индекс -> имя модели
        available_models = await chat_settings_service.get_available_models(session, has_premium)
        try:
            model_index = int(idx_str)
            model_name = available_models[model_index]
        except Exception:
            await callback.answer("❌ Неверный выбор модели.", show_alert=True)
            return

        success = await chat_settings_service.update_chat_model(session, chat_id, user.telegram_id, model_name)
        if success:
            # Возвращаемся к меню настроек чата
            # Получаем обновленную информацию о чате
            chat_info = await chat_settings_service.get_chat_info(session, chat_id, user.telegram_id)
            if chat_info:
                info_text = (
                    f"💬 <b>Текущий чат:</b> {chat_info['title']}\n"
                    f"🤖 <b>Модель:</b> {chat_info['model_name']}\n"
                    f"🌡️ <b>Температура:</b> {chat_info['temperature']}\n"
                    f"🎭 <b>Личность:</b> {chat_info['system_prompt'][:50]}{'...' if len(chat_info['system_prompt']) > 50 else ''}\n"
                    f"🎲 <b>Top-P:</b> {chat_info['top_p'] if chat_info['top_p'] is not None else 'Не задан'}\n"
                    f"🎲 <b>Top-K:</b> {chat_info['top_k'] if chat_info['top_k'] is not None else 'Не задан'}\n"
                )
                await callback.message.edit_text(info_text, reply_markup=get_chat_settings_keyboard(chat_id), parse_mode="HTML")
                await callback.answer(f"✅ Модель изменена на {model_name}")
            else:
                 await callback.answer("✅ Модель изменена, но возникла ошибка при обновлении информации.", show_alert=True)
        else:
            await callback.answer("❌ Ошибка при изменении модели.", show_alert=True)

    except (ValueError, IndexError) as e:
        await callback.answer("❌ Неверный формат данных.", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка в select_model: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)

# --- Температура ---
@router.callback_query(F.data.startswith("temp_input:"))
async def request_temperature_input(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Запрашивает ввод температуры."""
    try:
        chat_id_str = callback.data.split(":")[1]
        await state.update_data(chat_id_for_setting=chat_id_str)
        await state.set_state(ChatSettingsStates.waiting_for_temperature)
        await callback.message.edit_text("🌡️ Введите значение температуры (от 0.0 до 2.0):", reply_markup=None)
        await callback.answer()
    except (ValueError, IndexError) as e:
        await callback.answer("❌ Неверный формат данных.", show_alert=True)

@router.message(ChatSettingsStates.waiting_for_temperature)
async def process_temperature_input(message: Message, state: FSMContext, user: User, session, **kwargs):
    """Обрабатывает ввод температуры."""
    try:
        data = await state.get_data()
        chat_id_str = data.get("chat_id_for_setting")
        if not chat_id_str:
            await message.answer("❌ Ошибка состояния. Попробуйте снова.")
            await state.clear()
            return

        chat_id = uuid.UUID(chat_id_str)
        temp_str = message.text.strip().replace(',', '.') # Заменяем запятую на точку для удобства

        try:
            temperature = float(temp_str)
            if not (0.0 <= temperature <= 2.0):
                raise ValueError("Out of range")
        except ValueError:
            await message.answer("❌ Неверный формат. Введите число от 0.0 до 2.0.")
            # Не очищаем состояние, чтобы пользователь мог попробовать снова
            return

        success = await chat_settings_service.update_chat_temperature(session, chat_id, user.telegram_id, temperature)
        if success:
            await message.answer(f"✅ Температура установлена на {temperature}.")
            # Возвращаемся к меню настроек чата
            # Получаем обновленную информацию о чате
            chat_info = await chat_settings_service.get_chat_info(session, chat_id, user.telegram_id)
            if chat_info:
                info_text = (
                    f"💬 <b>Текущий чат:</b> {chat_info['title']}\n"
                    f"🤖 <b>Модель:</b> {chat_info['model_name']}\n"
                    f"🌡️ <b>Температура:</b> {chat_info['temperature']}\n"
                    f"🎭 <b>Личность:</b> {chat_info['system_prompt'][:50]}{'...' if len(chat_info['system_prompt']) > 50 else ''}\n"
                    f"🎲 <b>Top-P:</b> {chat_info['top_p'] if chat_info['top_p'] is not None else 'Не задан'}\n"
                    f"🎲 <b>Top-K:</b> {chat_info['top_k'] if chat_info['top_k'] is not None else 'Не задан'}\n"
                )
                await message.answer(info_text, reply_markup=get_chat_settings_keyboard(chat_id), parse_mode="HTML")
            else:
                 await message.answer("✅ Температура установлена, но возникла ошибка при обновлении информации.")
        else:
            await message.answer("❌ Ошибка при установке температуры.")
    except Exception as e:
        # logger.error(f"Ошибка в process_temperature_input: {e}")
        await message.answer("❌ Произошла ошибка при обработке ввода.")
    finally:
        await state.clear()

# --- Продвинутые настройки ---
@router.callback_query(F.data.startswith("advanced_input:"))
async def request_advanced_input(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Запрашивает ввод продвинутых настроек."""
    try:
        chat_id_str = callback.data.split(":")[1]
        await state.update_data(chat_id_for_setting=chat_id_str)
        await state.set_state(ChatSettingsStates.waiting_for_advanced_settings)
        # Сообщение уже отправлено в handle_chat_settings_menu
        await callback.answer()
    except (ValueError, IndexError) as e:
        await callback.answer("❌ Неверный формат данных.", show_alert=True)

@router.message(ChatSettingsStates.waiting_for_advanced_settings)
async def process_advanced_input(message: Message, state: FSMContext, user: User, session, **kwargs):
    """Обрабатывает ввод продвинутых настроек."""
    try:
        data = await state.get_data()
        chat_id_str = data.get("chat_id_for_setting")
        if not chat_id_str:
            await message.answer("❌ Ошибка состояния. Попробуйте снова.")
            await state.clear()
            return

        chat_id = uuid.UUID(chat_id_str)
        input_text = message.text.strip()

        top_p, top_k = None, None
        if input_text.lower() in ["", "none", "none,none"]:
            # Сброс настроек
            pass # top_p и top_k остаются None
        else:
            try:
                parts = input_text.split(',')
                if len(parts) != 2:
                    raise ValueError("Неверный формат. Используйте: Top-P,Top-K")

                p_str, k_str = parts[0].strip(), parts[1].strip()

                if p_str.lower() != "none":
                    top_p = float(p_str.replace(',', '.'))
                    if not (0.0 <= top_p <= 1.0):
                        raise ValueError("Top-P должен быть от 0.0 до 1.0")

                if k_str.lower() != "none":
                    top_k = int(k_str)
                    if top_k <= 0:
                        raise ValueError("Top-K должен быть положительным целым числом")

            except ValueError as ve:
                await message.answer(f"❌ Ошибка ввода: {ve}")
                # Не очищаем состояние
                return

        success = await chat_settings_service.update_chat_advanced(session, chat_id, user.telegram_id, top_p, top_k)
        if success:
            p_text = f"{top_p}" if top_p is not None else "Не задан"
            k_text = f"{top_k}" if top_k is not None else "Не задан"
            await message.answer(f"✅ Продвинутые настройки обновлены:\nTop-P: {p_text}\nTop-K: {k_text}")

            # Возвращаемся к меню настроек чата
            chat_info = await chat_settings_service.get_chat_info(session, chat_id, user.telegram_id)
            if chat_info:
                info_text = (
                    f"💬 <b>Текущий чат:</b> {chat_info['title']}\n"
                    f"🤖 <b>Модель:</b> {chat_info['model_name']}\n"
                    f"🌡️ <b>Температура:</b> {chat_info['temperature']}\n"
                    f"🎭 <b>Личность:</b> {chat_info['system_prompt'][:50]}{'...' if len(chat_info['system_prompt']) > 50 else ''}\n"
                    f"🎲 <b>Top-P:</b> {chat_info['top_p'] if chat_info['top_p'] is not None else 'Не задан'}\n"
                    f"🎲 <b>Top-K:</b> {chat_info['top_k'] if chat_info['top_k'] is not None else 'Не задан'}\n"
                )
                await message.answer(info_text, reply_markup=get_chat_settings_keyboard(chat_id), parse_mode="HTML")
            else:
                 await message.answer("✅ Настройки обновлены, но возникла ошибка при обновлении информации.")

        else:
            await message.answer("❌ Ошибка при обновлении продвинутых настроек.")
    except Exception as e:
        # logger.error(f"Ошибка в process_advanced_input: {e}")
        await message.answer("❌ Произошла ошибка при обработке ввода.")
    finally:
        await state.clear()

# --- Системный промпт (Личность) ---
@router.callback_query(F.data.startswith("preset_select:"))
async def select_preset_prompt(callback: CallbackQuery, user: User, session, **kwargs):
    """Выбор пресета системного промпта."""
    try:
        parts = callback.data.split(":")
        idx_str = parts[1]
        chat_id_str = parts[2]
        chat_id = uuid.UUID(chat_id_str)

        # Такой же список пресетов, как в keyboards.get_system_prompt_presets_keyboard
        presets = [
            "Эксперт по Python",
            "Креативный копирайтер",
            "Помощник в путешествиях",
            "Саркастичный ассистент",
            "Переводчик"
        ]

        try:
            preset_index = int(idx_str)
            preset_prompt = presets[preset_index]
        except Exception:
            await callback.answer("❌ Неверный выбор пресета.", show_alert=True)
            return

        success = await chat_settings_service.update_chat_system_prompt(session, chat_id, user.telegram_id, preset_prompt)
        if success:
             # Возвращаемся к меню настроек чата
            chat_info = await chat_settings_service.get_chat_info(session, chat_id, user.telegram_id)
            if chat_info:
                info_text = (
                    f"💬 <b>Текущий чат:</b> {chat_info['title']}\n"
                    f"🤖 <b>Модель:</b> {chat_info['model_name']}\n"
                    f"🌡️ <b>Температура:</b> {chat_info['temperature']}\n"
                    f"🎭 <b>Личность:</b> {chat_info['system_prompt'][:50]}{'...' if len(chat_info['system_prompt']) > 50 else ''}\n"
                    f"🎲 <b>Top-P:</b> {chat_info['top_p'] if chat_info['top_p'] is not None else 'Не задан'}\n"
                    f"🎲 <b>Top-K:</b> {chat_info['top_k'] if chat_info['top_k'] is not None else 'Не задан'}\n"
                )
                await callback.message.edit_text(info_text, reply_markup=get_chat_settings_keyboard(chat_id), parse_mode="HTML")
                await callback.answer(f"✅ Личность установлена: {preset_prompt}")
            else:
                 await callback.answer("✅ Личность установлена, но возникла ошибка при обновлении информации.", show_alert=True)
        else:
            await callback.answer("❌ Ошибка при установке личности.", show_alert=True)

    except (ValueError, IndexError) as e:
        await callback.answer("❌ Неверный формат данных.", show_alert=True)
    except Exception as e:
        # logger.error(f"Ошибка в select_preset_prompt: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)

@router.callback_query(F.data.startswith("custom_prompt_input:"))
async def request_custom_prompt_input(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Запрашивает ввод пользовательского системного промпта."""
    try:
        chat_id_str = callback.data.split(":")[1]
        await state.update_data(chat_id_for_setting=chat_id_str)
        await state.set_state(ChatSettingsStates.waiting_for_system_prompt)
        await callback.message.edit_text("🎭 Введите вашу собственную роль для ассистента (System Prompt):", reply_markup=None)
        await callback.answer()
    except (ValueError, IndexError) as e:
        await callback.answer("❌ Неверный формат данных.", show_alert=True)

@router.message(ChatSettingsStates.waiting_for_system_prompt)
async def process_custom_prompt_input(message: Message, state: FSMContext, user: User, session, **kwargs):
    """Обрабатывает ввод пользовательского системного промпта."""
    try:
        data = await state.get_data()
        chat_id_str = data.get("chat_id_for_setting")
        if not chat_id_str:
            await message.answer("❌ Ошибка состояния. Попробуйте снова.")
            await state.clear()
            return

        chat_id = uuid.UUID(chat_id_str)
        custom_prompt = message.text.strip()

        # Ограничение длины? В ТЗ не указано, но можно добавить
        # if len(custom_prompt) > 1000: # Пример ограничения
        #     await message.answer("❌ Промпт слишком длинный (макс. 1000 символов).")
        #     return

        success = await chat_settings_service.update_chat_system_prompt(session, chat_id, user.telegram_id, custom_prompt)
        if success:
            await message.answer(f"✅ Личность установлена: {custom_prompt[:50]}{'...' if len(custom_prompt) > 50 else ''}")

            # Возвращаемся к меню настроек чата
            chat_info = await chat_settings_service.get_chat_info(session, chat_id, user.telegram_id)
            if chat_info:
                info_text = (
                    f"💬 <b>Текущий чат:</b> {chat_info['title']}\n"
                    f"🤖 <b>Модель:</b> {chat_info['model_name']}\n"
                    f"🌡️ <b>Температура:</b> {chat_info['temperature']}\n"
                    f"🎭 <b>Личность:</b> {chat_info['system_prompt'][:50]}{'...' if len(chat_info['system_prompt']) > 50 else ''}\n"
                    f"🎲 <b>Top-P:</b> {chat_info['top_p'] if chat_info['top_p'] is not None else 'Не задан'}\n"
                    f"🎲 <b>Top-K:</b> {chat_info['top_k'] if chat_info['top_k'] is not None else 'Не задан'}\n"
                )
                await message.answer(info_text, reply_markup=get_chat_settings_keyboard(chat_id), parse_mode="HTML")
            else:
                 await message.answer("✅ Личность установлена, но возникла ошибка при обновлении информации.")

        else:
            await message.answer("❌ Ошибка при установке личности.")
    except Exception as e:
        # logger.error(f"Ошибка в process_custom_prompt_input: {e}")
        await message.answer("❌ Произошла ошибка при обработке ввода.")
    finally:
        await state.clear()

# --- Навигация ---
@router.callback_query(F.data.startswith("back_to_chat_settings:"))
async def back_to_chat_settings(callback: CallbackQuery, user: User, session, **kwargs):
    """Возврат к меню настроек чата."""
    try:
        chat_id_str = callback.data.split(":")[1]
        chat_id = uuid.UUID(chat_id_str)

        chat_info = await chat_settings_service.get_chat_info(session, chat_id, user.telegram_id)
        if chat_info:
            info_text = (
                f"💬 <b>Текущий чат:</b> {chat_info['title']}\n"
                f"🤖 <b>Модель:</b> {chat_info['model_name']}\n"
                f"🌡️ <b>Температура:</b> {chat_info['temperature']}\n"
                f"🎭 <b>Личность:</b> {chat_info['system_prompt'][:50]}{'...' if len(chat_info['system_prompt']) > 50 else ''}\n"
                f"🎲 <b>Top-P:</b> {chat_info['top_p'] if chat_info['top_p'] is not None else 'Не задан'}\n"
                f"🎲 <b>Top-K:</b> {chat_info['top_k'] if chat_info['top_k'] is not None else 'Не задан'}\n"
            )
            await callback.message.edit_text(info_text, reply_markup=get_chat_settings_keyboard(chat_id), parse_mode="HTML")
            await callback.answer()
        else:
             await callback.answer("❌ Ошибка получения информации о чате.", show_alert=True)
    except (ValueError, IndexError) as e:
        await callback.answer("❌ Неверный формат данных.", show_alert=True)
    except Exception as e:
        # logger.error(f"Ошибка в back_to_chat_settings: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)
