# 🩺 Enhanced AI Project Doctor

Enhanced AI Project Doctor is a **CLI tool** that scans your project, performs static analysis, and then asks an **AI model** (Gemini, OpenAI, or Anthropic) to give you a diagnosis report.

---

## 🚀 Features

- 🎨 **ASCII Banner & Progress Indicators** for a nice CLI experience.
- ⚙️ **Configurable** via `~/.sophisticated_doctor_config.json`.
- 🤖 **Multi-Provider Support**: Gemini, OpenAI GPT, Anthropic Claude.
- 🗂️ **Project File Scanning** with ignore patterns & size limits.
- 🔍 **Static Analysis** (Python + JavaScript/TypeScript basics).
- 🧠 **AI Diagnosis** with categorized feedback:
  - 🚨 Critical Issues  
  - 🤔 Things You Might Be Forgetting  
  - ✨ Suggestions for Improvement
- 📦 **Caching** of results for faster re-runs.
- 📝 **Markdown Report Output**.

---

## 🛠️ Installation

Clone or download this script. Make sure you have **Python 3.8+** installed.

Install dependencies:
```bash
pip install requests
```

(Other modules used are standard library.)

---

## 🔑 Setup API Keys

Export at least one API key before running:

```bash
export GEMINI_API_KEY="your_api_key"
export OPENAI_API_KEY="your_api_key"
export ANTHROPIC_API_KEY="your_api_key"
```

---

## 📖 Usage

### Analyze a Project
```bash
python enhanced_doctor.py ./my-app -t "Python Flask API"
```

### Choose Provider
```bash
python enhanced_doctor.py ./my-app -t "React app" --provider openai
```

### Save Report to File
```bash
python enhanced_doctor.py ./my-app -t "Node.js API" -o report.md
```

### Ignore Files/Dirs
```bash
python enhanced_doctor.py ./my-app -t "Next.js App" --ignore "docs" --ignore "*.test.js"
```

### Verbose Mode
```bash
python enhanced_doctor.py ./my-app -t "Django Project" -v
```

### Quiet Mode (output only to file)
```bash
python enhanced_doctor.py ./my-app -t "Go Microservice" -q -o diagnosis.md
```

### Show Config
```bash
python enhanced_doctor.py ./my-app -t "Rust API" --config
```

### Disable Caching
```bash
python enhanced_doctor.py ./my-app -t "Express API" --no-cache
```

### Disable Static Analysis
```bash
python enhanced_doctor.py ./my-app -t "Vue.js App" --no-static-analysis
```

---

## 📦 Example Workflow

1. Run first analysis:
```bash
python enhanced_doctor.py ./my-app -t "FastAPI backend" --provider gemini -o fastapi_diagnosis.md
```
2. Make code changes.
3. Re-run (if unchanged, cached results are used):
```bash
python enhanced_doctor.py ./my-app -t "FastAPI backend"
```

---

## ⚡ TL;DR
This tool acts as a **doctor for your repo** 🩺 — it scans, analyzes, and gives you a neat report on what's broken, what's missing, and what could be improved.
