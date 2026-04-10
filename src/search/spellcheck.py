"""
Spellcheck Module - Redis FT.SPELLCHECK
Provides spelling correction suggestions when FTS returns 0 results
"""

import redis
from typing import List, Dict, Any


def spellcheck_query(
    redis_client: redis.Redis,
    query: str,
    indexes: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Use Redis FT.SPELLCHECK to get spelling correction suggestions.

    Tries each index and returns the best suggestion per misspelled term.

    Args:
        redis_client: Redis connection
        query: Original query that returned no results
        indexes: List of index names to check against

    Returns:
        List of correction suggestions, e.g.:
        [{"original": "robaro", "suggestion": "bloquear", "score": 0.95}]
    """
    if indexes is None:
        indexes = ['idx:routes', 'idx:products', 'idx:skus']

    corrections = {}  # original_term -> best suggestion

    for idx_name in indexes:
        try:
            result = redis_client.execute_command(
                "FT.SPELLCHECK", idx_name, query
            )

            # Parse result:
            # Each element is: ['TERM', 'misspelled_word', [['score', 'suggestion'], ...]]
            if not result:
                continue

            for term_result in result:
                if not isinstance(term_result, (list, tuple)) or len(term_result) < 3:
                    continue

                original_term = term_result[1]
                if isinstance(original_term, bytes):
                    original_term = original_term.decode()

                suggestions_list = term_result[2]
                if not suggestions_list:
                    continue

                # Get the best suggestion (highest score)
                for suggestion_pair in suggestions_list:
                    if isinstance(suggestion_pair, (list, tuple)) and len(suggestion_pair) >= 2:
                        try:
                            score = float(suggestion_pair[0])
                            suggested_word = suggestion_pair[1]
                            if isinstance(suggested_word, bytes):
                                suggested_word = suggested_word.decode()

                            # Keep best suggestion per original term
                            if original_term not in corrections or score > corrections[original_term]['score']:
                                corrections[original_term] = {
                                    "original": original_term,
                                    "suggestion": suggested_word,
                                    "score": score
                                }
                        except (ValueError, TypeError, IndexError):
                            continue

        except Exception as e:
            print(f"FT.SPELLCHECK on {idx_name}: {e}")
            continue

    return list(corrections.values())


def get_corrected_query(
    redis_client: redis.Redis,
    query: str,
    indexes: List[str] = None
) -> str:
    """
    Get a corrected version of the query using FT.SPELLCHECK.

    Replaces misspelled words with their best suggestions.

    Args:
        redis_client: Redis connection
        query: Original query
        indexes: List of index names

    Returns:
        Corrected query string (or original if no corrections found)
    """
    corrections = spellcheck_query(redis_client, query, indexes)

    if not corrections:
        return query

    corrected = query
    for correction in corrections:
        corrected = corrected.replace(
            correction['original'],
            correction['suggestion']
        )

    return corrected
