# AEO Audit Tool

Answer Engine Optimization (AEO) may be the new buzzword in town, but it is where the world is heading. As more and more users are adopting AI Technologies and traditional keyword search is declining down due to AI Overviews and Conversational Bots. Your website which may be optimized for SEO or rankings in search results may not be visible in Answer Engines such as ChatGPT, Perplexity, etc. This is where this tool will help you it will take your Domain URL and crawls your website like and evaluates if your website/brand is AI Visible or not. 

## What It Does
* Accepts a Seed URL and Crawls Up to 20 Pages, Only Static HTML of the Same Domain of the Seed URL
* Per Page Extraction: title tags, meta description, h1-h6 hierarchy, faq listicles, schema.org, structured data, markup, canonical  URL, word count, internal links, body content and other essential data for an AEO Audit
* Runs deterministic AEO Checks on each page with modern day AEO standards
* Produces an overall site score and page scores and helps you understand how visible your website is to AI Chat bots
* Provides you with Top 5 actionable recommendations for you to apply in your website right now to improve your AI Visibility.
* A well structured JSON report is created which is represented on a HTML Website 

## Tech Stack

**Programming Language**: Python

**API Gateway**: FastAPI

**Server**: Uvicorn

**Async HTTP Client**: httpx

**Config Management**: pydantic-settings

**Environment Variable Management**: python-dotenv

**HTML Parsing**: BeautifulSoup4

## Project Structure

```text
aeo-audit-tool/
|- app/
|- |- api/
|- |- |- routes/
|- |- |- |- __init__.py
|- |- |- |- audit.py
|- |- |- __init__.py
|- |- core/
|- |- |- __init__.py
|- |- |- crawler.py
|- |- |- orchestrator.py
|- |- |- parser.py
|- |- |- reporter.py
|- |- |- scorer.py
|- |- models/
|- |- |- __init__.py
|- |- |- schema.py
|- |- __init__.py
|- |- config.py
|- |- logger.py
|- tests/
|- .env.example
|- .gitignore
|- main.py
|- README.md
|- requirements.txt
```

## Setup & Installation
**Clone the Repository**: 
```bash
git clone <repository_url>
cd aeo-audit-tool
```

**Setup Python Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate # Mac/Linux
venv/Scripts/activate # Windows
```

**Install the Packages**
```bash
pip install -r requirements.txt
```

**Setup Environment Variables**

```text
APP_ENV=development
LOG_LEVEL=INFO
CRAWL_LIMIT=20
CRAWL_TIMEOUT=10
USER_AGENT=aeo-audit-bot/1.0
```

## Running the Server
**Spin up the Server**

```bash
uvicorn main:app --reload #Use Reload only in Development
```
## API Endpoints

### Audit Website
Crawls your website and returns a detailed report about your domain.

**Endpoint** 
```http
POST /api/v1/audit
```

**Request Payload**
```json
{
    "url": "https://example.com"
}
```

**Example Request**
```bash
curl -X POST "http://localhost:8000/api/v1/audit" \
-d '{
    "url": "https://example.com"
}'
```

**Success Response**

**200**

```json
{
  "url": "string",
  "pages_crawled": 0,
  "overall_score": 0,
  "findings": [
    "string"
  ],
  "recommendations": [
    "string"
  ],
  "crawl_duration_seconds": 0,
  "created_at": "2026-06-08T04:15:55.262Z"
}
```

### Health Checkpoint
Server Health Check

**Endpoint** 
```http
GET /health
```

**Example Request**
```bash
curl -X GET "http://localhost:8000/health" 
```

**Success Response**

**200**

```json
{
    "status":"ok",
    "env":"development"
}
```
