import httpx
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def build_prompt(question: str, chunks: list[dict], system_prompt: str) -> list[dict]:
    """
    Build messages for the LLM.
    Returns list of messages in OpenAI format.
    Groq uses OpenAI compatible API.
    """
    # format chunks as context
    sources_text = ""
    for i, chunk in enumerate(chunks):
        sources_text += f"\nSource {i+1} ({chunk['filename']}):\n{chunk['content']}\n"

    user_message = f"""Use the following sources to answer the question.
Only use information from the sources below.
If the sources do not contain enough information say so clearly.
Always mention which source you used.

Sources:
{sources_text}

Question: {question}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]


async def generate_answer(
    question: str,
    chunks: list[dict],
    system_prompt: str
) -> str:
    """
    Send prompt to Groq and get answer back.
    Groq uses OpenAI compatible API format.
    """
    if not chunks:
        logger.warning("No chunks provided to LLM - returning default response")
        return "I could not find relevant information to answer your question."

    messages = build_prompt(question, chunks, system_prompt)

    logger.info(
        f"Sending prompt to Groq "
        f"model={settings.groq_llm_model} "
        f"chunks={len(chunks)}"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": settings.groq_llm_model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 1024
            }
        )
        response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"]

    logger.info(f"Groq answer generated length={len(answer)} chars")
    return answer


async def call_groq(messages: list[dict]) -> str:
    """
    Generic Groq call for any messages.
    Used by router and other nodes.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": settings.groq_llm_model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 512
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]