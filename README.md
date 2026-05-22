# Dominium LeadRadar V2

AI Sales Intelligence & Prospecting CRM for contract logistics.

## What V2 Adds

- Campaign Builder
- Google Places lead discovery
- SQLite CRM database
- Duplicate checker
- Lead board with stages
- Follow-up tracking
- Sales owner assignment
- AI lead scoring with scoring breakdown
- AI outreach generator
- AI proposal outline generator
- Decision-maker search helper
- Website scan summary
- Excel import
- Management-ready Excel export
- Voice command support
- Render deployment config with environment variables

## Local Setup

```bash
git clone https://github.com/DigitalDominium/LeadFinderAI
cd LeadFinderAI
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Add your API keys into `.env`.

```bash
uvicorn main:app --reload --port 8000
```

Open:

```text
http://localhost:8000
```

## Render Setup

Add these Render environment variables:

```text
GOOGLE_MAPS_API_KEY
OPENAI_API_KEY
OPENAI_MODEL
DATABASE_PATH=/var/data/leadradar.db
```

This V2 includes a persistent disk in `render.yaml` mounted at:

```text
/var/data
```

The SQLite database path is:

```text
/var/data/leadradar.db
```

## Important Security Note

Never commit your real `.env` file.

Only commit:

```text
.env.example
```

## Google APIs Needed

Enable:

- Places API (New)
- Geocoding API

## Main API Routes

```text
GET  /health
POST /api/search
POST /api/analyze
GET  /api/dashboard
GET  /api/campaigns
POST /api/campaigns
GET  /api/leads
GET  /api/leads/{lead_id}
PUT  /api/leads/{lead_id}
POST /api/leads/{lead_id}/analyze
POST /api/leads/{lead_id}/outreach
POST /api/leads/{lead_id}/proposal
POST /api/website-scan
GET  /api/followups
POST /api/export
POST /api/import-excel
POST /api/transcribe
POST /api/tts
POST /api/interpret
```

## Suggested Git Commands

```bash
git add .
git commit -m "Upgrade LeadRadar to V2 sales intelligence CRM"
git push origin main
```
