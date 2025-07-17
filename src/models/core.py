"""Core data models for Sliced Bread."""

from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Optional, Any
import pandas as pd


class SignalType(Enum):
    """Trading signal types."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class TradeAction(Enum):
    """Trade action types."""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Quote:
    """Market quote data."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None


@dataclass
class Signal:
    """Trading signal with metadata."""
    symbol: str
    timestamp: datetime
    signal_type: SignalType
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    source: str  # technical, ml, sentiment, composite
    metadata: Dict[str, Any]


@dataclass
class Trade:
    """Executed trade record."""
    symbol: str
    timestamp: datetime
    action: TradeAction
    quantity: int
    price: float
    commission: float
    strategy_id: str


@dataclass
class Position:
    """Portfolio position."""
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float


@dataclass
class Portfolio:
    """Portfolio snapshot."""
    positions: Dict[str, Position]
    cash: float
    total_value: float
    last_updated: datetime


@dataclass
class BacktestResult:
    """Backtesting results."""
    strategy_id: str
    start_date: date
    end_date: date
    initial_capital: float
    final_value: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    trades: List[Trade]
    daily_returns: pd.Series


@dataclass
class PerformanceMetrics:
    """Performance metrics for strategies."""
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    calmar_ratio: float


@dataclass
class NewsArticle:
    """News article data."""
    title: str
    content: str
    source: str
    published_at: datetime
    url: str
    sentiment_score: Optional[float] = None


@dataclass
class SentimentScore:
    """Sentiment analysis result."""
    compound: float
    positive: float
    negative: float
    neutral: float
    confidence: float


@dataclass
class PredictionResult:
    """ML prediction result."""
    symbol: str
    timestamp: datetime
    predicted_return: float
    confidence_interval: tuple[float, float]
    feature_importance: Dict[str, float]
    model_version: str