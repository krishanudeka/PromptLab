# PromptLab

# 🚀 PromptLab

**PromptLab** is a full-stack prompt evaluation platform that enables systematic experimentation, comparison, and scoring of multiple prompt versions using local LLMs.

It is designed to help developers, researchers, and AI engineers understand how prompt design impacts model performance across multiple quality dimensions.

---

## ✨ Features

* 🔁 **Prompt Versioning** — Create and manage multiple versions of a prompt
* 🧪 **Experiment Runner** — Run the same input across all versions
* 📊 **Multi-Dimensional Scoring**

  * Clarity (25%)
  * Relevance (35%)
  * Grammar (15%)
  * Depth (25%)
* 🏆 **Automatic Best Version Selection**
* 📈 **Analytics Dashboard**

  * Score trends
  * Latency trends
  * Per-prompt insights
* ⚡ **Local LLM Integration (Ollama)**
* 🧾 **Experiment History & Debug View**

---

## 🧠 Key Insight

> Increasing prompt complexity does **not always** improve performance.

PromptLab demonstrates that:

* Overly rigid prompts can degrade output quality
* Balanced and flexible prompts yield better results
* Prompt engineering is **non-linear and context-dependent**

---

## 🏗️ Architecture

```
Frontend (HTML/CSS/JS)
        ↓
FastAPI Backend
        ↓
SQLite Database
        ↓
Ollama (LLM inference)
```

---

## 🧩 Tech Stack

### Backend

* FastAPI
* SQLAlchemy
* SQLite

### Frontend

* Vanilla JavaScript
* Chart.js

### AI / Inference

* Ollama (local LLM runtime)

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/PromptLab.git
cd PromptLab
```

---

### 2. Backend setup

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

---

### 3. Start Ollama

```bash
ollama serve
ollama pull tinyllama
```

---

### 4. Run frontend

Open:

```
http://127.0.0.1:5500/frontend/index.html
```

(Use Live Server or any static server)

---

## 🧪 How It Works

1. Create a prompt
2. Add multiple versions
3. Provide a test input
4. Run experiment

The system will:

* Execute all versions against the same input
* Extract structured scores from LLM output
* Compute weighted composite score
* Rank versions automatically

---

## 📊 Scoring System

| Metric    | Weight |
| --------- | ------ |
| Clarity   | 25%    |
| Relevance | 35%    |
| Grammar   | 15%    |
| Depth     | 25%    |

Composite Score = Weighted average of all metrics

---

## 📈 Example Insight

In experiments:

* Highly structured prompts performed worse due to rigidity
* Flexible structured prompts achieved the highest scores
* Longer outputs did not necessarily imply better quality

---

## 🧠 Design Decisions

* **Batch DB commit** for performance and consistency
* **Error-safe experiment execution** with rollback
* **Separation of concerns** (Frontend / Backend / DB)
* **Scalable schema design** for prompt/version/result tracking

---

## 🚧 Future Improvements

* Parallel experiment execution (async batching)
* Prompt auto-optimization suggestions
* Model comparison (multiple LLMs)
* User authentication & multi-tenant support
* Export results (CSV / JSON)

---

## 🏆 Why This Project Matters

PromptLab goes beyond simple prompt testing — it provides a **structured evaluation framework** for prompt engineering.

It highlights that:

> Prompt engineering is an empirical, data-driven process — not guesswork.

---

## 👨‍💻 Author

**Krishanu Deka**

---

## ⭐ If you found this useful

Give it a star ⭐ on GitHub!
