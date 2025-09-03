# SMITE 2 Chatbot

An intelligent chatbot that provides comprehensive answers about SMITE 2 game content through web scraping, LLM processing, and semantic search.

## 🎮 Overview

This project combines multiple technologies to create a knowledgeable SMITE 2 assistant:

- **Web Scraping**: Automated extraction of game data from the SMITE 2 wiki
- **LLM Integration**: Enhanced data processing using local language models (Ollama)
- **Vector Search**: Semantic search capabilities using ChromaDB and sentence transformers
- **Interactive Interface**: Streamlit-based chat interface and FastAPI backend

## 🚀 Quick Start

### Prerequisites

This project uses `uv` for dependency management. Install it first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd smite-chatbot
```

2. Install dependencies:
```bash
uv sync
```

3. Install development dependencies (optional):
```bash
uv sync --group dev
```

### Usage

#### 1. Scrape Game Data
```bash
# Run complete scraping pipeline
uv run smite-scraper

# Custom output directory
uv run smite-scraper --out custom_folder

# Limit patch notes scraping
uv run smite-scraper --limit-patch-notes 5
```

#### 2. Process Data
```bash
# Process scraped data with LLM enhancement
uv run smite-processor
```

#### 3. Populate Vector Database
```bash
# Index processed data for semantic search
uv run smite-populate
```

#### 4. Run the Chatbot
```bash
# Streamlit web interface
uv run smite-app

# Or FastAPI backend
uv run smite-api
```

## 📁 Project Structure

```
src/smite_chatbot/
├── scraper/          # Web scraping modules
│   ├── base.py           # Base scraper with HTTP handling
│   ├── orchestrator.py   # Main scraping coordinator
│   ├── gods_detailed.py  # God pages scraper
│   ├── items.py          # Items scraper
│   └── ...
├── processors/       # Data processing pipeline
├── storage/          # Vector database and document storage
├── models/           # LLM integration and chatbot logic
├── app/              # Streamlit interface
└── api/              # FastAPI backend
```

## 🛠️ Features

### Data Collection
- **Gods**: Detailed information including abilities, stats, and lore
- **Items**: Complete item database with stats and descriptions
- **Patches**: Historical patch notes with balance changes
- **Abilities**: Comprehensive ability data with scaling information

### Processing Pipeline
- **LLM Enhancement**: Raw scraped data is processed through language models for better structure
- **Data Validation**: Automatic validation and error handling
- **Timestamped Storage**: All data is versioned with timestamps

### Search & Query
- **Semantic Search**: Vector-based similarity search for natural language queries
- **Hybrid Storage**: Combines traditional database with vector embeddings
- **Context-Aware Responses**: Uses retrieved context to generate accurate answers

### Interfaces
- **Web Chat**: Streamlit-based conversational interface
- **API**: RESTful API for programmatic access
- **Modular Design**: Easy to extend with new scrapers or interfaces

## 🔧 Development

### Running Individual Components

```bash
# Individual scrapers
uv run python -m smite_chatbot.scraper.gods_detailed
uv run python -m smite_chatbot.scraper.items
uv run python -m smite_chatbot.scraper.ability_scraper

# Data processing
uv run python -m smite_chatbot.processors.orchestrator

# Vector database operations
uv run python -m smite_chatbot.storage.populate
```

### Code Quality

```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# Run tests
uv run pytest
```

### Key Configuration

- **Rate Limiting**: Default 0.7s delay between requests (configurable in base scraper)
- **Data Storage**: Timestamped directories under `data/scrape-YYYYMMDD_HHMMSSZ/`
- **Vector Database**: ChromaDB with sentence-transformers embeddings
- **LLM Backend**: Ollama for local model inference

## 📊 Data Flow

1. **Scraping**: Extract content from SMITE 2 wiki using specialized scrapers
2. **Processing**: Enhance raw data through LLM processing pipeline
3. **Storage**: Save processed data in JSON format with metadata
4. **Indexing**: Create vector embeddings and populate search database
5. **Querying**: Use semantic search + LLM to answer user questions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test them
4. Run code quality checks: `uv run black src/ && uv run ruff check src/`
5. Submit a pull request

## 📋 Requirements

- Python 3.12+
- UV package manager
- Ollama (for local LLM inference)
- Chrome/Chromium (for Playwright scraping)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- SMITE 2 Wiki contributors for providing comprehensive game data
- The open-source community for the excellent tools and libraries used in this project

---

**Note**: This project is for educational and personal use. Please respect the SMITE 2 wiki's terms of service and rate limits when scraping data.