# AI Lead Finder — Contract Logistics CRM
### Digital Dominium Enterprise · 2026

A production-grade AI-powered sales prospecting and CRM desktop application
built for contract logistics sales teams in Johor Bahru and the Singapore corridor.

---

## Features

| Tab | What It Does |
|---|---|
| 🔍 Prospect | Find business leads via Google Maps, score & draft outreach with GPT-4 |
| 📋 Pipeline | Full CRM with stage tracking, contact notes, per-lead editing |
| 📅 Follow-ups | Daily due/overdue follow-up dashboard with quick actions |
| 📊 Analytics | KPI cards, stage/priority breakdown bars, top leads leaderboard |

---

## Setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file
Create a file named `.env` in the same folder as `main.py`:

```env
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

### 3. Run the app
```bash
python main.py
```

---

## Project Structure

```
ai_lead_finder/
├── main.py              # Entry point
├── app.py               # Full UI — all 4 tabs
├── config.py            # Env config, constants
├── database.py          # SQLite persistence layer
├── requirements.txt
├── leads.db             # Auto-created on first run
├── exports/             # Auto-created for Excel exports
└── services/
    ├── google_maps.py   # Google Places API integration
    ├── ai_analyzer.py   # OpenAI GPT analysis engine
    └── exporter.py      # Styled Excel export
```

---

## Google Maps API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable **Places API** and **Geocoding API**
3. Create an API key and add it to `.env`

## OpenAI API Setup
1. Go to [platform.openai.com](https://platform.openai.com)
2. Create an API key and add it to `.env`
3. Default model is `gpt-4.1-mini` (cost-efficient). Change to `gpt-4o` for better analysis.

---

## Tips for Sales Use
- Set **Target Service** specifically: e.g. *"bonded warehouse, VAS, cross-border trucking JB-SG"*
- After finding leads, hit **Analyze All with AI** then **Save All to Pipeline**
- Use the **Follow-ups tab** every morning as your daily sales briefing
- Copy WhatsApp drafts directly — they're under 50 words for mobile-friendly cold outreach
- Export to Excel for management reporting or sharing with the team
