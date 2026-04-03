from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import time
import requests

from database import SessionLocal, engine, Base
import models
import schemas

app = FastAPI()

Base.metadata.create_all(bind=engine)


# ---------------- DB Dependency ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    return {"message": "PromptLab API is running 🚀"}


# ---------------- Create Prompt ----------------
@app.post("/prompts")
def create_prompt(data: schemas.PromptCreate, db: Session = Depends(get_db)):
    new_prompt = models.Prompt(name=data.name)
    db.add(new_prompt)
    db.commit()
    db.refresh(new_prompt)
    return new_prompt


# ---------------- Create Version ----------------
@app.post("/prompts/{prompt_id}/versions")
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
        content=data.content
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    return new_version


# ---------------- REAL LLM (GENERATION) ----------------
def run_llm(prompt, user_input, model="mistral"):
    full_prompt = f"""
    {prompt}

    User Input:
    {user_input}
    """

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": False
            },
            timeout=15
        )

        result = response.json().get("response", "").strip()
        return result

    except Exception as e:
        return f"LLM Error: {str(e)}"


# ---------------- LLM EVALUATION ----------------
def evaluate(output, model="phi"):
    prompt = f"""
    Rate this response from 1 to 10 based on clarity, usefulness, and quality.

    Response:
    {output}

    Only return a number.
    """

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=10
        )

        result = response.json().get("response", "").strip()
        return float(result)

    except Exception:
        return 5.0


# ---------------- Run Experiment ----------------
@app.post("/experiments/run")
def run_experiment(data: schemas.ExperimentRun, db: Session = Depends(get_db)):

    prompt = db.query(models.Prompt).filter(models.Prompt.id == data.prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    experiment = models.Experiment(
        prompt_id=data.prompt_id,
        input_text=data.input_text
    )

    db.add(experiment)
    db.commit()
    db.refresh(experiment)

    versions = db.query(models.PromptVersion).filter(
        models.PromptVersion.prompt_id == data.prompt_id
    ).all()

    if not versions:
        raise HTTPException(status_code=400, detail="No versions found")

    results = []

    for version in versions:
        start_time = time.time()

        # 🔥 REAL LLM OUTPUT
        output = run_llm(version.content, data.input_text, model="mistral")

        latency = time.time() - start_time

        # 🔥 EVALUATION (different model)
        score = evaluate(output, model="phi")

        result = models.Result(
            experiment_id=experiment.id,
            version_id=version.id,
            output=output,
            score=score,
            latency=latency
        )

        db.add(result)

        results.append({
            "version": version.version_number,
            "output": output,
            "score": score,
            "latency": latency
        })

    db.commit()

    best_result = max(results, key=lambda x: x["score"])

    return {
        "experiment_id": experiment.id,
        "results": results,
        "best_version": best_result
    }


# ---------------- Compare Versions ----------------
@app.get("/prompts/{prompt_id}/compare")
def compare_versions(prompt_id: int, db: Session = Depends(get_db)):

    versions = db.query(models.PromptVersion).filter(
        models.PromptVersion.prompt_id == prompt_id
    ).all()

    response = []

    for v in versions:
        avg_score = db.query(func.avg(models.Result.score)).filter(
            models.Result.version_id == v.id
        ).scalar()

        response.append({
            "version": v.version_number,
            "content": v.content,
            "avg_score": avg_score or 0
        })

    return response
