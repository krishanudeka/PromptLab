# 🚀 PromptLab

**PromptLab** is a full-stack prompt evaluation and experimentation platform designed to systematically analyze, compare, and optimize prompt performance for Large Language Models (LLMs).

It provides a **reproducible, metric-driven framework** for evaluating prompt quality across multiple dimensions, enabling developers to move from **trial-and-error prompt engineering → structured, data-driven optimization**.

---

## ✨ Core Capabilities

### 🔁 Prompt Versioning System

* Create and manage multiple prompt variants
* Version-controlled experimentation workflow
* Enables iterative prompt optimization

---

### 🧪 Experimentation Engine

* Executes the same input across all prompt versions
* Ensures **controlled, reproducible comparisons**
* Handles batch execution with latency tracking

---

### 📊 Multi-Dimensional Evaluation (LLM-as-a-Judge)

PromptLab uses an **LLM-based evaluator** to score outputs across structured dimensions:

| Metric    | Description                        | Weight |
| --------- | ---------------------------------- | ------ |
| Clarity   | Structure and readability          | 25%    |
| Relevance | Alignment with user intent         | 35%    |
| Grammar   | Fluency and linguistic quality     | 15%    |
| Depth     | Technical completeness and insight | 25%    |

👉 Composite Score = Weighted aggregation

This aligns with modern prompt evaluation approaches where outputs are scored across multiple quality axes rather than a single metric ([Braintrust][1])

---

### 🏆 Automatic Ranking & Selection

* Identifies best-performing prompt version
* Computes average scores across runs
* Enables data-driven prompt selection

---

### 📈 Analytics & Observability

* Score trends across experiments
* Latency tracking per version
* Historical experiment comparison
* Performance variability insights

---

### ⚡ Local LLM Integration (Ollama)

* Runs fully offline using local models
* No dependency on external APIs
* Supports rapid iteration and testing

---

## 🧠 Why PromptLab Exists

Prompt engineering is inherently **non-deterministic and sensitive to small changes** in wording and structure ([Wikipedia][2])

Traditional approaches rely on intuition and manual testing.

PromptLab introduces:

> ✅ **Structured evaluation**
> ✅ **Quantitative scoring**
> ✅ **Version comparison**
> ✅ **Reproducible experiments**

This transforms prompt engineering into an **engineering discipline instead of guesswork**.

---

## 🏗️ System Architecture

```mermaid id="archpromptlab"
flowchart LR

A[Prompt Versions] --> B[Experiment Engine]
B --> C[LLM - Ollama]
C --> D[Generated Outputs]
D --> E[Evaluation Parser]
E --> F[Scoring Engine]
F --> G[Database - SQLite]
G --> H[API Layer - FastAPI]
H --> I[Frontend Dashboard]
```

---

## 🧩 Tech Stack

### Backend

* FastAPI (API & orchestration)
* SQLAlchemy (ORM)
* SQLite (lightweight persistence)

### Frontend

* Vanilla JavaScript
* HTML / CSS
* Chart.js (visual analytics)

### AI Layer

* Ollama (local LLM runtime)

---

## 📂 Project Structure

```id="promptlabstruct"
PromptLab/
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
├── main.py              # FastAPI app & experiment orchestration
├── models.py            # DB models (Prompt, Version, Result, Experiment)
├── schemas.py           # API schemas
├── database.py          # DB setup
│
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Clone Repository

```bash id="cln"
git clone https://github.com/krishanudeka/PromptLab.git
cd PromptLab
```

---

### 2. Install Dependencies

```bash id="dep"
pip install -r requirements.txt
```

---

### 3. Start Backend

```bash id="runapi"
uvicorn main:app --reload
```

---

### 4. Start Ollama

```bash id="ollama"
ollama serve
ollama pull tinyllama
```

---

### 5. Run Frontend

```id="runfront"
http://127.0.0.1:5500/frontend/index.html
```

---

## 🧪 How It Works

1. Create a prompt
2. Add multiple versions
3. Provide input query
4. Run experiment

The system:

* Executes all versions against the same input
* Captures model outputs
* Parses structured evaluation scores
* Computes weighted metrics
* Ranks prompt performance

---

## 📊 Example Insight

PromptLab reveals critical real-world behavior:

* Increasing prompt complexity **does not guarantee better results**
* Overly rigid prompts can reduce clarity
* Balanced, flexible prompts outperform strict templates

This aligns with research showing prompt performance depends on structure, context, and evaluation criteria rather than wording alone ([Medium][3])

---

## 🧠 Design Decisions

* **Batch DB commits** for consistency and performance
* **LLM-as-a-judge scoring model** for scalable evaluation
* **Schema-driven design** for extensibility
* **Separation of concerns** (UI, API, evaluation, storage)
* **Offline-first architecture** (no API dependency)

---

## 🚧 Future Enhancements

* Parallel experiment execution
* Multi-model benchmarking (GPT, Claude, etc.)
* Prompt auto-optimization (closed-loop feedback)
* Confidence scoring & variance analysis
* Export results (CSV / JSON)
* Role-based user system

---

## 🏆 What Makes This Project Stand Out

Unlike typical LLM demos:

❌ Not just prompt → output
❌ Not a simple chatbot

✔ Prompt evaluation framework
✔ Multi-dimensional scoring system
✔ Version-controlled experimentation
✔ Analytics-driven insights
✔ Full-stack + LLM integration

---

## 👨‍💻 Author

**Krishanu Deka**
GitHub: https://github.com/krishanudeka

---

## ⭐ Support

If you found this useful, consider giving it a ⭐ on GitHub.

[1]: https://www.braintrust.dev/articles/what-is-prompt-evaluation?utm_source=chatgpt.com "What is prompt evaluation? How to test prompts with metrics ..."
[2]: https://en.wikipedia.org/wiki/Prompt_engineering?utm_source=chatgpt.com "Prompt engineering"
[3]: https://medium.com/%40rohitkulkarni2023/measuring-the-unmeasurable-a-deep-dive-into-prompt-evaluation-strategies-88199705937f?utm_source=chatgpt.com "A Deep Dive into Prompt Evaluation Strategies"
