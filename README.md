# Sliced Bread

A comprehensive AI-powered stock analysis and trading system designed to provide intelligent investment insights through advanced data analysis, machine learning, and automated trading capabilities. The best thing since... well, sliced bread!

## Features

- **Data Pipeline**: Reliable market data ingestion from multiple providers
- **Backtesting Engine**: Strategy evaluation using Backtrader framework
- **Technical Analysis**: Standard indicators with signal generation
- **Machine Learning**: XGBoost-based return predictions
- **Sentiment Analysis**: News sentiment integration
- **Portfolio Management**: Risk-aware position sizing and optimization
- **Paper Trading**: Live strategy validation without financial risk

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd sliced-bread
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Initialize Database**
   ```bash
   python -m src.utils.database
   ```

4. **Run Tests**
   ```bash
   pytest tests/
   ```

## Project Structure

```
src/
├── api/           # FastAPI endpoints
├── models/        # Data models and database schemas
├── services/      # Core business logic
└── utils/         # Utilities and helpers

tests/             # Test suite
.kiro/specs/       # Project specifications
```

## Development Status

This project is under active development following a phased approach:

- ✅ Phase 1: Project Foundation and Data Pipeline
- 🔄 Phase 2: Technical Analysis and Signal Generation
- ⏳ Phase 3: Machine Learning Integration
- ⏳ Phase 4: Portfolio Management and Risk Control

## License

MIT License - see LICENSE file for details.