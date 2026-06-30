"""
tokenizer.py

Two ways to count tokens for this project:

    approximate_tokens(text)  -> the len(text) // 4 rule-of-thumb heuristic
    bpe_tokens(text)          -> a REAL subword count, via tiktoken (BPE)

tiktoken needs to download its vocabulary/merge-rule file the first
time it's used (it's not bundled in the pip package itself). If that
download can't happen -- no internet, a restricted network, the
package isn't installed -- bpe_tokens() falls back to
approximate_tokens() automatically, and tells you it did so via the
returned TokenCountResult.exact flag.
"""

from __future__ import annotations


def approximate_tokens(text: str) -> int:
    """Rough rule-of-thumb: ~4 characters per token for English text.

    This is NOT real tokenization -- no vocabulary, no merge rules, just
    a quick heuristic. Useful as a zero-dependency fallback, and as a
    point of comparison against real BPE counts.
    """
    return max(1, len(text) // 4)


class TokenCountResult:
    def __init__(self, token_count: int, exact: bool, note: str = "") -> None:
        self.token_count = token_count
        self.exact = exact
        self.note = note

    def __repr__(self) -> str:
        precision = "exact (BPE)" if self.exact else "approximate"
        return f"TokenCountResult({self.token_count} tokens, {precision})"


_encoding = None  # lazy-loaded, shared across calls so we only load it once


def bpe_tokens(text: str, encoding_name: str = "cl100k_base") -> TokenCountResult:
    """
    Real subword token count using tiktoken (Byte Pair Encoding), the
    same family of tokenizer used by GPT models.

    Falls back to approximate_tokens() if tiktoken isn't installed, or
    if it can't reach the network to download its vocabulary file on
    first use -- this mirrors the graceful-fallback pattern used in the
    TokenCostEstimator project's ClaudeTokenizer/GPTTokenizer classes.
    """
    global _encoding

    try:
        if _encoding is None:
            import tiktoken

            _encoding = tiktoken.get_encoding(encoding_name)

        tokens = _encoding.encode(text)
        return TokenCountResult(token_count=len(tokens), exact=True)

    except Exception as e:
        approx = approximate_tokens(text)
        return TokenCountResult(
            token_count=approx,
            exact=False,
            note=f"tiktoken unavailable ({e.__class__.__name__}), used approximation",
        )
