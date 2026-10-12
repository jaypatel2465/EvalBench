from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from target_app.rag import RAGService

app = FastAPI(title="EvalBench SEC RAG Target", version="0.1.0")
service = RAGService()


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=20_000)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "target": "sec-rag"}


@app.post("/query")
async def query(payload: QueryRequest) -> dict:
    return await service.query(payload.question)

