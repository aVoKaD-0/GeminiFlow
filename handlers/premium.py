from aiogram import Router, F
from aiogram.types import CallbackQuery, LabeledPrice, PreCheckoutQuery
from database.models import User
from services.user_service import UserService
from keyboards import get_premium_keyboard, get_referral_keyboard
from sqlalchemy import select, func
from database.models import Referral
import config

router = Router()

"""Используем планы из config.PREMIUM_PLANS"""

@router.callback_query(F.data == "premium_info")
async def show_premium_info(callback: CallbackQuery, user: User, session, has_premium: bool, **kwargs):
    if has_premium:
        expires_text = ""
        if user.subscription_expires_at:
            from zoneinfo import ZoneInfo
            dt = user.subscription_expires_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Moscow"))
            expires_text = f"\n🗓 Действует до: {dt.strftime('%d.%m.%Y %H:%M')} MSK"
        
        text = f"""⭐ <b>Premium статус</b>

✅ <b>Статус:</b> Активен{expires_text}

<b>Ваши Premium возможности:</b>
• 🤖 Доступ к современным моделям Gemini
• 💬 До {config.PREMIUM_CHAT_LIMIT} чатов
• ⚡ Приоритетная обработка
• 🎯 Выбор модели для каждого чата
• поддержка файлов до 10 МБ

<b>Спасибо за поддержку проекта! 💖</b>"""
    else:
        text = f"""⭐ <b>Premium подписка</b>

<b>Получите больше возможностей:</b>
• 🤖 Доступ к современным моделям Gemini
• 💬 До {config.PREMIUM_CHAT_LIMIT} чатов вместо 1
• ⚡ Приоритетная обработка запросов
• 🎯 Выбор модели для каждого чата
• поддержка файлов до 20 МБ

<b>💰 Цены:</b>
• 1 месяц - {config.PREMIUM_PLANS["1"]["stars"]}⭐ (~$1)
• 3 месяца - {config.PREMIUM_PLANS["3"]["stars"]}⭐ (~$2.5) 🔥
• 6 месяцев - {config.PREMIUM_PLANS["6"]["stars"]}⭐ (~$4.5) 💎
• 1 год - {config.PREMIUM_PLANS["12"]["stars"]}⭐ (~$8) ⚡

Выберите подходящий план:"""

    await callback.message.edit_text(
        text,
        reply_markup=get_premium_keyboard(has_premium, user.subscription_expires_at),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("buy_premium:"))
async def buy_premium(callback: CallbackQuery, **kwargs):
    months = callback.data.split(":")[1]
    
    if months not in config.PREMIUM_PLANS:
        await callback.answer("❌ Неверный план", show_alert=True)
        return
    
    plan = config.PREMIUM_PLANS[months]
    
    # Create invoice for Telegram Stars
    prices = [LabeledPrice(label=plan["name"], amount=plan["stars"])]
    
    await callback.message.answer_invoice(
        title=plan["name"],
        description=f"Premium доступ к Gemini Flow на {plan['days']} дней",
        payload=f"premium_{months}_{callback.from_user.id}",
        provider_token="",  # Empty for Telegram Stars
        currency="XTR",  # Telegram Stars currency
        prices=prices,
        start_parameter="premium_subscription"
    )
    
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery, **kwargs):
    # Always approve payments for simplicity
    # In production, you might want to verify the payload
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message, user: User, session, **kwargs):
    payment = message.successful_payment
    payload_parts = payment.invoice_payload.split("_")
    
    if len(payload_parts) >= 3 and payload_parts[0] == "premium":
        months = payload_parts[1]
        user_id = int(payload_parts[2])
        
        if months in config.PREMIUM_PLANS and user_id == user.telegram_id:
            plan = config.PREMIUM_PLANS[months]
            
            # Grant premium access
            await UserService.grant_premium(session, user.telegram_id, plan["days"])
            
            await message.answer(
                f"🎉 <b>Оплата успешна!</b>\n\n"
                f"✅ Premium активирован на {plan['days']} дней\n"
                f"💫 Сумма: {payment.total_amount} звезд\n\n"
                f"Спасибо за поддержку проекта! 💖",
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Ошибка при обработке платежа. Обратитесь в поддержку.")
    else:
        await message.answer("❌ Неверный формат платежа.")

@router.callback_query(F.data == "referral_info")
async def show_referral_info(callback: CallbackQuery, user: User, session, **kwargs):
    # Get referral count
    result = await session.execute(
        select(func.count(Referral.id)).where(Referral.referrer_id == user.telegram_id)
    )
    referral_count = result.scalar() or 0
    
    reward_status = "✅ Получена" if user.reward_claimed else f"{referral_count}/{config.REFERRAL_TARGET_COUNT}"
    
    ref_link = f"https://t.me/your_bot_name?start=ref{user.telegram_id}"
    
    text = f"""🎁 <b>Реферальная программа</b>

<b>Пригласите друзей и получите Premium бесплатно!</b>

📊 <b>Ваш прогресс:</b>
• Приглашено: {referral_count} человек
• Цель: {config.REFERRAL_TARGET_COUNT} человек
• Награда: {config.REFERRAL_REWARD_DAYS} дней Premium
• Статус награды: {reward_status}

🔗 <b>Ваша реферальная ссылка:</b>
<code>{ref_link}</code>

<b>Как это работает:</b>
1. Поделитесь ссылкой с друзьями
2. Когда друг зарегистрируется по вашей ссылке
3. При достижении {config.REFERRAL_TARGET_COUNT} рефералов получите {config.REFERRAL_REWARD_DAYS} дней Premium!

<b>💡 Совет:</b> Делитесь ссылкой в соцсетях, форумах и чатах!"""

    await callback.message.edit_text(
        text,
        reply_markup=get_referral_keyboard(user.telegram_id),
        parse_mode="HTML"
    )
    await callback.answer()