"""
EnterpriseIQ ML — Text Chunking Utilities
Month 1 research deliverable: three chunking strategies benchmarked.

Strategies:
  1. FixedTokenChunker   — 512 tokens, 50 token overlap (default)
  2. SemanticChunker     — split on sentence boundaries using spacy
  3. RecursiveChunker    — recursive character split (LangChain-style)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

from shared.config import get_settings

settings = get_settings()


class _FallbackTokenizer:
    def encode(self, text: str) -> list[str]:
        return re.findall(r"\S+", text)

    def decode(self, tokens: list[str]) -> str:
        return " ".join(tokens)


try:
    _TOKENIZER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _TOKENIZER = _FallbackTokenizer()


@dataclass
class Chunk:
    text: str
    token_count: int
    chunk_index: int


class FixedTokenChunker:
    """
    Default chunking strategy: fixed token windows with overlap.
    Used in production for predictable embedding dimensions.
    """

    def __init__(self, max_tokens: int | None = None,
                 overlap_tokens: int | None = None) -> None:
        self.max_tokens = max_tokens or settings.max_chunk_tokens
        self.overlap = overlap_tokens or settings.chunk_overlap_tokens

    def chunk(self, text: str) -> list[Chunk]:
        tokens = _TOKENIZER.encode(text)
        chunks: list[Chunk] = []
        step = self.max_tokens - self.overlap
        idx = 0

        for i in range(0, len(tokens), step):
            window = tokens[i : i + self.max_tokens]
            chunk_text = _TOKENIZER.decode(window)
            chunks.append(Chunk(
                text=chunk_text,
                token_count=len(window),
                chunk_index=idx,
            ))
            idx += 1

        return chunks


class SemanticChunker:
    """
    Sentence-boundary chunking using spacy.
    Groups sentences until max_tokens reached, then starts new chunk.
    Better for coherent retrieval — used for research/evaluation.
    """

    def __init__(self, max_tokens: int = 512) -> None:
        self.max_tokens = max_tokens
        try:
            import spacy
            self._nlp = spacy.load("en_core_web_sm")
            self._available = True
        except OSError:
            self._available = False

    def chunk(self, text: str) -> list[Chunk]:
        if not self._available:
            return FixedTokenChunker().chunk(text)

        doc = self._nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

        chunks: list[Chunk] = []
        current: list[str] = []
        current_tokens = 0
        idx = 0

        for sentence in sentences:
            sent_tokens = len(_TOKENIZER.encode(sentence))

            if current_tokens + sent_tokens > self.max_tokens and current:
                chunk_text = " ".join(current)
                chunks.append(Chunk(text=chunk_text, token_count=current_tokens, chunk_index=idx))
                idx += 1
                current = []
                current_tokens = 0

            current.append(sentence)
            current_tokens += sent_tokens

        if current:
            chunk_text = " ".join(current)
            chunks.append(Chunk(text=chunk_text, token_count=current_tokens, chunk_index=idx))

        return chunks


class RecursiveChunker:
    """
    Recursive character-level split — tries paragraph → sentence → word boundaries.
    LangChain-compatible approach.
    """

    SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 50) -> None:
        self.max_tokens = max_tokens
        self.overlap = overlap_tokens

    def chunk(self, text: str) -> list[Chunk]:
        chunks = self._split(text, self.SEPARATORS)
        result: list[Chunk] = []
        for i, c in enumerate(chunks):
            result.append(Chunk(
                text=c,
                token_count=len(_TOKENIZER.encode(c)),
                chunk_index=i,
            ))
        return result

    def _split(self, text: str, separators: list[str]) -> list[str]:
        if not separators:
            return [text]

        sep = separators[0]
        parts = text.split(sep) if sep else list(text)

        good: list[str] = []
        current = ""

        for part in parts:
            candidate = (current + sep + part).strip() if current else part
            if len(_TOKENIZER.encode(candidate)) <= self.max_tokens:
                current = candidate
            else:
                if current:
                    good.append(current)
                if len(_TOKENIZER.encode(part)) > self.max_tokens:
                    good.extend(self._split(part, separators[1:]))
                    current = ""
                else:
                    current = part

        if current:
            good.append(current)

        return good
