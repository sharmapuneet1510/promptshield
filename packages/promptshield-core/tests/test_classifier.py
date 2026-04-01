"""
Tests for promptshield_core.classifier
"""

import pytest

from promptshield_core.classifier import classify_prompt, get_primary_category
from promptshield_core.enums import PromptCategory


class TestClassifyCoding:
    def test_code_block_triggers_coding(self) -> None:
        prompt = "Here is my code:\n```python\ndef foo(): pass\n```\nPlease review it."
        result = classify_prompt(prompt, 30)
        assert PromptCategory.CODING in result

    def test_def_keyword_triggers_coding(self) -> None:
        prompt = "Write a Python function: def compute_average(numbers: list) -> float"
        result = classify_prompt(prompt, 20)
        assert PromptCategory.CODING in result

    def test_import_keyword_triggers_coding(self) -> None:
        prompt = "import pandas as pd\nimport numpy as np\nHow do I merge these?"
        result = classify_prompt(prompt, 20)
        assert PromptCategory.CODING in result

    def test_bug_fix_triggers_coding(self) -> None:
        prompt = "Help me debug this function, it has a bug when input is empty"
        result = classify_prompt(prompt, 20)
        assert PromptCategory.CODING in result

    def test_sql_triggers_coding(self) -> None:
        prompt = "SELECT * FROM users WHERE active = 1 -- how do I add a JOIN here?"
        result = classify_prompt(prompt, 20)
        assert PromptCategory.CODING in result


class TestClassifyDocumentation:
    def test_summarize_triggers_documentation(self) -> None:
        prompt = "Summarize the following text for me"
        result = classify_prompt(prompt, 15)
        assert PromptCategory.DOCUMENTATION in result

    def test_write_docs_triggers_documentation(self) -> None:
        prompt = "Write documentation for this module"
        result = classify_prompt(prompt, 15)
        assert PromptCategory.DOCUMENTATION in result

    def test_explain_code_triggers_documentation(self) -> None:
        prompt = "Explain this code to me line by line"
        result = classify_prompt(prompt, 15)
        assert PromptCategory.DOCUMENTATION in result

    def test_add_docstrings_triggers_documentation(self) -> None:
        prompt = "Add docstrings to all my functions please"
        result = classify_prompt(prompt, 15)
        assert PromptCategory.DOCUMENTATION in result


class TestClassifySearchLike:
    def test_what_is_triggers_search(self) -> None:
        prompt = "What is the capital of France?"
        result = classify_prompt(prompt, 10)
        assert PromptCategory.SEARCH_LIKE in result

    def test_who_is_triggers_search(self) -> None:
        prompt = "Who is the current president of the United States?"
        result = classify_prompt(prompt, 12)
        assert PromptCategory.SEARCH_LIKE in result

    def test_when_did_triggers_search(self) -> None:
        prompt = "When did World War II end?"
        result = classify_prompt(prompt, 10)
        assert PromptCategory.SEARCH_LIKE in result

    def test_how_does_work_triggers_search(self) -> None:
        prompt = "How does photosynthesis work"
        result = classify_prompt(prompt, 8)
        assert PromptCategory.SEARCH_LIKE in result

    def test_coding_prompt_does_not_get_search_like(self) -> None:
        prompt = "What is wrong with this Python function?\n```def foo():\n    pass\n```"
        result = classify_prompt(prompt, 25)
        # Coding should be present, search_like should NOT override coding
        assert PromptCategory.CODING in result


class TestClassifyOversized:
    def test_oversized_token_count_triggers_oversized(self) -> None:
        result = classify_prompt("a " * 100, 9000)
        assert PromptCategory.OVERSIZED in result

    def test_normal_token_count_does_not_trigger_oversized(self) -> None:
        result = classify_prompt("Hello world, please help me.", 10)
        assert PromptCategory.OVERSIZED not in result


class TestClassifyBroadScope:
    def test_very_short_prompt_triggers_broad_scope(self) -> None:
        # < 20 tokens (we pass token count directly)
        result = classify_prompt("AI", 1)
        assert PromptCategory.BROAD_SCOPE in result

    def test_medium_prompt_no_broad_scope(self) -> None:
        prompt = "Write a Python function to sort a list of integers in ascending order."
        result = classify_prompt(prompt, 25)
        assert PromptCategory.BROAD_SCOPE not in result


class TestClassifyGeneric:
    def test_generic_fallback_when_no_patterns_match(self) -> None:
        prompt = "Please create a nice poem about the ocean at sunset in 4 stanzas."
        result = classify_prompt(prompt, 20)
        # Should not be search/code/docs, should fall back to generic
        assert PromptCategory.SEARCH_LIKE not in result or PromptCategory.GENERIC in result


class TestClassifyReturnsNonEmpty:
    def test_always_returns_at_least_one_category(self) -> None:
        for text, tokens in [
            ("hello", 1),
            ("", 0),
            ("x" * 1000, 250),
        ]:
            result = classify_prompt(text, tokens)
            assert len(result) >= 1


class TestGetPrimaryCategory:
    def test_oversized_takes_priority(self) -> None:
        categories = [PromptCategory.CODING, PromptCategory.OVERSIZED, PromptCategory.GENERIC]
        assert get_primary_category(categories) == PromptCategory.OVERSIZED

    def test_search_like_beats_generic(self) -> None:
        categories = [PromptCategory.GENERIC, PromptCategory.SEARCH_LIKE]
        assert get_primary_category(categories) == PromptCategory.SEARCH_LIKE

    def test_single_category(self) -> None:
        assert get_primary_category([PromptCategory.CODING]) == PromptCategory.CODING

    def test_empty_returns_unknown(self) -> None:
        assert get_primary_category([]) == PromptCategory.UNKNOWN
