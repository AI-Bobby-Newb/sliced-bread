"""Technical analysis service for generating trading signals."""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from src.models.core import Signal, SignalType


logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Collection of technical indicators."""
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average."""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average."""
        return data.ewm(span=period).mean()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """MACD (Moving Average Convergence Divergence)."""
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """Bollinger Bands."""
        sma = TechnicalIndicators.sma(data, period)
        std = data.rolling(window=period).std()
        
        return {
            'upper': sma + (std * std_dev),
            'middle': sma,
            'lower': sma - (std * std_dev)
        }
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                   k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Stochastic Oscillator."""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'k': k_percent,
            'd': d_percent
        }


class SignalResult:
    """Result of signal generation."""
    
    def __init__(self):
        self.signals = []
        self.indicators = {}
        self.metadata = {}


class CompositeSignal:
    """Composite signal combining multiple indicators."""
    
    def __init__(self, symbol: str, timestamp: datetime):
        self.symbol = symbol
        self.timestamp = timestamp
        self.signal_type = SignalType.HOLD
        self.strength = 0.0
        self.confidence = 0.0
        self.contributing_signals = []
        self.metadata = {}


class TechnicalAnalysisService:
    """Service for technical analysis and signal generation."""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
    
    def calculate_indicators(self, data: pd.DataFrame, indicators: List[str]) -> pd.DataFrame:
        """
        Calculate technical indicators for the given data.
        
        Args:
            data: OHLC DataFrame
            indicators: List of indicator names to calculate
            
        Returns:
            DataFrame with calculated indicators
        """
        result = data.copy()
        
        try:
            for indicator in indicators:
                if indicator == 'sma_10':
                    result['sma_10'] = self.indicators.sma(data['close'], 10)
                elif indicator == 'sma_20':
                    result['sma_20'] = self.indicators.sma(data['close'], 20)
                elif indicator == 'sma_50':
                    result['sma_50'] = self.indicators.sma(data['close'], 50)
                elif indicator == 'ema_12':
                    result['ema_12'] = self.indicators.ema(data['close'], 12)
                elif indicator == 'ema_26':
                    result['ema_26'] = self.indicators.ema(data['close'], 26)
                elif indicator == 'rsi':
                    result['rsi'] = self.indicators.rsi(data['close'])
                elif indicator == 'macd':
                    macd_data = self.indicators.macd(data['close'])
                    result['macd'] = macd_data['macd']
                    result['macd_signal'] = macd_data['signal']
                    result['macd_histogram'] = macd_data['histogram']
                elif indicator == 'bollinger':
                    bb_data = self.indicators.bollinger_bands(data['close'])
                    result['bb_upper'] = bb_data['upper']
                    result['bb_middle'] = bb_data['middle']
                    result['bb_lower'] = bb_data['lower']
                elif indicator == 'stochastic':
                    stoch_data = self.indicators.stochastic(data['high'], data['low'], data['close'])
                    result['stoch_k'] = stoch_data['k']
                    result['stoch_d'] = stoch_data['d']
                
            logger.info(f"Calculated {len(indicators)} indicators")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            raise
    
    def generate_signals(self, data: pd.DataFrame, strategy_config: Dict) -> SignalResult:
        """
        Generate trading signals based on technical indicators.
        
        Args:
            data: DataFrame with OHLC data and indicators
            strategy_config: Configuration for signal generation
            
        Returns:
            SignalResult with generated signals
        """
        result = SignalResult()
        
        try:
            # Get the latest data point
            if len(data) < 2:
                logger.warning("Insufficient data for signal generation")
                return result
            
            latest = data.iloc[-1]
            previous = data.iloc[-2]
            symbol = latest.get('symbol', 'UNKNOWN')
            timestamp = latest.get('timestamp', datetime.now())
            
            signals = []
            
            # Moving Average Crossover Signals
            if 'sma_10' in data.columns and 'sma_20' in data.columns:
                signal = self._generate_ma_crossover_signal(
                    symbol, timestamp, latest, previous, 'sma_10', 'sma_20'
                )
                if signal:
                    signals.append(signal)
            
            # RSI Signals
            if 'rsi' in data.columns:
                signal = self._generate_rsi_signal(symbol, timestamp, latest)
                if signal:
                    signals.append(signal)
            
            # MACD Signals
            if 'macd' in data.columns and 'macd_signal' in data.columns:
                signal = self._generate_macd_signal(symbol, timestamp, latest, previous)
                if signal:
                    signals.append(signal)
            
            # Bollinger Bands Signals
            if all(col in data.columns for col in ['bb_upper', 'bb_lower', 'close']):
                signal = self._generate_bollinger_signal(symbol, timestamp, latest)
                if signal:
                    signals.append(signal)
            
            result.signals = signals
            result.metadata = {
                'total_signals': len(signals),
                'timestamp': timestamp,
                'symbol': symbol
            }
            
            logger.info(f"Generated {len(signals)} signals for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating signals: {str(e)}")
            raise
    
    def _generate_ma_crossover_signal(self, symbol: str, timestamp: datetime,
                                    latest: pd.Series, previous: pd.Series,
                                    fast_ma: str, slow_ma: str) -> Optional[Signal]:
        """Generate moving average crossover signal."""
        try:
            fast_current = latest[fast_ma]
            fast_previous = previous[fast_ma]
            slow_current = latest[slow_ma]
            slow_previous = previous[slow_ma]
            
            # Check for crossover
            if pd.isna(fast_current) or pd.isna(slow_current):
                return None
            
            # Bullish crossover (fast MA crosses above slow MA)
            if fast_previous <= slow_previous and fast_current > slow_current:
                return Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    signal_type=SignalType.BUY,
                    strength=0.7,
                    confidence=0.8,
                    source='technical_ma_crossover',
                    metadata={
                        'indicator': f'{fast_ma}_cross_{slow_ma}',
                        'fast_ma': fast_current,
                        'slow_ma': slow_current,
                        'crossover_type': 'bullish'
                    }
                )
            
            # Bearish crossover (fast MA crosses below slow MA)
            elif fast_previous >= slow_previous and fast_current < slow_current:
                return Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    signal_type=SignalType.SELL,
                    strength=0.7,
                    confidence=0.8,
                    source='technical_ma_crossover',
                    metadata={
                        'indicator': f'{fast_ma}_cross_{slow_ma}',
                        'fast_ma': fast_current,
                        'slow_ma': slow_current,
                        'crossover_type': 'bearish'
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating MA crossover signal: {str(e)}")
            return None
    
    def _generate_rsi_signal(self, symbol: str, timestamp: datetime, latest: pd.Series) -> Optional[Signal]:
        """Generate RSI-based signal."""
        try:
            rsi = latest['rsi']
            
            if pd.isna(rsi):
                return None
            
            # Oversold condition (RSI < 30)
            if rsi < 30:
                return Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    signal_type=SignalType.BUY,
                    strength=min(1.0, (30 - rsi) / 30),  # Stronger signal when more oversold
                    confidence=0.6,
                    source='technical_rsi',
                    metadata={
                        'indicator': 'rsi',
                        'rsi_value': rsi,
                        'condition': 'oversold'
                    }
                )
            
            # Overbought condition (RSI > 70)
            elif rsi > 70:
                return Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    signal_type=SignalType.SELL,
                    strength=min(1.0, (rsi - 70) / 30),  # Stronger signal when more overbought
                    confidence=0.6,
                    source='technical_rsi',
                    metadata={
                        'indicator': 'rsi',
                        'rsi_value': rsi,
                        'condition': 'overbought'
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating RSI signal: {str(e)}")
            return None
    
    def _generate_macd_signal(self, symbol: str, timestamp: datetime,
                            latest: pd.Series, previous: pd.Series) -> Optional[Signal]:
        """Generate MACD-based signal."""
        try:
            macd_current = latest['macd']
            signal_current = latest['macd_signal']
            macd_previous = previous['macd']
            signal_previous = previous['macd_signal']
            
            if any(pd.isna(val) for val in [macd_current, signal_current, macd_previous, signal_previous]):
                return None
            
            # Bullish crossover (MACD crosses above signal line)
            if macd_previous <= signal_previous and macd_current > signal_current:
                return Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    signal_type=SignalType.BUY,
                    strength=0.6,
                    confidence=0.7,
                    source='technical_macd',
                    metadata={
                        'indicator': 'macd',
                        'macd': macd_current,
                        'signal': signal_current,
                        'crossover_type': 'bullish'
                    }
                )
            
            # Bearish crossover (MACD crosses below signal line)
            elif macd_previous >= signal_previous and macd_current < signal_current:
                return Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    signal_type=SignalType.SELL,
                    strength=0.6,
                    confidence=0.7,
                    source='technical_macd',
                    metadata={
                        'indicator': 'macd',
                        'macd': macd_current,
                        'signal': signal_current,
                        'crossover_type': 'bearish'
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating MACD signal: {str(e)}")
            return None
    
    def _generate_bollinger_signal(self, symbol: str, timestamp: datetime, latest: pd.Series) -> Optional[Signal]:
        """Generate Bollinger Bands signal."""
        try:
            close = latest['close']
            bb_upper = latest['bb_upper']
            bb_lower = latest['bb_lower']
            
            if any(pd.isna(val) for val in [close, bb_upper, bb_lower]):
                return None
            
            # Price touches lower band (oversold)
            if close <= bb_lower:
                return Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    signal_type=SignalType.BUY,
                    strength=0.5,
                    confidence=0.6,
                    source='technical_bollinger',
                    metadata={
                        'indicator': 'bollinger_bands',
                        'close': close,
                        'bb_lower': bb_lower,
                        'condition': 'oversold'
                    }
                )
            
            # Price touches upper band (overbought)
            elif close >= bb_upper:
                return Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    signal_type=SignalType.SELL,
                    strength=0.5,
                    confidence=0.6,
                    source='technical_bollinger',
                    metadata={
                        'indicator': 'bollinger_bands',
                        'close': close,
                        'bb_upper': bb_upper,
                        'condition': 'overbought'
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating Bollinger signal: {str(e)}")
            return None
    
    def combine_signals(self, signals: List[Signal]) -> CompositeSignal:
        """
        Combine multiple signals into a composite signal.
        
        Args:
            signals: List of individual signals
            
        Returns:
            CompositeSignal with weighted combination
        """
        if not signals:
            return CompositeSignal("UNKNOWN", datetime.now())
        
        # Use the first signal's symbol and timestamp
        composite = CompositeSignal(signals[0].symbol, signals[0].timestamp)
        composite.contributing_signals = signals
        
        # Separate buy and sell signals
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        
        # Calculate weighted scores
        buy_score = sum(s.strength * s.confidence for s in buy_signals)
        sell_score = sum(s.strength * s.confidence for s in sell_signals)
        
        # Determine composite signal
        if buy_score > sell_score and buy_score > 0.3:
            composite.signal_type = SignalType.BUY
            composite.strength = min(1.0, buy_score)
            composite.confidence = min(1.0, buy_score / len(buy_signals)) if buy_signals else 0.0
        elif sell_score > buy_score and sell_score > 0.3:
            composite.signal_type = SignalType.SELL
            composite.strength = min(1.0, sell_score)
            composite.confidence = min(1.0, sell_score / len(sell_signals)) if sell_signals else 0.0
        else:
            composite.signal_type = SignalType.HOLD
            composite.strength = 0.0
            composite.confidence = 0.5
        
        composite.metadata = {
            'buy_signals': len(buy_signals),
            'sell_signals': len(sell_signals),
            'buy_score': buy_score,
            'sell_score': sell_score,
            'total_signals': len(signals)
        }
        
        logger.info(f"Combined {len(signals)} signals into {composite.signal_type.value} signal "
                   f"(strength: {composite.strength:.2f}, confidence: {composite.confidence:.2f})")
        
        return composite