import re
import time
import asyncio
import httpx
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import SessionLocal, engine, Base
import models
import schemas
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PromptLab Elite Pro", version="4.5.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
DEBUG = False
# Use 127.0.0.1 for Windows stability
OLLAMA_BASE = "http://127.0.0.1:11434"
LLM_MODEL   = "phi"
TIMEOUT     = 600 # 10 Minutes

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── OLLAMA UTILITIES ─────────────────────────────────────────

async def is_ollama_running():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            return r.status_code == 200
    except Exception as e:
        print(f"[OLLAMA HEALTH ERROR] {e}")
        return False

async def call_ollama(prompt: str):
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    f"{OLLAMA_BASE}/api/generate",
                    json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
                )
                res = response.json().get("response", "").strip()
                print(f"[OLLAMA] Generated {len(res)} characters.")
                return res
        except Exception as e:
            print(f"[OLLAMA ERROR] Attempt {attempt+1} failed: {e}")
            if attempt == 0: await asyncio.sleep(3)
    return ""

# ── ADVANCED PARSER ──────────────────────────────────────────

def _parse_response(raw: str):
    """Detects scores anywhere in text, handles decimals/separators."""
    scores = {"CLARITY": 5.0, "RELEVANCE": 5.0, "GRAMMAR": 5.0, "DEPTH": 5.0}

    if DEBUG:
        print("\n" + "="*30 + "\nDEBUG: RAW AI RESPONSE CONTENT:\n" + raw + "\n" + "="*30)

    for key in scores.keys():
        # Captures Clarity: 9, Clarity=9.5, Clarity - 8/10
        pattern = rf"{key}\s*[:=\-]?\s*(\d+(\.\d+)?)"
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            scores[key] = max(1.0, min(10.0, float(match.group(1))))

    # Remove score lines from final display answer
    lines = raw.splitlines()
    clean = [l for l in lines if not l.upper().strip().startswith(tuple(scores.keys()))]
    answer = "\n".join(clean).strip() or raw

    return answer, scores["CLARITY"], scores["RELEVANCE"], scores["GRAMMAR"], scores["DEPTH"]

# ── HEALTH & STATS ──────────────────────────────────────────

@app.get("/health")
async def health():
    up = await is_ollama_running()
    return {"ollama": "ok" if up else "offline"}

@app.get("/stats")
def global_stats(db: Session = Depends(get_db)):
    avg = db.query(func.avg(models.Result.score)).scalar()
    return {
        "total_prompts": db.query(func.count(models.Prompt.id)).scalar() or 0,
        "total_versions": db.query(func.count(models.PromptVersion.id)).scalar() or 0,
        "total_experiments": db.query(func.count(models.Experiment.id)).scalar() or 0,
        "avg_score": round(avg, 2) if avg else 0.0
    }

@app.get("/stats/{prompt_id}")
def prompt_stats(prompt_id: int, db: Session = Depends(get_db)):
    p = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not p: raise HTTPException(404)

    best = db.query(models.PromptVersion.version_number, func.avg(models.Result.score)).join(models.Result).filter(models.PromptVersion.prompt_id == prompt_id).group_by(models.PromptVersion.id).order_by(func.avg(models.Result.score).desc()).first()

    # Calculate actual trend data for the charts
    exps = db.query(models.Experiment).filter(models.Experiment.prompt_id == prompt_id).order_by(models.Experiment.created_at.desc()).limit(10).all()
    trend = []
    for e in reversed(exps):
        avg_s = db.query(func.avg(models.Result.score)).filter(models.Result.experiment_id == e.id).scalar()
        avg_l = db.query(func.avg(models.Result.latency)).filter(models.Result.experiment_id == e.id).scalar()
        trend.append({"experiment_id": e.id, "avg_score": avg_s or 0, "avg_latency": avg_l or 0})

    return {
        "version_count": len(p.versions),
        "experiment_count": len(p.experiments),
        "best_version": {"version_number": best[0], "avg_score": round(best[1],1)} if best else None,
        "trend": trend
    }

# ── PROMPTS & VERSIONS ───────────────────────────────────────

@app.get("/prompts")
def list_prompts(db: Session = Depends(get_db)):
    # Explicit mapping fixes the 'undefinedv' sidebar issue
    prompts = db.query(models.Prompt).order_by(models.Prompt.id.desc()).all()
    return [{
        "id": p.id, "name": p.name, 
        "version_count": len(p.versions), 
        "experiment_count": len(p.experiments)
    } for p in prompts]

@app.get("/prompts/{prompt_id}/versions")
def list_versions(prompt_id: int, db: Session = Depends(get_db)):
    v_list = db.query(models.PromptVersion).filter(models.PromptVersion.prompt_id == prompt_id).all()
    
    # Ranking Logic
    temp = [{"id": x.id, "avg": db.query(func.avg(models.Result.score)).filter(models.Result.version_id == x.id).scalar() or 0} for x in v_list]
    temp.sort(key=lambda x: x["avg"], reverse=True)
    rank_map = {item["id"]: i + 1 for i, item in enumerate(temp) if item["avg"] > 0}

    return [{
        "id": v.id, "version_number": v.version_number, "content": v.content,
        "avg_score": round(db.query(func.avg(models.Result.score)).filter(models.Result.version_id == v.id).scalar() or 0, 1),
        "run_count": len(v.results), "rank": rank_map.get(v.id)
    } for v in v_list]

