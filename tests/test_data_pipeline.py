"""Tests for data pipeline service."""

import pytest
import pandas as pd
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock

from src.services.data_pipeline import DataPipelineService, DataQualityReport
from src.models.core import Quote


class TestDataPipelineService:
    """Test cases for DataPipelineService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = DataPipelineService()
    
    def test_validate_data_quality_empty_data(self):
        """Test data quality validation with empty DataFrame."""
        empty_df = pd.DataFrame()
        report = self.service.validate_data_quality(empty_df)
        
        assert report.quality_score == 0.0
        assert report.missing_data_points == 0
    
    def test_validate_data_quality_perfect_data(self):
        """Test data quality validation with perfect data."""
        data = pd.DataFrame({
            'symbol': ['AAPL'] * 5,
            'timestamp': pd.date_range('2023-01-01', periods=5),
            'open': [150.0, 151.0, 152.0, 153.0, 154.0],
            'high': [155.0, 156.0, 157.0, 158.0, 159.0],
            'low': [149.0, 150.0, 151.0, 152.0, 153.0],
            'close': [154.0, 155.0, 156.0, 157.0, 158.0],
            'volume': [1000000, 1100000, 1200000, 1300000, 1400000]
        })
        
        report = self.service.validate_data_quality(data)
        
        assert report.quality_score == 1.0
        assert report.missing_data_points == 0
        assert report.duplicate_entries == 0
        assert report.price_anomalies == 0
        assert report.volume_anomalies == 0
    
    def test_validate_data_quality_with_issues(self):
        """Test data quality validation with data issues."""
        data = pd.DataFrame({
            'symbol': ['AAPL'] * 5,
            'timestamp': pd.date_range('2023-01-01', periods=5),
            'open': [150.0, None, 152.0, 0.0, 154.0],  # Missing and zero price
            'high': [155.0, 156.0, 157.0, 158.0, 159.0],
            'low': [149.0, 150.0, 151.0, 152.0, 153.0],
            'close': [154.0, 155.0, 156.0, 157.0, 158.0],
            'volume': [1000000, 1100000, -1200000, 1300000, 1400000]  # Negative volume
        })
        
        report = self.service.validate_data_quality(data)
        
        assert report.quality_score < 1.0
        assert report.missing_data_points == 1
        assert report.price_anomalies == 1  # Zero price
        assert report.volume_anomalies == 1  # Negative volume
    
    @patch('yfinance.Ticker')
    def test_get_real_time_quote_success(self, mock_ticker):
        """Test successful real-time quote fetching."""
        # Mock yfinance response
        mock_history = pd.DataFrame({
            'Open': [150.0],
            'High': [155.0],
            'Low': [149.0],
            'Close': [154.0],
            'Volume': [1000000]
        }, index=[datetime.now()])
        
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = mock_history
        mock_ticker_instance.info = {'symbol': 'AAPL'}
        mock_ticker.return_value = mock_ticker_instance
        
        quote = self.service.get_real_time_quote('AAPL')
        
        assert isinstance(quote, Quote)
        assert quote.symbol == 'AAPL'
        assert quote.open == 150.0
        assert quote.high == 155.0
        assert quote.low == 149.0
        assert quote.close == 154.0
        assert quote.volume == 1000000
    
    @patch('yfinance.Ticker')
    def test_get_real_time_quote_no_data(self, mock_ticker):
        """Test real-time quote fetching with no data."""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = pd.DataFrame()
        mock_ticker.return_value = mock_ticker_instance
        
        with pytest.raises(ValueError, match="No recent data available"):
            self.service.get_real_time_quote('INVALID')
    
    def test_cache_functionality(self):
        """Test quote caching functionality."""
        # Create a mock quote
        quote = Quote(
            symbol='AAPL',
            timestamp=datetime.now(),
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=1000000
        )
        
        # Manually add to cache
        cache_key = "quote_AAPL"
        self.service.cache[cache_key] = (quote, datetime.now())
        
        # Verify cache contains the quote
        assert cache_key in self.service.cache
        cached_quote, cached_time = self.service.cache[cache_key]
        assert cached_quote.symbol == 'AAPL'
        assert cached_quote.close == 154.0
    
    @patch('yfinance.Ticker')
    def test_fetch_ohlc_data_success(self, mock_ticker):
        """Test successful OHLC data fetching."""
        # Mock yfinance response
        mock_data = pd.DataFrame({
            'Open': [150.0, 151.0, 152.0],
            'High': [155.0, 156.0, 157.0],
            'Low': [149.0, 150.0, 151.0],
            'Close': [154.0, 155.0, 156.0],
            'Volume': [1000000, 1100000, 1200000]
        }, index=pd.date_range('2023-01-01', periods=3))
        
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = mock_data
        mock_ticker.return_value = mock_ticker_instance
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 3)
        
        result = self.service.fetch_ohlc_data('AAPL', start_date, end_date)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert 'symbol' in result.columns
        assert 'timestamp' in result.columns
        assert all(result['symbol'] == 'AAPL')
        assert 'open' in result.columns
        assert 'high' in result.columns
        assert 'low' in result.columns
        assert 'close' in result.columns
        assert 'volume' in result.columns
    
    @patch('yfinance.Ticker')
    def test_fetch_ohlc_data_no_data(self, mock_ticker):
        """Test OHLC data fetching with no data."""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = pd.DataFrame()
        mock_ticker.return_value = mock_ticker_instance
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 3)
        
        with pytest.raises(ValueError, match="No data available"):
            self.service.fetch_ohlc_data('INVALID', start_date, end_date)