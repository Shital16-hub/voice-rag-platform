import asyncio
import json
import time
import sys
import os

# set environment variables before any imports
os.environ["POSTGRES_USER"] = "raguser"
os.environ["POSTGRES_PASSWORD"] = "ragpassword"
os.environ["POSTGRES_DB"] = "ragdb"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"
os.environ["OLLAMA_HOST"] = "localhost"
os.environ["OLLAMA_PORT"] = "11434"
os.environ["OLLAMA_LLM_MODEL"] = "llama3.2:3b"
os.environ["OLLAMA_EMBED_MODEL"] = "nomic-embed-text"
os.environ["APP_SECRET_KEY"] = "changethisinproduction"
os.environ["APP_DEBUG"] = "true"

sys.path.append(os.path.join(os.path.dirname(__file__), "../backend"))

from app.core.config import settings
from app.services.retrieval_service import retrieve_relevant_chunks
from app.services.llm_service import generate_answer
from app.core.logger import get_logger
from metrics import (
    recall_at_k,
    mean_reciprocal_rank,
    check_answer_groundedness,
    check_unanswerable_handled
)
logger = get_logger(__name__)

# load evaluation dataset
EVAL_DATASET_PATH = os.path.join(os.path.dirname(__file__), "hr_eval_dataset.json")

# these come from our test data
TENANT_ID = "c230676f-a74d-4204-a471-ac9a4917ad18"
AGENT_ID = "d357a032-144f-48a4-91f7-3b2feb967dd0"
TOP_K = 3
SCORE_THRESHOLD = 0.5

HR_SYSTEM_PROMPT = (
    "You are a helpful HR assistant. "
    "Answer questions based only on the provided sources. "
    "If you cannot find the answer in the sources, say so clearly."
)


async def run_single_question(question_data: dict) -> dict:
    """
    Run one question through the RAG pipeline and measure results.
    Returns a result dict with all metrics.
    """
    question = question_data["question"]
    relevant_content = question_data.get("relevant_content", [])
    expected_contains = question_data.get("expected_answer_contains", [])
    is_unanswerable = question_data.get("expected_unanswerable", False)

    logger.info(f"Evaluating question: {question}")

    # measure retrieval
    retrieval_start = time.time()
    chunks = await retrieve_relevant_chunks(
        question=question,
        tenant_id=TENANT_ID,
        agent_id=AGENT_ID,
        top_k=TOP_K,
        score_threshold=SCORE_THRESHOLD
    )
    retrieval_latency = time.time() - retrieval_start

    # get chunk texts for metric calculation
    chunk_texts = [c["content"] for c in chunks]

    # measure LLM
    llm_start = time.time()
    answer = await generate_answer(
        question=question,
        chunks=chunks,
        system_prompt=HR_SYSTEM_PROMPT
    )
    llm_latency = time.time() - llm_start

    # calculate metrics
    recall = recall_at_k(chunk_texts, relevant_content, TOP_K)
    mrr = mean_reciprocal_rank(chunk_texts, relevant_content)
    grounded = check_answer_groundedness(answer, expected_contains)

    # for unanswerable questions check refusal
    if is_unanswerable:
        handled_correctly = check_unanswerable_handled(answer)
    else:
        handled_correctly = None

    result = {
        "question_id": question_data["id"],
        "question": question,
        "difficulty": question_data.get("difficulty", "unknown"),
        "answer": answer,
        "chunks_retrieved": len(chunks),
        "top_chunk_score": chunks[0]["score"] if chunks else 0.0,
        "recall_at_k": recall,
        "mrr": mrr,
        "grounded": grounded,
        "unanswerable_handled": handled_correctly,
        "retrieval_latency_ms": round(retrieval_latency * 1000),
        "llm_latency_ms": round(llm_latency * 1000),
        "total_latency_ms": round((retrieval_latency + llm_latency) * 1000)
    }

    return result


async def run_evaluation():
    """Run full evaluation on all questions in dataset."""

    # load dataset
    with open(EVAL_DATASET_PATH) as f:
        dataset = json.load(f)

    questions = dataset["questions"]
    logger.info(f"Running evaluation on {len(questions)} questions")

    results = []
    for q in questions:
        result = await run_single_question(q)
        results.append(result)
        print(f"\nQ{result['question_id']}: {result['question']}")
        print(f"  Answer:     {result['answer'][:100]}")
        print(f"  Recall@{TOP_K}:  {result['recall_at_k']:.2f}")
        print(f"  MRR:        {result['mrr']:.2f}")
        print(f"  Grounded:   {result['grounded']}")
        print(f"  Retrieval:  {result['retrieval_latency_ms']}ms")
        print(f"  LLM:        {result['llm_latency_ms']}ms")
        if result['unanswerable_handled'] is not None:
            print(f"  Unanswerable handled: {result['unanswerable_handled']}")

    # calculate summary metrics
    answerable = [r for r in results if r["unanswerable_handled"] is None]
    unanswerable = [r for r in results if r["unanswerable_handled"] is not None]

    avg_recall = sum(r["recall_at_k"] for r in answerable) / len(answerable) if answerable else 0
    avg_mrr = sum(r["mrr"] for r in answerable) / len(answerable) if answerable else 0
    grounded_count = sum(1 for r in answerable if r["grounded"])
    avg_retrieval_ms = sum(r["retrieval_latency_ms"] for r in results) / len(results)
    avg_llm_ms = sum(r["llm_latency_ms"] for r in results) / len(results)
    unanswerable_correct = sum(
        1 for r in unanswerable if r["unanswerable_handled"]
    )

    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    print(f"Total questions:        {len(results)}")
    print(f"Answerable questions:   {len(answerable)}")
    print(f"Unanswerable questions: {len(unanswerable)}")
    print(f"")
    print(f"Retrieval Metrics:")
    print(f"  Avg Recall@{TOP_K}:      {avg_recall:.2f}")
    print(f"  Avg MRR:            {avg_mrr:.2f}")
    print(f"")
    print(f"Answer Quality:")
    print(f"  Grounded answers:   {grounded_count}/{len(answerable)}")
    print(f"  Unanswerable handled correctly: {unanswerable_correct}/{len(unanswerable)}")
    print(f"")
    print(f"Latency:")
    print(f"  Avg retrieval:      {avg_retrieval_ms:.0f}ms")
    print(f"  Avg LLM:            {avg_llm_ms:.0f}ms")
    print(f"  Avg total:          {avg_retrieval_ms + avg_llm_ms:.0f}ms")
    print("="*60)

    # save results to file
    output_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "summary": {
                "avg_recall_at_k": avg_recall,
                "avg_mrr": avg_mrr,
                "grounded_rate": grounded_count / len(answerable) if answerable else 0,
                "unanswerable_handled_rate": unanswerable_correct / len(unanswerable) if unanswerable else 0,
                "avg_retrieval_ms": avg_retrieval_ms,
                "avg_llm_ms": avg_llm_ms
            },
            "results": results
        }, f, indent=2)

    logger.info(f"Results saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())