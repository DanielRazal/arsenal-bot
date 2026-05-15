import asyncio
import logging

from groq import AsyncGroq, GroqError

from ..config import GEMINI_API_KEY, GROQ_API_KEY

log = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"


class LLMClient:
    def __init__(self) -> None:
        self._groq = AsyncGroq(api_key=GROQ_API_KEY)
        self._gemini = None
        if GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                self._gemini = genai.GenerativeModel(GEMINI_MODEL)
            except Exception:
                log.exception("Failed to init Gemini fallback; will skip on Groq failures")

    async def complete(self, system: str, user: str, *, max_tokens: int = 600) -> str:
        try:
            resp = await self._groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=0.7,
            )
            return resp.choices[0].message.content or ""
        except GroqError:
            log.exception("Groq call failed; trying Gemini fallback")

        if self._gemini is None:
            raise RuntimeError("Groq failed and no Gemini fallback configured")

        # Gemini SDK is sync; run it in a thread
        def _call_gemini() -> str:
            full_prompt = f"{system}\n\n{user}"
            result = self._gemini.generate_content(full_prompt)
            return result.text or ""

        return await asyncio.to_thread(_call_gemini)

    async def close(self) -> None:
        await self._groq.close()