# ── THE ULTIMATE EXPERIMENT RUNNER ───────────────────────────

@app.post("/experiments/run")
async def run_experiment(data: schemas.ExperimentRun, db: Session = Depends(get_db)):
    if not await is_ollama_running(): raise HTTPException(503, "Ollama Offline")

    versions = (
        db.query(models.PromptVersion)
        .filter(models.PromptVersion.prompt_id == data.prompt_id)
        .order_by(models.PromptVersion.version_number)
        .all()
    )
    if not versions: raise HTTPException(400, "No versions found")

    exp = models.Experiment(prompt_id=data.prompt_id, input_text=data.input_text)
    db.add(exp); db.commit(); db.refresh(exp)

    try:
        for v in versions:
            start = time.time()
            print(f"[EXP] Running v{v.version_number}...")

            prompt_text = (
                f"You are a STRICT technical auditor. First, answer the user question properly.\n"
                f"Persona to use: {v.content}\n"
                f"User Question: {data.input_text}\n\n"
                "After your answer, you MUST STRICTLY provide these 4 scores:\n"
                "CLARITY: [1-10]\nRELEVANCE: [1-10]\nGRAMMAR: [1-10]\nDEPTH: [1-10]"
            )

            raw = await call_ollama(prompt_text)

            if not raw:
                ans, c, r, g, d, score = "[LLM TIMEOUT ERROR]", 2.0, 2.0, 2.0, 2.0, 2.0
            else:
                ans, c, r, g, d = _parse_response(raw)
                score = round((c*0.25)+(r*0.35)+(g*0.15)+(d*0.25), 2)

            res = models.Result(
                experiment_id=exp.id,
                version_id=v.id,
                output=ans,
                score=score,
                clarity_score=c,
                relevance_score=r,
                grammar_score=g,
                depth_score=d,
                latency=round(time.time() - start, 2)
            )

            db.add(res)

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Experiment failed: {str(e)}")

    return get_experiment(exp.id, db)

# ── DETAIL VIEWS ─────────────────────────────────────────────

@app.get("/experiments/{exp_id}")
def get_experiment(exp_id: int, db: Session = Depends(get_db)):
    exp = db.query(models.Experiment).filter(models.Experiment.id == exp_id).first()
    if not exp: raise HTTPException(404)
    version_map = {
        v.id: v.version_number
        for v in db.query(models.PromptVersion).all()
    }
    # Safe Version Lookup (No mapping bugs)
    results = []
    for r in exp.results:
        results.append({
            "version": version_map.get(r.version_id, 0),
            "output": r.output,
            "score": r.score,
            "latency": r.latency,
            "scores": {
                "clarity": r.clarity_score,
                "relevance": r.relevance_score,
                "grammar": r.grammar_score,
                "depth": r.depth_score
            }
        })

    valid_results = [r for r in results if r.get("score") is not None]

    best = max(valid_results, key=lambda x: x["score"], default=None)
    return {
        "id": exp.id,
        "input_text": exp.input_text,
        "created_at": exp.created_at,
        "results": results,
        "best_version": {
            "version": best["version"],
            "score": best["score"]
        } if best else None
    }

@app.get("/experiments")
def list_experiments(db: Session = Depends(get_db)):
    exps = db.query(models.Experiment).order_by(models.Experiment.created_at.desc()).limit(50).all()
    return [{"id": e.id, "prompt_id": e.prompt_id, "input_text": e.input_text, "created_at": e.created_at, "result_count": len(e.results)} for e in exps]

@app.post("/prompts")
def create_prompt(data: schemas.PromptCreate, db: Session = Depends(get_db)):
    p = models.Prompt(name=data.name); db.add(p); db.commit(); db.refresh(p); return p

@app.post("/prompts/{prompt_id}/versions")
def create_version(prompt_id: int, data: schemas.VersionCreate, db: Session = Depends(get_db)):
    last = db.query(func.max(models.PromptVersion.version_number)).filter(models.PromptVersion.prompt_id == prompt_id).scalar() or 0
    v = models.PromptVersion(prompt_id=prompt_id, version_number=last+1, content=data.content)
    db.add(v); db.commit(); db.refresh(v); return v


@app.get("/prompts/{prompt_id}/compare")
def compare_versions(prompt_id: int, db: Session = Depends(get_db)):
    versions = db.query(models.PromptVersion)\
        .filter(models.PromptVersion.prompt_id == prompt_id)\
        .order_by(models.PromptVersion.version_number)\
        .all()

    data = []
    for v in versions:
        data.append({
            "version": v.version_number,
            "avg_score": db.query(func.avg(models.Result.score)).filter(models.Result.version_id == v.id).scalar() or 0,
            "avg_clarity": db.query(func.avg(models.Result.clarity_score)).filter(models.Result.version_id == v.id).scalar() or 0,
            "avg_relevance": db.query(func.avg(models.Result.relevance_score)).filter(models.Result.version_id == v.id).scalar() or 0,
            "avg_grammar": db.query(func.avg(models.Result.grammar_score)).filter(models.Result.version_id == v.id).scalar() or 0,
            "avg_depth": db.query(func.avg(models.Result.depth_score)).filter(models.Result.version_id == v.id).scalar() or 0,
            "avg_latency": db.query(func.avg(models.Result.latency)).filter(models.Result.version_id == v.id).scalar() or 0,
            "run_count": db.query(models.Result).filter(models.Result.version_id == v.id).count()
        })

    return data
