import httpx
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

OLLAMA_URL = f"http://{settings.ollama_host}:{settings.ollama_port}"


def build_prompt(question: str, chunks: list[dict], system_prompt: str) -> str:
    """
    Build the prompt we send to the LLM.
    
    We give the LLM:
    1. A system instruction
    2. The relevant chunks as context
    3. The user question
    
    This is the core of RAG - grounding the LLM answer
    in actual retrieved documents.
    """
    # format the chunks as numbered sources
    sources_text = ""
    for i, chunk in enumerate(chunks):
        sources_text += f"\nSource {i+1} ({chunk['filename']}):\n{chunk['content']}\n"

    prompt = f"""{system_prompt}

Use the following sources to answer the question.
Only use information from the sources below.
If the sources do not contain enough information, say so clearly.
Always mention which source you used.

Sources:
{sources_text}

Question: {question}

Answer:"""

    return prompt


async def generate_answer(
    question: str,
    chunks: list[dict],
    system_prompt: str
) -> str:
    """
    Send prompt to Ollama LLM and get answer back.
    """
    if not chunks:
        logger.warning("No chunks provided to LLM - returning default response")
        return "I could not find relevant information to answer your question."

    prompt = build_prompt(question, chunks, system_prompt)

    logger.info(
        f"Sending prompt to LLM "
        f"model={settings.ollama_llm_model} "
        f"chunks={len(chunks)}"
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": settings.ollama_llm_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
        )
        response.raise_for_status()
        data = response.json()
        answer = data["message"]["content"]

    logger.info(f"LLM answer generated length={len(answer)} chars")
    return answer