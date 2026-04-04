import asyncio
import time

import httpx
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import SessionLocal, engine, Base
import models
import schemas

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PromptLab API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

OLLAMA_BASE = "http://localhost:11434"
OLLAMA_TIMEOUT = 30


# ---------------- DB Dependency ----------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- Ollama Health Check ----------------

async def is_ollama_running() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


# ---------------- Health ----------------

@app.get("/")
def home():
    return {"message": "PromptLab API is running 🚀", "version": "3.0.0"}


@app.get("/health")
async def health_check():
    ollama_up = await is_ollama_running()
    return {
        "api": "ok",
        "ollama": "ok" if ollama_up else "offline",
        "ollama_url": OLLAMA_BASE,
    }


# ---------------- Prompts ----------------

@app.get("/prompts")
def list_prompts(db: Session = Depends(get_db)):
    prompts = db.query(models.Prompt).order_by(models.Prompt.created_at.desc()).all()
    result = []
    for p in prompts:
        version_count = db.query(func.count(models.PromptVersion.id)).filter(
            models.PromptVersion.prompt_id == p.id
        ).scalar()
        result.append({
            "id": p.id,
            "name": p.name,
            "created_at": p.created_at,
            "version_count": version_count or 0,
        })
    return result


@app.get("/prompts/{prompt_id}")
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    version_count = db.query(func.count(models.PromptVersion.id)).filter(
        models.PromptVersion.prompt_id == prompt_id
    ).scalar()
    return {
        "id": prompt.id,
        "name": prompt.name,
        "created_at": prompt.created_at,
        "version_count": version_count or 0,
    }


@app.post("/prompts", status_code=201)
def create_prompt(data: schemas.PromptCreate, db: Session = Depends(get_db)):
    new_prompt = models.Prompt(name=data.name)
    db.add(new_prompt)
    db.commit()
    db.refresh(new_prompt)
    return {"id": new_prompt.id, "name": new_prompt.name, "created_at": new_prompt.created_at, "version_count": 0}


@app.delete("/prompts/{prompt_id}", status_code=204)
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    db.delete(prompt)
    db.commit()


# ---------------- Versions ----------------

