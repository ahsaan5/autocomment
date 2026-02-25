from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

WORD_RE = re.compile(r"[a-zA-Z0-9']+")


class KnowledgeBase:
    """Tiny persistent knowledge base with lexical retrieval."""

    def __init__(self, storage_path: str = "data/knowledge.json") -> None:
        self.storage = Path(storage_path)
        self.storage.parent.mkdir(parents=True, exist_ok=True)
        self.documents: list[dict[str, str]] = []
        self._load()

    def _load(self) -> None:
        if self.storage.exists():
            self.documents = json.loads(self.storage.read_text())

    def _save(self) -> None:
        self.storage.write_text(json.dumps(self.documents, indent=2))

    def add_text(self, text: str, source: str) -> int:
        chunks = self._chunk(text)
        for chunk in chunks:
            self.documents.append({"source": source, "content": chunk})
        self._save()
        return len(chunks)

    def _chunk(self, text: str, size: int = 700) -> list[str]:
        normalized = " ".join(text.split())
        if not normalized:
            return []
        return [normalized[i : i + size] for i in range(0, len(normalized), size)]

    def query(self, question: str, top_k: int = 3) -> list[dict[str, str]]:
        q_vec = self._term_vector(question)
        if not q_vec:
            return []

        scored: list[tuple[float, dict[str, str]]] = []
        for doc in self.documents:
            score = self._cosine_similarity(q_vec, self._term_vector(doc["content"]))
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def context_for(self, question: str, top_k: int = 3) -> str:
        matches = self.query(question, top_k=top_k)
        parts = [f"[{m['source']}] {m['content']}" for m in matches]
        return "\n\n".join(parts)

    @staticmethod
    def _term_vector(text: str) -> Counter[str]:
        return Counter(word.lower() for word in WORD_RE.findall(text))

    @staticmethod
    def _cosine_similarity(a: Counter[str], b: Counter[str]) -> float:
        common = set(a) & set(b)
        dot = sum(a[k] * b[k] for k in common)
        a_norm = math.sqrt(sum(v * v for v in a.values()))
        b_norm = math.sqrt(sum(v * v for v in b.values()))
        if a_norm == 0 or b_norm == 0:
            return 0
        return dot / (a_norm * b_norm)


def merge_text_parts(parts: Iterable[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())
