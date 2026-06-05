# kill-prop: Source-Triangulation News Analyzer

kill-prop is a news analysis system designed to identify propaganda, highlight contradictions between different source pools (Western, Russian, Chinese, Neutral), and extract verified facts using a 6-stage pipeline.

## Features

- **Multi-Source Intake**: Ingests articles from Western mainstream, Russian state-aligned, Russian independent, and Chinese state-aligned sources.
- **Auto-Translation**: Automatically translates non-English sources (e.g., TASS, RIA Novosti) into English for cross-source analysis.
- **Claim Extraction**: Uses rule-based (MVP) or LLM-based (Production) extraction of atomic claims.
- **Propaganda Detection**: Flags loaded language, "us-vs-them" framing, and certainty without evidence.
- **Consensus Engine**: Groups claims into events and identifies where sources agree or disagree.
- **Interactive Dashboard**: Visualizes facts, disputes, and source-specific framing.

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Pydantic
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Storage**: In-memory with JSON persistence for MVP

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-repo/kill-prop.git
   cd kill-prop
   ```

2. **Set up the Backend**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up the Frontend**:
   ```bash
   cd ../frontend
   npm install
   ```

### Running the App

1. **Start the Backend**:
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```
   The API will be available at `http://localhost:8000`.
   - API Docs: `http://localhost:8000/docs`
   - Trigger Pipeline: `curl http://localhost:8000/api/pipeline/run`

2. **Start the Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```
   The app will be available at `http://localhost:5173`.

## Architecture

The system follows a 6-stage pipeline:

1. **Source Intake**: Fetch articles from diverse ideological pools.
2. **Article Normalization**: Convert raw data to structured canonical forms.
3. **Event Clustering**: Group related claims into a single "event".
4. **Claim Extraction**: Identify facts, attributions, and framing.
5. **Evidence Scoring**: Rank claims based on source reliability and corroboration.
6. **User Presentation**: Display facts and highlight contradictions.

## Supported Sources

- **Western Mainstream**: Reuters, AP, BBC, NYT, Washington Post.
- **Russian State**: TASS, RIA Novosti, RT.
- **Russian Independent**: Meduza, Novaya Gazeta.
- **Chinese State**: Xinhua, People's Daily, Global Times.
- **Neutral Wire**: Swissinfo, Interfax.

## Development

- **Run Tests**: 
  - Backend: `cd backend && pytest`
  - Frontend: `cd frontend && npm test` (if configured)
- **Adding Sources**: Update `SourcePool` in `backend/models.py` and implement a fetcher in `backend/pipeline/ingestion.py`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
