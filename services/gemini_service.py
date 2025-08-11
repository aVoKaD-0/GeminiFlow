import google.generativeai as genai
from typing import List, Dict, Optional
import asyncio
import logging
from utils.crypto import decrypt_api_key

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.client_cache = {}
    
    def _get_client(self, api_key: str, model_name: str):
        """Get or create Gemini client for API key"""
        if api_key not in self.client_cache:
            genai.configure(api_key=api_key)
            self.client_cache[api_key] = genai.GenerativeModel(model_name)
        return self.client_cache[api_key]
    
    async def validate_api_key(self, encrypted_api_key: str, model_name: str) -> bool:
        """Validate Gemini API key"""
        try:
            api_key = decrypt_api_key(encrypted_api_key)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            
            # Make a simple test request
            response = await asyncio.to_thread(
                model.generate_content,
                "Hello"
            )
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False
    
    async def generate_response(
        self,
        encrypted_api_key: str,
        messages: List[Dict[str, str]],
        model_name: str = "gemini-1.5-flash"
    ) -> str:
        """Генерация ответа Gemini по подготовленной истории сообщений.

        messages: список словарей вида {"role": "user|model", "content": "..."}
        Последнее сообщение должно быть сообщением пользователя, на которое генерируем ответ.
        """
        try:
            api_key = decrypt_api_key(encrypted_api_key)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)

            # Конвертируем историю в формат Gemini (кроме последнего сообщения)
            chat_history = []
            if len(messages) > 1:
                for msg in messages[:-1]:
                    role = "user" if msg["role"] == "user" else "model"
                    chat_history.append({
                        "role": role,
                        "parts": [msg["content"]]
                    })

            chat = model.start_chat(history=chat_history)

            last_message = messages[-1]["content"]
            response = await asyncio.to_thread(chat.send_message, last_message)
            return response.text

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            if "API_KEY_INVALID" in str(e):
                raise ValueError("Неверный API ключ")
            elif "QUOTA_EXCEEDED" in str(e):
                raise ValueError("Превышен лимит запросов")
            else:
                raise ValueError(f"Ошибка Gemini API: {str(e)}")

    async def generate_response_with_image(
        self,
        encrypted_api_key: str,
        history_messages: List[Dict[str, str]],
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        caption: str = "",
        model_name: str = "gemini-1.5-flash"
    ) -> str:
        """Генерация ответа с изображением и историей диалога.

        history_messages: история без текущего фото-сообщения
        image_bytes: содержимое изображения
        caption: подпись к фото (опционально)
        """
        try:
            api_key = decrypt_api_key(encrypted_api_key)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)

            # История для чата
            chat_history = []
            if history_messages:
                for msg in history_messages:
                    role = "user" if msg["role"] == "user" else "model"
                    chat_history.append({
                        "role": role,
                        "parts": [msg["content"]]
                    })

            chat = model.start_chat(history=chat_history)

            parts = [
                {"mime_type": mime_type, "data": image_bytes}
            ]
            if caption:
                parts.append(caption)

            response = await asyncio.to_thread(chat.send_message, parts)
            return response.text

        except Exception as e:
            logger.error(f"Gemini API error (image): {e}")
            if "API_KEY_INVALID" in str(e):
                raise ValueError("Неверный API ключ")
            elif "QUOTA_EXCEEDED" in str(e):
                raise ValueError("Превышен лимит запросов")
            else:
                raise ValueError(f"Ошибка Gemini API: {str(e)}")

    async def generate_response_with_file(
        self,
        encrypted_api_key: str,
        history_messages: List[Dict[str, str]],
        file_bytes: bytes,
        mime_type: str,
        prompt: str = "",
        model_name: str = "gemini-1.5-flash",
    ) -> str:
        """Генерация ответа с произвольным файлом (PDF/TXT/JSON/CSV и т.п.) и историей диалога."""
        try:
            api_key = decrypt_api_key(encrypted_api_key)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)

            # История для чата
            chat_history = []
            if history_messages:
                for msg in history_messages:
                    role = "user" if msg["role"] == "user" else "model"
                    chat_history.append({
                        "role": role,
                        "parts": [msg["content"]]
                    })

            chat = model.start_chat(history=chat_history)

            parts: List = [
                {"mime_type": mime_type, "data": file_bytes}
            ]
            if prompt:
                parts.append(prompt)

            response = await asyncio.to_thread(chat.send_message, parts)
            return response.text

        except Exception as e:
            logger.error(f"Gemini API error (file): {e}")
            if "API_KEY_INVALID" in str(e):
                raise ValueError("Неверный API ключ")
            elif "QUOTA_EXCEEDED" in str(e):
                raise ValueError("Превышен лимит запросов")
            else:
                raise ValueError(f"Ошибка Gemini API: {str(e)}")

    async def generate_response_with_images_batch(
        self,
        encrypted_api_key: str,
        history_messages: List[Dict[str, str]],
        images: List[Dict[str, bytes]],  # [{"mime_type": str, "data": bytes}]
        caption: str = "",
        model_name: str = "gemini-1.5-flash"
    ) -> str:
        """Генерация ответа с несколькими изображениями и историей диалога."""
        try:
            api_key = decrypt_api_key(encrypted_api_key)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)

            chat_history = []
            if history_messages:
                for msg in history_messages:
                    role = "user" if msg["role"] == "user" else "model"
                    chat_history.append({
                        "role": role,
                        "parts": [msg["content"]]
                    })

            chat = model.start_chat(history=chat_history)

            parts = [{"mime_type": img["mime_type"], "data": img["data"]} for img in images]
            if caption:
                parts.append(caption)

            response = await asyncio.to_thread(chat.send_message, parts)
            return response.text

        except Exception as e:
            logger.error(f"Gemini API error (images batch): {e}")
            if "API_KEY_INVALID" in str(e):
                raise ValueError("Неверный API ключ")
            elif "QUOTA_EXCEEDED" in str(e):
                raise ValueError("Превышен лимит запросов")
            else:
                raise ValueError(f"Ошибка Gemini API: {str(e)}")

    async def generate_response_with_files_batch(
        self,
        encrypted_api_key: str,
        history_messages: List[Dict[str, str]],
        files: List[Dict[str, bytes]],  # [{"mime_type": str, "data": bytes}]
        prompt: str = "",
        model_name: str = "gemini-1.5-flash",
    ) -> str:
        """Генерация ответа с несколькими файлами и историей диалога."""
        try:
            api_key = decrypt_api_key(encrypted_api_key)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)

            chat_history = []
            if history_messages:
                for msg in history_messages:
                    role = "user" if msg["role"] == "user" else "model"
                    chat_history.append({
                        "role": role,
                        "parts": [msg["content"]]
                    })

            chat = model.start_chat(history=chat_history)

            parts: List = [{"mime_type": f["mime_type"], "data": f["data"]} for f in files]
            if prompt:
                parts.append(prompt)

            response = await asyncio.to_thread(chat.send_message, parts)
            return response.text

        except Exception as e:
            logger.error(f"Gemini API error (files batch): {e}")
            if "API_KEY_INVALID" in str(e):
                raise ValueError("Неверный API ключ")
            elif "QUOTA_EXCEEDED" in str(e):
                raise ValueError("Превышен лимит запросов")
            else:
                raise ValueError(f"Ошибка Gemini API: {str(e)}")


    # async def generate_response(
    #     self, 
    #     encrypted_api_key: str, 
    #     messages: List[Dict[str, str]], 
    #     model_name: str = "gemini-1.5-flash"
    # ) -> str:
    #     """Generate response from Gemini"""
    #     try:
    #         api_key = decrypt_api_key(encrypted_api_key)
    #         genai.configure(api_key=api_key)
    #         model = genai.GenerativeModel(model_name)
            
    #         # Convert messages to Gemini format
    #         chat_history = []
    #         for msg in messages[:-1]:  # All except the last message
    #             role = "user" if msg["role"] == "user" else "model"
    #             chat_history.append({
    #                 "role": role,
    #                 "parts": [msg["content"]]
    #             })
            
    #         # Start chat with history
    #         chat = model.start_chat(history=chat_history)
            
    #         # Send the last message
    #         last_message = messages[-1]["content"]
    #         response = await asyncio.to_thread(chat.send_message, last_message)
            
    #         return response.text
            
    #     except Exception as e:
    #         logger.error(f"Gemini API error: {e}")
    #         if "API_KEY_INVALID" in str(e):
    #             raise ValueError("Неверный API ключ")
    #         elif "QUOTA_EXCEEDED" in str(e):
    #             raise ValueError("Превышен лимит запросов")
    #         else:
    #             raise ValueError(f"Ошибка Gemini API: {str(e)}")
    
    async def summarize_context(
        self, 
        encrypted_api_key: str, 
        messages: List[Dict[str, str]],
        model_name: str = "gemini-1.5-flash"
    ) -> str:
        """Summarize old messages to save context"""
        try:
            api_key = decrypt_api_key(encrypted_api_key)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            
            # Prepare messages for summarization
            conversation_text = ""
            for msg in messages:
                role = "Пользователь" if msg["role"] == "user" else "Ассистент"
                conversation_text += f"{role}: {msg['content']}\n\n"
            
            prompt = f"""Кратко обобщи следующий диалог, сохранив ключевую информацию и контекст:

{conversation_text}

Обобщение:"""
            
            response = await asyncio.to_thread(model.generate_content, prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Context summarization failed: {e}")
            return "Предыдущий контекст недоступен"