@app.get("/prompts/{prompt_id}/versions")
def list_versions(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    versions = db.query(models.PromptVersion).filter(
        models.PromptVersion.prompt_id == prompt_id
    ).order_by(models.PromptVersion.version_number).all()

    result = []
    for v in versions:
        avg_score = db.query(func.avg(models.Result.score)).filter(
            models.Result.version_id == v.id
        ).scalar()
        result.append({
            "id": v.id,
            "version_number": v.version_number,
            "content": v.content,
            "created_at": v.created_at,
            "avg_score": round(avg_score, 2) if avg_score is not None else None,
        })
    return result


@app.post("/prompts/{prompt_id}/versions", status_code=201)
def create_version(prompt_id: int, data: schemas.VersionCreate, db: Session = Depends(get_db)):
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    max_version = db.query(func.max(models.PromptVersion.version_number)).filter(
        models.PromptVersion.prompt_id == prompt_id
    ).scalar()

    version_number = (max_version or 0) + 1
    new_version = models.PromptVersion(
        prompt_id=prompt_id,
        version_number=version_number,
        content=data.content,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


@app.delete("/prompts/{prompt_id}/versions/{version_id}", status_code=204)
def delete_version(prompt_id: int, version_id: int, db: Session = Depends(get_db)):
    version = db.query(models.PromptVersion).filter(
        models.PromptVersion.id == version_id,
        models.PromptVersion.prompt_id == prompt_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    db.delete(version)
    db.commit()


# ---------------- LLM helpers ----------------

async def call_ollama(prompt: str, model: str, timeout: int = OLLAMA_TIMEOUT) -> str:
    """Core Ollama call — raises on failure so callers can handle gracefully."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()


async def run_llm_async(prompt_content: str, user_input: str, model: str = "mistral") -> str:
    full_prompt = f"{prompt_content}\n\nUser Input:\n{user_input}"
    try:
        return await call_ollama(full_prompt, model)
    except Exception as e:
        return f"[LLM Error: {str(e)}]"


async def score_dimension(output: str, user_input: str, dimension: str, model: str = "phi") -> float:
    """
    Score a single quality dimension from 1–10.
    dimension: 'clarity', 'relevance', 'grammar'
    """
    dimension_prompts = {
        "clarity": (
            f"Rate the CLARITY of the following response from 1 to 10.\n"
            f"Clarity means: easy to understand, well-structured, no ambiguity.\n\n"
            f"Response:\n{output}\n\nOnly return a single number between 1 and 10. Nothing else."
        ),
        "relevance": (
            f"Rate the RELEVANCE of the following response to the given user input from 1 to 10.\n"
            f"Relevance means: directly answers what was asked, stays on topic.\n\n"
            f"User input: {user_input}\n\n"
            f"Response:\n{output}\n\nOnly return a single number between 1 and 10. Nothing else."
        ),
        "grammar": (
            f"Rate the GRAMMAR and writing quality of the following response from 1 to 10.\n"
            f"Consider: spelling, sentence structure, punctuation, fluency.\n\n"
            f"Response:\n{output}\n\nOnly return a single number between 1 and 10. Nothing else."
        ),
    }

    prompt = dimension_prompts.get(dimension, dimension_prompts["clarity"])

    try:
        raw = await call_ollama(prompt, model, timeout=15)
        # Extract first number found in response
        import re
        numbers = re.findall(r"\b([1-9]|10)\b", raw)
        if numbers:
            return round(float(numbers[0]), 2)
        return 5.0
    except Exception:
        return 5.0


async def evaluate_multi_async(output: str, user_input: str, model: str = "phi") -> dict:
    """Run all 3 scoring dimensions concurrently and return scores + composite."""
    clarity, relevance, grammar = await asyncio.gather(
        score_dimension(output, user_input, "clarity", model),
        score_dimension(output, user_input, "relevance", model),
        score_dimension(output, user_input, "grammar", model),
    )

    # Weighted composite: relevance matters most
    composite = round(
        (clarity * 0.30) + (relevance * 0.50) + (grammar * 0.20),
        2,
    )

    return {
        "clarity": clarity,
        "relevance": relevance,
        "grammar": grammar,
        "composite": composite,
    }


async def run_version(version: models.PromptVersion, input_text: str):
    """Run LLM + multi-dim evaluation for a single version."""
    start = time.time()
    output = await run_llm_async(version.content, input_text)
    latency = round(time.time() - start, 3)

    # If LLM failed, return safe defaults
    if output.startswith("[LLM Error"):
        return {
            "version": version.version_number,
            "version_id": version.id,
            "output": output,
            "score": 0.0,
            "scores": {"clarity": 0.0, "relevance": 0.0, "grammar": 0.0, "composite": 0.0},
            "latency": latency,
            "error": True,
        }

    scores = await evaluate_multi_async(output, input_text)

    return {
        "version": version.version_number,
        "version_id": version.id,
        "output": output,
        "score": scores["composite"],   # keep top-level score = composite for backward compat
        "scores": scores,
        "latency": latency,
        "error": False,
    }


# ---------------- Experiments ----------------

@app.post("/experiments/run")
async def run_experiment(data: schemas.ExperimentRun, db: Session = Depends(get_db)):

    # ✅ Check Ollama FIRST — fail fast with a clear error
    if not await is_ollama_running():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ollama_offline",
                "message": "Ollama is not running. Start it with: ollama serve",
                "tip": "Make sure your model is pulled: ollama pull mistral && ollama pull phi",
            },
        )

    prompt = db.query(models.Prompt).filter(models.Prompt.id == data.prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    versions = db.query(models.PromptVersion).filter(
        models.PromptVersion.prompt_id == data.prompt_id
    ).all()

    if not versions:
        raise HTTPException(status_code=400, detail="No versions found for this prompt")

    experiment = models.Experiment(prompt_id=data.prompt_id, input_text=data.input_text)
    db.add(experiment)
    db.commit()
    db.refresh(experiment)

    # Run all versions concurrently
    tasks = [run_version(v, data.input_text) for v in versions]
    results_data = await asyncio.gather(*tasks)

    # Persist results
    for r in results_data:
        result = models.Result(
            experiment_id=experiment.id,
            version_id=r["version_id"],
            output=r["output"],
            score=r["score"],
            clarity_score=r["scores"]["clarity"],
            relevance_score=r["scores"]["relevance"],
            grammar_score=r["scores"]["grammar"],
            latency=r["latency"],
        )
        db.add(result)
    db.commit()

    results_out = [
        {
            "version": r["version"],
            "output": r["output"],
            "score": r["score"],
            "scores": r["scores"],
            "latency": r["latency"],
            "error": r.get("error", False),
        }
        for r in results_data
    ]

    successful = [r for r in results_out if not r["error"]]
    if not successful:
        raise HTTPException(status_code=500, detail="All LLM calls failed. Check Ollama logs.")

    best = max(successful, key=lambda x: x["score"])

    return {
        "experiment_id": experiment.id,
        "results": results_out,
        "best_version": best,
    }


@app.get("/experiments")
def list_experiments(prompt_id: int = None, db: Session = Depends(get_db)):
    query = db.query(models.Experiment).order_by(models.Experiment.created_at.desc())
    if prompt_id:
        query = query.filter(models.Experiment.prompt_id == prompt_id)
    experiments = query.limit(100).all()
    return [
        {
            "id": e.id,
            "prompt_id": e.prompt_id,
            "input_text": e.input_text,
            "created_at": e.created_at,
            "result_count": db.query(func.count(models.Result.id))
                              .filter(models.Result.experiment_id == e.id)
                              .scalar() or 0,
        }
        for e in experiments
    ]


@app.get("/experiments/{exp_id}")
def get_experiment(exp_id: int, db: Session = Depends(get_db)):
    experiment = db.query(models.Experiment).filter(models.Experiment.id == exp_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    results = db.query(models.Result).filter(models.Result.experiment_id == exp_id).all()

    if not results:
        return {"experiment_id": exp_id, "results": [], "best_version": None}

    best = max(results, key=lambda x: x.score)

    return {
        "experiment_id": exp_id,
        "input_text": experiment.input_text,
        "created_at": experiment.created_at,
        "results": [
            {
                "version_id": r.version_id,
                "output": r.output,
                "score": r.score,
                "scores": {
                    "clarity": r.clarity_score,
                    "relevance": r.relevance_score,
                    "grammar": r.grammar_score,
                    "composite": r.score,
                },
                "latency": r.latency,
            }
            for r in results
        ],
        "best_version": best.version_id,
    }


# ---------------- Compare ----------------

@app.get("/prompts/{prompt_id}/compare")
def compare_versions(prompt_id: int, db: Session = Depends(get_db)):
    versions = db.query(models.PromptVersion).filter(
        models.PromptVersion.prompt_id == prompt_id
    ).order_by(models.PromptVersion.version_number).all()

    if not versions:
        raise HTTPException(status_code=404, detail="No versions found")

    return [
        {
            "version": v.version_number,
            "content": v.content,
            "avg_score": round(
                db.query(func.avg(models.Result.score)).filter(models.Result.version_id == v.id).scalar() or 0.0, 2
            ),
            "avg_clarity": round(
                db.query(func.avg(models.Result.clarity_score)).filter(models.Result.version_id == v.id).scalar() or 0.0, 2
            ),
            "avg_relevance": round(
                db.query(func.avg(models.Result.relevance_score)).filter(models.Result.version_id == v.id).scalar() or 0.0, 2
            ),
            "avg_grammar": round(
                db.query(func.avg(models.Result.grammar_score)).filter(models.Result.version_id == v.id).scalar() or 0.0, 2
            ),
            "avg_latency": round(
                db.query(func.avg(models.Result.latency)).filter(models.Result.version_id == v.id).scalar() or 0.0, 3
            ),
            "run_count": db.query(func.count(models.Result.id)).filter(models.Result.version_id == v.id).scalar() or 0,
        }
        for v in versions
    ]
