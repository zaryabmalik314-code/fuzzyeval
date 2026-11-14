"""
FuzzyEval API — FastAPI backend
================================
POST /api/query     → send prompt to Groq + Gemini, get both responses
POST /api/evaluate  → rate both responses, run fuzzy TOPSIS, get ranking
GET  /api/health    → health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import os
from pathlib import Path

from llm_clients import query_both
from fuzzy_engine import fuzzy_topsis, LINGUISTIC_LABELS

app = FastAPI(title="FuzzyEval", version="1.0.0")

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)
    groq_api_key: str = Field(..., min_length=1)
    gemini_api_key: str = Field(..., min_length=1)
    groq_model: str = "llama-3.1-70b-versatile"
    gemini_model: str = "gemini-1.5-flash"

class QueryResponse(BaseModel):
    prompt: str
    responses: list[dict]  # [{model_name, provider, response_text, model_id, error}]

class EvaluateRequest(BaseModel):
    ratings: dict[str, list[int]]  # {model_name: [r1, r2, r3, r4]} each 1–5
    criteria_weights: list[int]    # importance of each criterion, 1–5
    criteria_names: list[str] = ["Relevance", "Accuracy", "Completeness", "Clarity"]

class ConfigResponse(BaseModel):
    criteria: list[dict]
    linguistic_scale: dict[int, str]
    models: dict


# ── Routes ────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "FuzzyEval"}


@app.get("/api/config")
async def get_config():
    """Return default criteria, scale, and available models."""
    return {
        "criteria": [
            {"name": "Relevance", "description": "How well the response addresses the prompt"},
            {"name": "Accuracy", "description": "Factual correctness of the response"},
            {"name": "Completeness", "description": "How thoroughly the response covers the topic"},
            {"name": "Clarity", "description": "How clear and well-structured the response is"},
        ],
        "linguistic_scale": LINGUISTIC_LABELS,
        "models": {
            "groq": [
                {"id": "llama-3.1-70b-versatile", "name": "Llama 3.1 70B"},
                {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B"},
                {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B"},
                {"id": "gemma2-9b-it", "name": "Gemma 2 9B"},
            ],
            "gemini": [
                {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
                {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
            ],
        },
    }


@app.post("/api/query")
async def query_models(req: QueryRequest):
    """Send prompt to both LLMs and return their responses."""
    responses = await query_both(
        prompt=req.prompt,
        groq_key=req.groq_api_key,
        gemini_key=req.gemini_api_key,
        groq_model=req.groq_model,
        gemini_model=req.gemini_model,
    )

    return {
        "prompt": req.prompt,
        "responses": [
            {
                "model_name": r.model_name,
                "provider": r.provider,
                "response_text": r.response_text,
                "model_id": r.model_id,
                "error": r.error,
            }
            for r in responses
        ],
    }


@app.post("/api/evaluate")
async def evaluate(req: EvaluateRequest):
    """Run fuzzy TOPSIS evaluation on rated responses."""
    # Validate
    n_criteria = len(req.criteria_names)
    for model, rats in req.ratings.items():
        if len(rats) != n_criteria:
            raise HTTPException(
                status_code=400,
                detail=f"{model} has {len(rats)} ratings, expected {n_criteria}",
            )
        for r in rats:
            if not (1 <= r <= 5):
                raise HTTPException(
                    status_code=400,
                    detail=f"Rating must be 1–5, got {r} for {model}",
                )

    if len(req.criteria_weights) != n_criteria:
        raise HTTPException(
            status_code=400,
            detail=f"Expected {n_criteria} weights, got {len(req.criteria_weights)}",
        )

    result = fuzzy_topsis(
        ratings=req.ratings,
        criteria_weights=req.criteria_weights,
        criteria_names=req.criteria_names,
    )

    return result


# ── Serve frontend build (production) ─────────────────────────────

frontend_build = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(frontend_build), html=True), name="frontend")
