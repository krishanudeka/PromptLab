from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
import requests

app = FastAPI()

Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Home route
@app.get("/")
def home():
    return {"message": "API is working"}

# 🔥 Create Prompt API
@app.post("/prompts")
def create_prompt(name: str, db: Session = Depends(get_db)):
    new_prompt = models.Prompt(name=name)
    db.add(new_prompt)
    db.commit()
    db.refresh(new_prompt)
    
    return {"id": new_prompt.id, "name": new_prompt.name}

@app.post("/prompts/{prompt_id}/versions")
def create_version(prompt_id: int, content: str, db: Session = Depends(get_db)):
    
    # find existing versions
    existing_versions = db.query(models.PromptVersion).filter(
        models.PromptVersion.prompt_id == prompt_id
    ).all()
    
    version_number = len(existing_versions) + 1

    new_version = models.PromptVersion(
        prompt_id=prompt_id,
        version_number=version_number,
        content=content
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    return {
        "version_id": new_version.id,
        "version_number": new_version.version_number,
        "content": new_version.content
    }

def fake_llm(prompt, user_input):
    return f"[Prompt]: {prompt} \n[Answer]: Response to '{user_input}'"

@app.post("/experiments/run")
def run_experiment(prompt_id: int, input_text: str, db: Session = Depends(get_db)):
    
    experiment = models.Experiment(
        prompt_id=prompt_id,
        input_text=input_text
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)

    versions = db.query(models.PromptVersion).filter(
        models.PromptVersion.prompt_id == prompt_id
    ).all()

    results = []

    for version in versions:
        output = fake_llm(version.content, input_text)
        score = evaluate(output)

        result = models.Result(
            experiment_id=experiment.id,
            version_id=version.id,
            output=output,
            score=score
        )

        db.add(result)

        results.append({
            "version": version.version_number,
            "output": output,
            "score": score
        })

    db.commit()

    best_result = max(results, key=lambda x: x["score"])

    return {
        "experiment_id": experiment.id,
        "results": results,
        "best_version": best_result
    }

def evaluate(output):
    prompt = f"""
    Rate this response from 1 to 10 based on clarity, usefulness, and quality.

    Response:
    {output}

    Only return a number.
    """

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "phi",
            "prompt": prompt,
            "stream": False
        }
    )

    result = response.json()["response"].strip()

    try:
        return float(result)
    except:
        return 5.0