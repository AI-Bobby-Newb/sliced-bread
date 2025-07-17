"""SQLAlchemy database models."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class MarketData(Base):
    """Market OHLC data table."""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    adjusted_close = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )


class TradingSignal(Base):
    """Trading signals table."""
    __tablename__ = "trading_signals"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    signal_type = Column(String(10), nullable=False)  # buy, sell, hold
    strength = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    source = Column(String(50), nullable=False)  # technical, ml, sentiment, composite
    signal_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExecutedTrade(Base):
    """Executed trades table."""
    __tablename__ = "executed_trades"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    action = Column(String(10), nullable=False)  # buy, sell
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, nullable=False)
    strategy_id = Column(String(100), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class PortfolioSnapshot(Base):
    """Portfolio snapshots table."""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    cash = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    snapshot_time = Column(DateTime, nullable=False)
    positions = Column(JSON)  # Store positions as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    
    trades = relationship("ExecutedTrade", back_populates="portfolio")


class Strategy(Base):
    """Trading strategies table."""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    parameters = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BacktestRun(Base):
    """Backtesting runs table."""
    __tablename__ = "backtest_runs"
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_value = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    trade_count = Column(Integer)
    win_rate = Column(Float)
    results_data = Column(JSON)  # Store detailed results
    created_at = Column(DateTime, default=datetime.utcnow)
    
    strategy = relationship("Strategy")


class MLPrediction(Base):
    """ML model predictions table."""
    __tablename__ = "ml_predictions"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    predicted_return = Column(Float, nullable=False)
    confidence_lower = Column(Float)
    confidence_upper = Column(Float)
    model_version = Column(String(50), nullable=False)
    feature_importance = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class NewsData(Base):
    """News articles table."""
    __tablename__ = "news_data"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    source = Column(String(100), nullable=False)
    published_at = Column(DateTime, nullable=False, index=True)
    url = Column(String(1000), unique=True)
    symbol = Column(String(10), index=True)
    sentiment_compound = Column(Float)
    sentiment_positive = Column(Float)
    sentiment_negative = Column(Float)
    sentiment_neutral = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


# Add back_populates for ExecutedTrade
ExecutedTrade.portfolio = relationship("PortfolioSnapshot", back_populates="trades")