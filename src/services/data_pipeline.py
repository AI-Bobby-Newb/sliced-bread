"""Data pipeline service for market data ingestion."""

import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
import logging
from dataclasses import asdict

from src.models.core import Quote
from src.models.database import MarketData
from src.utils.database import db_manager


logger = logging.getLogger(__name__)


class DataQualityReport:
    """Data quality assessment report."""
    
    def __init__(self):
        self.missing_data_points = 0
        self.duplicate_entries = 0
        self.price_anomalies = 0
        self.volume_anomalies = 0
        self.data_gaps = []
        self.quality_score = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "missing_data_points": self.missing_data_points,
            "duplicate_entries": self.duplicate_entries,
            "price_anomalies": self.price_anomalies,
            "volume_anomalies": self.volume_anomalies,
            "data_gaps": self.data_gaps,
            "quality_score": self.quality_score
        }


class RefreshStatus:
    """Data refresh operation status."""
    
    def __init__(self):
        self.successful_symbols = []
        self.failed_symbols = []
        self.total_records_updated = 0
        self.errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "successful_symbols": self.successful_symbols,
            "failed_symbols": self.failed_symbols,
            "total_records_updated": self.total_records_updated,
            "errors": self.errors
        }


class DataPipelineService:
    """Service for managing market data ingestion and storage."""
    
    def __init__(self):
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = timedelta(minutes=15)  # Cache TTL for real-time data
    
    def fetch_ohlc_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Fetch OHLC data for a symbol within date range.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLC data
            
        Raises:
            Exception: If data fetching fails
        """
        try:
            logger.info(f"Fetching OHLC data for {symbol} from {start_date} to {end_date}")
            
            # Use yfinance to fetch data
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty:
                raise ValueError(f"No data available for {symbol} in the specified date range")
            
            # Standardize column names
            data = data.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Add symbol column
            data['symbol'] = symbol
            data['timestamp'] = data.index
            
            # Reset index to make timestamp a regular column
            data = data.reset_index(drop=True)
            
            logger.info(f"Successfully fetched {len(data)} records for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {str(e)}")
            raise
    
    def get_real_time_quote(self, symbol: str) -> Quote:
        """
        Get real-time quote for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quote object with current market data
        """
        cache_key = f"quote_{symbol}"
        now = datetime.now()
        
        # Check cache first
        if cache_key in self.cache:
            cached_quote, cached_time = self.cache[cache_key]
            if now - cached_time < self.cache_ttl:
                logger.debug(f"Returning cached quote for {symbol}")
                return cached_quote
        
        try:
            logger.info(f"Fetching real-time quote for {symbol}")
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            history = ticker.history(period="1d", interval="1m")
            
            if history.empty:
                raise ValueError(f"No recent data available for {symbol}")
            
            # Get the latest data point
            latest = history.iloc[-1]
            
            quote = Quote(
                symbol=symbol,
                timestamp=now,
                open=float(latest['Open']),
                high=float(latest['High']),
                low=float(latest['Low']),
                close=float(latest['Close']),
                volume=int(latest['Volume']),
                adjusted_close=float(latest['Close'])  # For real-time, close = adj_close
            )
            
            # Cache the quote
            self.cache[cache_key] = (quote, now)
            
            logger.info(f"Successfully fetched real-time quote for {symbol}")
            return quote
            
        except Exception as e:
            logger.error(f"Failed to fetch real-time quote for {symbol}: {str(e)}")
            raise
    
    def store_market_data(self, data: pd.DataFrame) -> int:
        """
        Store market data in database.
        
        Args:
            data: DataFrame with market data
            
        Returns:
            Number of records stored
        """
        try:
            records_stored = 0
            
            with db_manager.get_session() as session:
                for _, row in data.iterrows():
                    # Check if record already exists
                    existing = session.query(MarketData).filter(
                        MarketData.symbol == row['symbol'],
                        MarketData.timestamp == row['timestamp']
                    ).first()
                    
                    if not existing:
                        market_data = MarketData(
                            symbol=row['symbol'],
                            timestamp=row['timestamp'],
                            open=row['open'],
                            high=row['high'],
                            low=row['low'],
                            close=row['close'],
                            volume=row['volume'],
                            adjusted_close=row.get('adjusted_close')
                        )
                        session.add(market_data)
                        records_stored += 1
                
                session.commit()
            
            logger.info(f"Stored {records_stored} new market data records")
            return records_stored
            
        except Exception as e:
            logger.error(f"Failed to store market data: {str(e)}")
            raise
    
    def refresh_data(self, symbols: List[str]) -> RefreshStatus:
        """
        Refresh data for multiple symbols.
        
        Args:
            symbols: List of stock symbols to refresh
            
        Returns:
            RefreshStatus with operation results
        """
        status = RefreshStatus()
        end_date = date.today()
        start_date = end_date - timedelta(days=365)  # Get last year of data
        
        for symbol in symbols:
            try:
                # Fetch data
                data = self.fetch_ohlc_data(symbol, start_date, end_date)
                
                # Store data
                records_stored = self.store_market_data(data)
                
                status.successful_symbols.append(symbol)
                status.total_records_updated += records_stored
                
            except Exception as e:
                error_msg = f"Failed to refresh {symbol}: {str(e)}"
                logger.error(error_msg)
                status.failed_symbols.append(symbol)
                status.errors.append(error_msg)
        
        logger.info(f"Data refresh completed. Success: {len(status.successful_symbols)}, "
                   f"Failed: {len(status.failed_symbols)}")
        
        return status
    
    def validate_data_quality(self, data: pd.DataFrame) -> DataQualityReport:
        """
        Validate data quality and generate report.
        
        Args:
            data: DataFrame to validate
            
        Returns:
            DataQualityReport with quality assessment
        """
        report = DataQualityReport()
        
        if data.empty:
            report.quality_score = 0.0
            return report
        
        # Check for missing data
        missing_count = data.isnull().sum().sum()
        report.missing_data_points = missing_count
        
        # Check for duplicates
        duplicate_count = data.duplicated().sum()
        report.duplicate_entries = duplicate_count
        
        # Check for price anomalies (e.g., zero or negative prices)
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in data.columns:
                anomalies = (data[col] <= 0).sum()
                report.price_anomalies += anomalies
        
        # Check for volume anomalies (negative volume)
        if 'volume' in data.columns:
            volume_anomalies = (data['volume'] < 0).sum()
            report.volume_anomalies = volume_anomalies
        
        # Calculate quality score (1.0 = perfect, 0.0 = unusable)
        total_data_points = len(data) * len(data.columns)
        if total_data_points > 0:
            total_issues = (missing_count + duplicate_count + 
                          report.price_anomalies + report.volume_anomalies)
            report.quality_score = max(0.0, 1.0 - (total_issues / total_data_points))
        
        logger.info(f"Data quality score: {report.quality_score:.2f}")
        return report