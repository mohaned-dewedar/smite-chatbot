# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a SMITE 2 chatbot project that combines web scraping, LLM integration, and vector search to provide intelligent answers about SMITE 2 game data. The system scrapes the SMITE 2 wiki, processes the data through LLMs for enhanced extraction, and provides a conversational interface.

## Architecture

### Core Components

The project follows standard Python package structure under `src/smite_chatbot/`:

- **Scraper System (`src/smite_chatbot/scraper/`)**: Modular scrapers for different content types
  - `base.py`: Base scraper class with HTTP handling, rate limiting, and JSON utilities
  - `orchestrator.py`: Main entry point that coordinates all scrapers
  - `gods_detailed.py`: Scrapes god pages with abilities, stats, and infobox data
  - `items.py`: Scrapes item pages with stats and descriptions
  - `patch_detail.py`: Scrapes patch notes with structured balance changes
  - `patch_index.py`: Scrapes patch listing pages
  - `patch_notes.py`: Alternative patch scraper
  - `gods.py`: Basic god listing scraper
  - `ability_scraper.py`: Focused ability extraction

- **LLM Integration (`src/smite_chatbot/models/`)**: LLM wrapper for enhanced data processing
  - Uses Ollama for local model inference
  - Enhances scraped data quality through LLM processing

- **Vector Store (`src/smite_chatbot/vectorstore/`)**: ChromaDB-based vector search
  - Enables semantic search over game content
  - Supports embeddings-based retrieval

- **Embeddings (`src/smite_chatbot/embeddings/`)**: Text embedding functionality
  - Sentence transformers for text vectorization
  - Integrates with vector store for search

- **Pipeline (`src/smite_chatbot/pipeline/`)**: Data processing pipeline
  - Transforms raw scraped data into structured formats
  - Handles data cleaning and normalization

- **App (`src/smite_chatbot/app/`)**: Streamlit-based chatbot interface
  - `main.py`: Streamlit app entry point
  - `chatbot.py`: Core chatbot logic and conversation handling

### Data Flow

1. **Scraping**: Orchestrator runs specialized scrapers to extract wiki content
2. **Processing**: Raw data is processed through LLM for enhanced extraction
3. **Storage**: Processed data is stored in timestamped JSON files under `data/`
4. **Indexing**: Content is embedded and stored in vector database
5. **Querying**: Chatbot uses vector search + LLM for intelligent responses

## Development Commands

### Prerequisites
This project uses `uv` for dependency management. Install uv first:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Environment Setup
```bash
# Install dependencies and create virtual environment
uv sync

# Install development dependencies
uv sync --group dev
```

### Running the Scraper
```bash
# Run complete scraping pipeline using the script
uv run smite-scraper

# Run with custom output directory
uv run smite-scraper --out custom_folder

# Limit patch notes scraping
uv run smite-scraper --limit-patch-notes 5

# Alternative: Run as module
uv run python -m smite_chatbot.scraper.orchestrator
```

### Individual Scrapers
```bash
# Run specific scrapers as modules
uv run python -m smite_chatbot.scraper.gods_detailed
uv run python -m smite_chatbot.scraper.items
uv run python -m smite_chatbot.scraper.ability_scraper
uv run python -m smite_chatbot.scraper.gods
```

### Running the App
```bash
# Run the Streamlit app (once implemented)
uv run smite-app
```

### Data Organization
- Scraped data stored in `data/scrape-YYYYMMDD_HHMMSSZ/` directories
- Each scrape session creates timestamped folder with manifest.json
- Raw data preserved alongside processed versions

### Development Patterns
- All scrapers inherit from `BaseScraper` for consistent HTTP handling
- Rate limiting (0.7s default delay) and retry logic built into base class
- JSON output includes metadata and timestamps for traceability
- Modular design allows independent scraper development and testing

### Key Files for Understanding
- `src/smite_chatbot/scraper/base.py:23`: BaseScraper class with core scraping utilities
- `src/smite_chatbot/scraper/orchestrator.py:14`: Main scraping coordination function
- `src/smite_chatbot/scraper/gods_detailed.py:103`: Example of complex page parsing
- `data/*/manifest.json`: Index of scraped data for each session
- `pyproject.toml`: Project configuration with dependencies and scripts

### Testing and Validation
- No formal test framework currently in place
- Scrapers include basic error handling and continue-on-failure logic
- Output validation through JSON structure and metadata inclusion