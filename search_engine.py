# search_engine.py

# Axtarış modullarını burada mərkəzləşdiririk
from search_local import python_lexical_search, deep_content_search
from search_anytxt import (
    anytxt_search, 
    clear_anytxt_cache, 
    fetch_word_score, 
    fetch_from_anytxt
)
from search_utils import normalize_text, expand_search_query

__all__ = [
    "python_lexical_search",
    "deep_content_search",
    "anytxt_search",
    "clear_anytxt_cache",
    "normalize_text",
    "fetch_word_score",
    "fetch_from_anytxt",
    "expand_search_query"
]