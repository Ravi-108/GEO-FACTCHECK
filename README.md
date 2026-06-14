# Fact-Check Agent

> AI-powered claim verification engine that reads PDF documents, extracts factual claims, and cross-references them against live web data.

🌐 **[Live App →](https://your-app.streamlit.app)** · 🎬 **[Demo Video →](https://your-demo-link)**

---

## How It Works

The Fact-Check Agent uses a 4-step AI pipeline to verify claims:

```
📄 Upload PDF  →  🔎 Extract Claims  →  🌐 Web Search  →  ⚖️ AI Verdict
```

| Step | What Happens |
|------|-------------|
| **1. Extract** | PDF text is parsed using `pdfplumber` to pull all readable content |
| **2. Identify** | Advanced OpenRouter LLMs scan the text and extract verifiable factual claims (stats, dates, financials) |
| **3. Verify** | Each claim is searched against live web data via Tavily's advanced search API |
| **4. Judge** | The AI compares the claim against web evidence and delivers a verdict with confidence level |

---

## Verdicts

| Verdict | Meaning |
|---------|---------|
| ✅ **VERIFIED** | Claim matches web evidence |
| ⚠️ **INACCURATE** | Outdated statistic or partially wrong information |
| ❌ **FALSE** | No evidence supports the claim |

Each verdict includes:
- **Confidence level** (HIGH / MEDIUM / LOW)
- **Explanation** of why the verdict was given
- **Correct fact** (when the claim is inaccurate or false)
- **Source links** to the evidence used

---

## Tech Stack

| Technology | Purpose |
|-----------|---------|
| [Streamlit](https://streamlit.io) | Web interface & deployment |
| [OpenRouter API](https://openrouter.ai/) | Claim extraction & verdict generation (using robust model fallback chains) |
| [Tavily](https://tavily.com) | Real-time web search for evidence |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | PDF text extraction |
| [Pandas](https://pandas.pydata.org) | Data handling & CSV export |

---

## Local Setup

### Prerequisites
- Python 3.9+
- [OpenRouter API key](https://openrouter.ai/) (for free or paid AI models)
- [Tavily API key](https://tavily.com) (free tier: 1000 searches/month)

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/factcheck-agent.git
cd factcheck-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Add your API keys
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your actual keys
```

### Configure API Keys

Create `.streamlit/secrets.toml`:

```toml
OPENROUTER_API_KEY = "sk-or-v1-your-key-here"
TAVILY_API_KEY = "tvly-your-key-here"
```

### Run

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## Output Format

The app generates a detailed report with color-coded verdict cards. You can also download the results as a CSV file with these columns:

| Column | Description |
|--------|------------|
| `claim` | The extracted factual claim |
| `type` | Category (statistic, date, financial, etc.) |
| `verdict` | VERIFIED, INACCURATE, or FALSE |
| `confidence` | HIGH, MEDIUM, or LOW |
| `explanation` | Why this verdict was given |
| `correct_fact` | The real fact (if claim is wrong) |

---

## Project Structure

```
factcheck-agent/
├── app.py                    # Streamlit UI (main entry point)
├── modules/
│   ├── pdf_extractor.py      # PDF text extraction
│   ├── claim_finder.py       # AI-powered claim identification
│   ├── web_verifier.py       # Tavily web search
│   └── verdict_engine.py     # AI-powered verdict generation
├── .streamlit/
│   └── secrets.toml          # API keys (not committed)
├── requirements.txt
├── .gitignore
└── README.md
```

---


