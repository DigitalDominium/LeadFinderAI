# JARVIS — AI Lead Finder (Web App)

Voice-enabled AI lead finder for contract logistics sales. Built with FastAPI + OpenAI + Google Maps.

## Project Structure

```
ai-lead-finder-web/
├── main.py                  # FastAPI backend
├── services/
│   ├── google_maps.py       # Google Places API
│   ├── ai_analyzer.py       # OpenAI lead scoring
│   ├── voice.py             # Whisper + TTS + command interpreter
│   └── exporter.py          # Excel export
├── static/
│   └── index.html           # Jarvis UI (voice + leads + drawer)
├── requirements.txt
├── render.yaml              # Render deploy config
├── .env.example
└── .gitignore
```

## Local Development

### 1. Clone and set up

```bash
git clone https://github.com/YOUR_USERNAME/ai-lead-finder-web
cd ai-lead-finder-web
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up environment

```bash
cp .env.example .env
# Edit .env and add your keys
```

### 3. Run locally

```bash
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000

---

## Deploy to Render

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/ai-lead-finder-web.git
git push -u origin main
```

### 2. Create Render Web Service

1. Go to https://render.com → New → Web Service
2. Connect your GitHub repo
3. Render auto-detects `render.yaml` — confirm settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. Add environment variables in Render dashboard

Go to your service → Environment → Add:

| Key | Value |
|-----|-------|
| `GOOGLE_MAPS_API_KEY` | your Google Maps key |
| `OPENAI_API_KEY` | your OpenAI key |
| `OPENAI_MODEL` | `gpt-4.1-mini` |

**Never put API keys in GitHub.**

### 4. Deploy

Render deploys automatically on every push to `main`.

---

## How to use

### Voice commands (click the orb):
- *"Find me 10 manufacturing companies in Johor Bahru"*
- *"Analyze the leads"*
- *"Export to Excel"*
- *"Clear the results"*

### Manual controls:
- Fill in the search parameters and click **Find Leads**
- Click **Analyze All Leads** to run AI scoring
- Click **▸ Expand** on any row to open the full detail drawer
- Click **Download Excel** to export

### Lead detail drawer:
- Full AI analysis: score, priority, pain points, suggested service
- Sales opening line and full email draft
- LinkedIn people search and company page buttons
- Google Maps and website links

---

## Google APIs needed

Enable in Google Cloud Console:
- Places API (New)
- Geocoding API

Make sure billing is enabled.

---

## Notes

- Render free tier sleeps after 15 min inactivity (30s cold start). Upgrade to $7/mo for always-on.
- Voice requires microphone permission in browser (Chrome/Edge recommended).
- TTS uses OpenAI `onyx` voice — deep and authoritative.
