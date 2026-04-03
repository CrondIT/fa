import logging
import httpx
import base64
from global_state import (
    GIGACHAT_CLIENT_ID,
    GIGACHAT_CLIENT_SECRET,
    GIGACHAT_API_KEY,
    GIGACHAT_SCOPE,
)

logger = logging.getLogger(__name__)

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"


class GigaChatClient:
    """Клиент для работы с GigaChat API"""

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        scope: str = None,
        model: str = "GigaChat-Max",
    ):
        self.client_id = client_id or GIGACHAT_CLIENT_ID
        self.client_secret = client_secret or GIGACHAT_CLIENT_SECRET
        self.scope = scope or GIGACHAT_SCOPE
        self.model = model
        self._access_token = None

    async def _get_token(self) -> str:
        """Получение access-токена от GigaChat"""
        if self._access_token:
            return self._access_token

        logger.info(f"GigaChat: client_id={'***' + self.client_id[-5:] if self.client_id else 'None'}, secret={'***' + self.client_secret[-5:] if self.client_secret else 'None'}")

        if not self.client_id or not self.client_secret:
            raise RuntimeError("GigaChat: не заданы GIGACHAT_CLIENT_ID или GIGACHAT_CLIENT_SECRET")

        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_b64 = base64.b64encode(auth_string.encode()).decode()

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                AUTH_URL,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "Authorization": f"Basic {auth_b64}",
                    "RqUID": self.client_secret,
                },
                data={"scope": self.scope},
                timeout=15,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"GigaChat auth error: {response.status_code} — {response.text}"
                )

            data = response.json()
            self._access_token = data["access_token"]
            logger.info("GigaChat: access-токен получен")
            return self._access_token

    async def ask(self, prompt: str, system_prompt: str = None) -> str:
        """
        Отправить запрос к GigaChat и получить ответ.

        Args:
            prompt: Текст вопроса пользователя.
            system_prompt: Системная инструкция (опционально).

        Returns:
            Текст ответа от нейросети.
        """
        token = await self._get_token()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
        }

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                CHAT_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"GigaChat API error: {response.status_code} — {response.text}"
                )

            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            return answer

    async def ask_with_history(self, messages: list, system_prompt: str = None) -> str:
        """
        Отправить запрос с историей диалога для контекста.

        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}, ...]
            system_prompt: Системная инструкция (опционально).

        Returns:
            Текст ответа от нейросети.
        """
        token = await self._get_token()

        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": full_messages,
        }

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                CHAT_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"GigaChat API error: {response.status_code} — {response.text}"
                )

            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            return answer


# Глобальный экземпляр для импорта из других модулей
gigachat = GigaChatClient()
