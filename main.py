#!/usr/bin/env python3
"""Main CLI interface for Sliced Bread."""

import argparse
import logging
from datetime import date, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.data_pipeline import DataPipelineService
from src.services.backtesting import BacktestEngine, SimpleMovingAverageCrossover
from src.services.technical_analysis import TechnicalAnalysisService
from src.services.ml_prediction import MLPredictionService
from src.utils.database import init_database
from src.models.core import Quote
import pandas as pd


def setup_logging(level=logging.INFO):
    """Setup logging configuration."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('sliced-bread.log')
        ]
    )


def test_data_pipeline(symbol: str = "AAPL"):
    """Test the data pipeline with a sample symbol."""
    print(f"Testing data pipeline with {symbol}...")
    
    service = DataPipelineService()
    
    try:
        # Test real-time quote
        print("Fetching real-time quote...")
        quote = service.get_real_time_quote(symbol)
        print(f"Quote: {quote.symbol} @ ${quote.close:.2f} (Volume: {quote.volume:,})")
        
        # Test historical data
        print("Fetching historical data...")
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        data = service.fetch_ohlc_data(symbol, start_date, end_date)
        print(f"Fetched {len(data)} historical records")
        
        # Test data quality
        print("Validating data quality...")
        quality_report = service.validate_data_quality(data)
        print(f"Data quality score: {quality_report.quality_score:.2f}")
        
        # Store data
        print("Storing data in database...")
        records_stored = service.store_market_data(data)
        print(f"Stored {records_stored} new records")
        
        return True
        
    except Exception as e:
        print(f"Error testing data pipeline: {e}")
        return False


def test_backtesting(symbol: str = "AAPL"):
    """Test the backtesting engine."""
    print(f"Testing backtesting engine with {symbol}...")
    
    try:
        # Get data
        service = DataPipelineService()
        end_date = date.today()
        start_date = end_date - timedelta(days=365)  # 1 year of data
        
        print("Fetching data for backtesting...")
        data = service.fetch_ohlc_data(symbol, start_date, end_date)
        
        # Prepare data for backtesting (set datetime index)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data = data.set_index('timestamp')
        
        # Run backtest
        print("Running backtest...")
        engine = BacktestEngine()
        result = engine.run_backtest(SimpleMovingAverageCrossover, data)
        
        print(f"Backtest Results for {symbol}:")
        print(f"  Initial Capital: ${result.initial_capital:,.2f}")
        print(f"  Final Value: ${result.final_value:,.2f}")
        print(f"  Total Return: {result.total_return:.2%}")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Max Drawdown: {result.max_drawdown:.2%}")
        print(f"  Number of Trades: {len(result.trades)}")
        
        return True
        
    except Exception as e:
        print(f"Error testing backtesting: {e}")
        return False


def test_technical_analysis(symbol: str = "AAPL"):
    """Test the technical analysis service."""
    print(f"Testing technical analysis with {symbol}...")
    
    try:
        # Get data
        service = DataPipelineService()
        ta_service = TechnicalAnalysisService()
        
        end_date = date.today()
        start_date = end_date - timedelta(days=90)  # 3 months of data
        
        print("Fetching data for technical analysis...")
        data = service.fetch_ohlc_data(symbol, start_date, end_date)
        
        # Calculate indicators
        print("Calculating technical indicators...")
        indicators = ['sma_10', 'sma_20', 'rsi', 'macd', 'bollinger']
        data_with_indicators = ta_service.calculate_indicators(data, indicators)
        
        print(f"Calculated indicators: {indicators}")
        
        # Generate signals
        print("Generating trading signals...")
        signal_result = ta_service.generate_signals(data_with_indicators, {})
        
        print(f"Generated {len(signal_result.signals)} signals:")
        for signal in signal_result.signals:
            print(f"  {signal.signal_type.value.upper()}: {signal.source} "
                  f"(strength: {signal.strength:.2f}, confidence: {signal.confidence:.2f})")
        
        # Test composite signal
        if signal_result.signals:
            print("Creating composite signal...")
            composite = ta_service.combine_signals(signal_result.signals)
            print(f"Composite Signal: {composite.signal_type.value.upper()} "
                  f"(strength: {composite.strength:.2f}, confidence: {composite.confidence:.2f})")
        
        # Show latest indicator values
        if len(data_with_indicators) > 0:
            latest = data_with_indicators.iloc[-1]
            print(f"\nLatest Indicator Values for {symbol}:")
            print(f"  Price: ${latest['close']:.2f}")
            if 'sma_10' in latest:
                print(f"  SMA(10): ${latest['sma_10']:.2f}")
            if 'sma_20' in latest:
                print(f"  SMA(20): ${latest['sma_20']:.2f}")
            if 'rsi' in latest:
                print(f"  RSI: {latest['rsi']:.1f}")
            if 'macd' in latest:
                print(f"  MACD: {latest['macd']:.3f}")
        
        return True
        
    except Exception as e:
        print(f"Error testing technical analysis: {e}")
        return False


def test_ml_prediction(symbol: str = "AAPL"):
    """Test the ML prediction service."""
    print(f"Testing ML prediction with {symbol}...")
    
    try:
        # Get data
        service = DataPipelineService()
        ml_service = MLPredictionService()
        
        end_date = date.today()
        start_date = end_date - timedelta(days=365)  # 1 year of data for training
        
        print("Fetching data for ML training...")
        data = service.fetch_ohlc_data(symbol, start_date, end_date)
        
        if len(data) < 100:
            print(f"Warning: Only {len(data)} records available. ML models work better with more data.")
        
        # Train model
        print("Training ML model...")
        training_result = ml_service.train_model(data, symbol)
        
        print(f"Model Training Results:")
        print(f"  Training R²: {training_result.train_score:.3f}")
        print(f"  Test R²: {training_result.test_score:.3f}")
        print(f"  CV Score: {training_result.cv_scores.mean():.3f} ± {training_result.cv_scores.std():.3f}")
        
        # Show top features
        print(f"\nTop 5 Most Important Features:")
        for i, (feature, importance) in enumerate(list(training_result.feature_importance.items())[:5]):
            print(f"  {i+1}. {feature}: {importance:.3f}")
        
        # Make prediction
        print("\nMaking prediction for next day...")
        prediction_result = ml_service.predict_returns(data, symbol)
        
        print(f"ML Prediction for {symbol}:")
        print(f"  Predicted Return: {prediction_result.predicted_return:.3f} ({prediction_result.predicted_return*100:.1f}%)")
        print(f"  Confidence Interval: ({prediction_result.confidence_interval[0]:.3f}, {prediction_result.confidence_interval[1]:.3f})")
        print(f"  Model Version: {prediction_result.model_version}")
        
        # Evaluate model performance
        print("\nEvaluating model performance...")
        performance = ml_service.evaluate_model_performance(data, symbol)
        
        print(f"Model Performance Metrics:")
        print(f"  R² Score: {performance.r2_score:.3f}")
        print(f"  RMSE: {performance.rmse:.4f}")
        print(f"  Direction Accuracy: {performance.prediction_accuracy:.1%}")
        
        return True
        
    except Exception as e:
        print(f"Error testing ML prediction: {e}")
        return False


def test_all_systems(symbol: str = "AAPL"):
    """Test all systems together - the full Sliced Bread experience!"""
    print(f"🍞 SLICED BREAD - FULL SYSTEM TEST with {symbol} 🍞")
    print("=" * 60)
    
    try:
        # Initialize services
        data_service = DataPipelineService()
        ta_service = TechnicalAnalysisService()
        ml_service = MLPredictionService()
        backtest_engine = BacktestEngine()
        
        # Step 1: Data Pipeline
        print("\n📊 STEP 1: DATA PIPELINE")
        print("-" * 30)
        
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        
        print(f"Fetching 1 year of data for {symbol}...")
        data = data_service.fetch_ohlc_data(symbol, start_date, end_date)
        print(f"✅ Fetched {len(data)} records")
        
        quality_report = data_service.validate_data_quality(data)
        print(f"✅ Data quality score: {quality_report.quality_score:.2f}")
        
        # Step 2: Technical Analysis
        print("\n📈 STEP 2: TECHNICAL ANALYSIS")
        print("-" * 30)
        
        indicators = ['sma_10', 'sma_20', 'rsi', 'macd', 'bollinger']
        data_with_indicators = ta_service.calculate_indicators(data, indicators)
        print(f"✅ Calculated {len(indicators)} technical indicators")
        
        signal_result = ta_service.generate_signals(data_with_indicators, {})
        print(f"✅ Generated {len(signal_result.signals)} trading signals")
        
        if signal_result.signals:
            composite = ta_service.combine_signals(signal_result.signals)
            print(f"📊 Current Signal: {composite.signal_type.value.upper()} "
                  f"(strength: {composite.strength:.2f})")
        
        # Step 3: Machine Learning
        print("\n🤖 STEP 3: MACHINE LEARNING")
        print("-" * 30)
        
        print("Training ML model...")
        training_result = ml_service.train_model(data, symbol)
        print(f"✅ Model trained - Direction Accuracy: {training_result.cv_scores.mean():.1%}")
        
        prediction_result = ml_service.predict_returns(data, symbol)
        print(f"🎯 ML Prediction: {prediction_result.predicted_return*100:.1f}% return")
        
        # Step 4: Backtesting
        print("\n⏮️  STEP 4: BACKTESTING")
        print("-" * 30)
        
        backtest_data = data.copy()
        backtest_data['timestamp'] = pd.to_datetime(backtest_data['timestamp'])
        backtest_data = backtest_data.set_index('timestamp')
        
        print("Running backtest...")
        backtest_result = backtest_engine.run_backtest(SimpleMovingAverageCrossover, backtest_data)
        print(f"✅ Backtest complete - Total Return: {backtest_result.total_return:.1%}")
        
        # Step 5: Final Analysis
        print("\n🎯 FINAL ANALYSIS")
        print("-" * 30)
        
        latest = data_with_indicators.iloc[-1]
        current_price = latest['close']
        
        print(f"Symbol: {symbol}")
        print(f"Current Price: ${current_price:.2f}")
        print(f"")
        print(f"📊 Technical Analysis:")
        if 'sma_10' in latest and 'sma_20' in latest:
            trend = "BULLISH" if latest['sma_10'] > latest['sma_20'] else "BEARISH"
            print(f"   Trend: {trend} (SMA10: ${latest['sma_10']:.2f}, SMA20: ${latest['sma_20']:.2f})")
        if 'rsi' in latest:
            rsi_signal = "OVERSOLD" if latest['rsi'] < 30 else "OVERBOUGHT" if latest['rsi'] > 70 else "NEUTRAL"
            print(f"   RSI: {latest['rsi']:.1f} ({rsi_signal})")
        
        print(f"")
        print(f"🤖 ML Prediction:")
        print(f"   Next Day Return: {prediction_result.predicted_return*100:.1f}%")
        print(f"   Confidence: ({prediction_result.confidence_interval[0]*100:.1f}%, {prediction_result.confidence_interval[1]*100:.1f}%)")
        
        print(f"")
        print(f"⏮️  Backtest Performance:")
        print(f"   Total Return: {backtest_result.total_return:.1%}")
        print(f"   Sharpe Ratio: {backtest_result.sharpe_ratio:.2f}")
        print(f"   Max Drawdown: {backtest_result.max_drawdown:.1%}")
        print(f"   Number of Trades: {len(backtest_result.trades)}")
        
        # Overall recommendation
        print(f"")
        print(f"🍞 SLICED BREAD RECOMMENDATION:")
        print("-" * 40)
        
        # Simple scoring system
        score = 0
        reasons = []
        
        # Technical score
        if signal_result.signals:
            if composite.signal_type.value == 'buy':
                score += composite.strength * composite.confidence
                reasons.append(f"Technical signals suggest BUY ({composite.strength:.2f} strength)")
            elif composite.signal_type.value == 'sell':
                score -= composite.strength * composite.confidence
                reasons.append(f"Technical signals suggest SELL ({composite.strength:.2f} strength)")
        
        # ML score
        if prediction_result.predicted_return > 0.01:  # > 1%
            score += 0.3
            reasons.append(f"ML predicts positive return ({prediction_result.predicted_return*100:.1f}%)")
        elif prediction_result.predicted_return < -0.01:  # < -1%
            score -= 0.3
            reasons.append(f"ML predicts negative return ({prediction_result.predicted_return*100:.1f}%)")
        
        # Backtest score
        if backtest_result.total_return > 0.1 and backtest_result.sharpe_ratio > 1:
            score += 0.2
            reasons.append(f"Strong backtest performance ({backtest_result.total_return:.1%} return)")
        
        # Final recommendation
        if score > 0.3:
            recommendation = "🟢 BUY"
        elif score < -0.3:
            recommendation = "🔴 SELL"
        else:
            recommendation = "🟡 HOLD"
        
        print(f"Recommendation: {recommendation} (Score: {score:.2f})")
        print(f"")
        print("Reasoning:")
        for reason in reasons:
            print(f"  • {reason}")
        
        print(f"")
        print("🍞 That's the best thing since sliced bread! 🍞")
        
        return True
        
    except Exception as e:
        print(f"Error in full system test: {e}")
        return False


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Sliced Bread CLI")
    parser.add_argument("--init-db", action="store_true", help="Initialize database")
    parser.add_argument("--test-data", action="store_true", help="Test data pipeline")
    parser.add_argument("--test-backtest", action="store_true", help="Test backtesting")
    parser.add_argument("--test-signals", action="store_true", help="Test technical analysis signals")
    parser.add_argument("--test-ml", action="store_true", help="Test ML prediction model")
    parser.add_argument("--test-all", action="store_true", help="Test all systems together")
    parser.add_argument("--symbol", default="AAPL", help="Stock symbol to test with")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    
    print("Sliced Bread - AI Trading System")
    print("=" * 40)
    
    if args.init_db:
        print("Initializing database...")
        init_database()
        print("Database initialized successfully!")
    
    if args.test_data:
        success = test_data_pipeline(args.symbol)
        if not success:
            sys.exit(1)
    
    if args.test_backtest:
        success = test_backtesting(args.symbol)
        if not success:
            sys.exit(1)
    
    if args.test_signals:
        success = test_technical_analysis(args.symbol)
        if not success:
            sys.exit(1)
    
    if args.test_ml:
        success = test_ml_prediction(args.symbol)
        if not success:
            sys.exit(1)
    
    if args.test_all:
        success = test_all_systems(args.symbol)
        if not success:
            sys.exit(1)
    
    if not any([args.init_db, args.test_data, args.test_backtest, args.test_signals, args.test_ml, args.test_all]):
        parser.print_help()


if __name__ == "__main__":
    main()