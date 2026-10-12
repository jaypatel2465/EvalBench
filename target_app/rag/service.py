from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas.domain import GenerationRequest
from app.services.providers.http import HTTPModelProvider


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class LexicalRetriever:
    """Small dependency-free BM25-style retriever appropriate for the bundled corpus."""

    def __init__(self, corpus_path: Path) -> None:
        self.documents: list[dict[str, Any]] = json.loads(corpus_path.read_text(encoding="utf-8"))
        self.term_counts = [Counter(tokenize(doc["text"])) for doc in self.documents]
        self.doc_frequency = Counter(term for terms in self.term_counts for term in terms)

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        terms, n = set(tokenize(query)), len(self.documents)
        scored = []
        for doc, counts in zip(self.documents, self.term_counts, strict=True):
            score = sum((1 + math.log(counts[term])) * math.log((n + 1) / (self.doc_frequency[term] + .5)) for term in terms if counts[term])
            if score > 0:
                scored.append({"source_id": doc["id"], "company": doc["company"], "filing": doc["filing"],
                    "section": doc["section"], "text": doc["text"], "score": round(score, 6)})
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]


class RAGService:
    def __init__(self, corpus_path: Path = Path("target_app/rag/corpus.json")) -> None:
        self.retriever = LexicalRetriever(corpus_path)
        self.settings = get_settings()

    def _generator(self) -> HTTPModelProvider | None:
        model = self.settings.default_model
        if model.startswith("ollama/"):
            return HTTPModelProvider(name="ollama", model=model.split("/", 1)[1], base_url=self.settings.ollama_base_url)
        if self.settings.openai_api_key and not model.startswith("mock-"):
            return HTTPModelProvider(name="openai", model=model, base_url="https://api.openai.com/v1", api_key=self.settings.openai_api_key)
        return None

    async def query(self, question: str) -> dict[str, Any]:
        started = time.perf_counter()
        retrieved = self.retriever.search(question)
        generator = self._generator()
        citations = [{"source_id": chunk["source_id"], "section": chunk["section"], "score": chunk["score"],
            "quote": chunk["text"][:240]} for chunk in retrieved]
        if not retrieved:
            answer, model, usage, cost = "I could not find relevant evidence in the bundled filing corpus.", "extractive-local-v1", {}, 0.0
        elif generator:
            context = "\n\n".join(f"[{item['source_id']}] {item['text']}" for item in retrieved)
            prompt = f"Answer using only the filing excerpts. Cite source IDs in brackets. If unsupported, say so.\n\n{context}\n\nQuestion: {question}"
            generated = await generator.generate(GenerationRequest(prompt=prompt, temperature=0, max_tokens=500))
            answer, model = generated.response, generated.model
            usage = {"input_tokens": generated.input_tokens, "output_tokens": generated.output_tokens, "total_tokens": generated.total_tokens}
            cost = generated.estimated_cost
        else:
            answer = " ".join(chunk["text"] for chunk in retrieved)
            model, cost = "extractive-local-v1", 0.0
            usage = {"input_tokens": len(question.split()), "output_tokens": len(answer.split())}
            usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
        return {"answer": answer, "citations": citations, "model": model, "latency_ms": (time.perf_counter() - started) * 1000,
            **usage, "estimated_cost": cost, "cost_is_estimate": generator is not None,
            "trace": {"query": question, "retrieval": {"algorithm": "bm25-style-v1", "chunks": retrieved}, "generation_mode": model}}

