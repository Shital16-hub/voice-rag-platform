def recall_at_k(retrieved_chunks: list[str], relevant_content: list[str], k: int) -> float:
    """
    What fraction of relevant content appeared in top K results?

    Example:
      relevant_content = ["20 days of leave", "sick leave 10 days"]
      retrieved_chunks = ["20 days of leave per year", "work from home policy"]
      k = 3
      
      "20 days of leave" found in retrieved → 1 match
      "sick leave 10 days" not found → 0 match
      Recall@3 = 1/2 = 0.5
    """
    if not relevant_content:
        return 1.0  # unanswerable question, no relevant content expected

    retrieved_top_k = retrieved_chunks[:k]
    matches = 0

    for relevant in relevant_content:
        relevant_lower = relevant.lower()
        for chunk in retrieved_top_k:
            if relevant_lower in chunk.lower():
                matches += 1
                break

    return matches / len(relevant_content)


def mean_reciprocal_rank(retrieved_chunks: list[str], relevant_content: list[str]) -> float:
    """
    Where does the first relevant chunk appear in results?
    Higher is better. 1.0 = first position. 0.5 = second position.

    Example:
      First relevant chunk found at position 2
      MRR = 1/2 = 0.5
    """
    if not relevant_content:
        return 1.0  # unanswerable question

    for rank, chunk in enumerate(retrieved_chunks, start=1):
        for relevant in relevant_content:
            if relevant.lower() in chunk.lower():
                return 1.0 / rank

    return 0.0  # relevant content not found at all


def check_answer_groundedness(answer: str, expected_contains: list[str]) -> bool:
    """
    Simple check: does the answer contain expected content?

    This is a basic groundedness check.
    We use LLM-as-judge in the next step for deeper evaluation.
    """
    if not expected_contains:
        return True  # unanswerable question, any response is ok

    answer_lower = answer.lower()
    for expected in expected_contains:
        if expected.lower() in answer_lower:
            return True

    return False


def check_unanswerable_handled(answer: str) -> bool:
    """
    For questions that have no answer in the knowledge base,
    check that the system said so instead of hallucinating.
    """
    refusal_phrases = [
        "could not find",
        "don't have",
        "do not have",
        "no information",
        "not enough information",
        "cannot answer",
        "unable to find"
    ]
    answer_lower = answer.lower()
    return any(phrase in answer_lower for phrase in refusal_phrases)