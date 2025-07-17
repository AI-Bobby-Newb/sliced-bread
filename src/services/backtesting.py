"""Backtesting engine using Backtrader framework."""

import backtrader as bt
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import logging
import numpy as np

from src.models.core import BacktestResult, Trade, TradeAction, PerformanceMetrics


logger = logging.getLogger(__name__)


class BacktestConfig:
    """Configuration for backtesting runs."""
    
    def __init__(self):
        self.initial_cash = 100000.0
        self.commission = 0.001  # 0.1% commission
        self.slippage = 0.0005   # 0.05% slippage
        self.position_size = 0.95  # Use 95% of available cash


class SimpleMovingAverageCrossover(bt.Strategy):
    """Simple moving average crossover strategy."""
    
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('position_size', 0.95),
    )
    
    def __init__(self):
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_period
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_period
        )
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        
        # Track trades
        self.trades = []
    
    def next(self):
        if not self.position:
            if self.crossover > 0:  # Fast MA crosses above slow MA
                size = int(self.broker.get_cash() * self.params.position_size / self.data.close[0])
                self.buy(size=size)
        else:
            if self.crossover < 0:  # Fast MA crosses below slow MA
                self.sell(size=self.position.size)
    
    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades.append({
                'symbol': self.data._name,
                'timestamp': self.data.datetime.datetime(0),
                'action': 'sell' if trade.size < 0 else 'buy',
                'quantity': abs(trade.size),
                'price': trade.price,
                'commission': trade.commission,
                'pnl': trade.pnl
            })


class BacktestEngine:
    """Backtesting engine for strategy evaluation."""
    
    def __init__(self):
        self.config = BacktestConfig()
    
    def run_backtest(self, strategy_class, data: pd.DataFrame, 
                    config: Optional[BacktestConfig] = None) -> BacktestResult:
        """
        Run backtest for a strategy.
        
        Args:
            strategy_class: Backtrader strategy class
            data: OHLC data for backtesting
            config: Backtesting configuration
            
        Returns:
            BacktestResult with performance metrics
        """
        if config is None:
            config = self.config
        
        try:
            logger.info(f"Starting backtest for {strategy_class.__name__}")
            
            # Create Cerebro engine
            cerebro = bt.Cerebro()
            
            # Add strategy
            cerebro.addstrategy(strategy_class)
            
            # Prepare data
            bt_data = self._prepare_data(data)
            cerebro.adddata(bt_data)
            
            # Set initial cash and commission
            cerebro.broker.setcash(config.initial_cash)
            cerebro.broker.setcommission(commission=config.commission)
            
            # Add analyzers
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            
            # Run backtest
            results = cerebro.run()
            strategy_instance = results[0]
            
            # Extract results
            final_value = cerebro.broker.getvalue()
            
            # Get analyzer results
            sharpe_ratio = strategy_instance.analyzers.sharpe.get_analysis().get('sharperatio', 0)
            drawdown = strategy_instance.analyzers.drawdown.get_analysis()
            returns_analyzer = strategy_instance.analyzers.returns.get_analysis()
            
            # Calculate performance metrics
            total_return = (final_value - config.initial_cash) / config.initial_cash
            max_drawdown = drawdown.get('max', {}).get('drawdown', 0) / 100.0
            
            # Convert trades
            trades = []
            if hasattr(strategy_instance, 'trades'):
                for trade_data in strategy_instance.trades:
                    trade = Trade(
                        symbol=trade_data['symbol'],
                        timestamp=trade_data['timestamp'],
                        action=TradeAction(trade_data['action']),
                        quantity=trade_data['quantity'],
                        price=trade_data['price'],
                        commission=trade_data['commission'],
                        strategy_id=strategy_class.__name__
                    )
                    trades.append(trade)
            
            # Create daily returns series
            daily_returns = pd.Series(
                returns_analyzer.get('rtot', []),
                name='daily_returns'
            )
            
            result = BacktestResult(
                strategy_id=strategy_class.__name__,
                start_date=data.index[0].date() if not data.empty else date.today(),
                end_date=data.index[-1].date() if not data.empty else date.today(),
                initial_capital=config.initial_cash,
                final_value=final_value,
                total_return=total_return,
                sharpe_ratio=sharpe_ratio or 0.0,
                max_drawdown=max_drawdown,
                trades=trades,
                daily_returns=daily_returns
            )
            
            logger.info(f"Backtest completed. Total return: {total_return:.2%}, "
                       f"Sharpe ratio: {sharpe_ratio:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Backtest failed: {str(e)}")
            raise
    
    def _prepare_data(self, data: pd.DataFrame) -> bt.feeds.PandasData:
        """
        Prepare pandas DataFrame for Backtrader.
        
        Args:
            data: OHLC DataFrame
            
        Returns:
            Backtrader data feed
        """
        # Ensure required columns exist
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Ensure datetime index
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'timestamp' in data.columns:
                data = data.set_index('timestamp')
            else:
                raise ValueError("Data must have datetime index or timestamp column")
        
        # Create Backtrader data feed
        bt_data = bt.feeds.PandasData(
            dataname=data,
            datetime=None,  # Use index
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=None
        )
        
        return bt_data
    
    def calculate_metrics(self, trades: List[Trade]) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            trades: List of executed trades
            
        Returns:
            PerformanceMetrics object
        """
        if not trades:
            return PerformanceMetrics(
                total_return=0.0,
                annualized_return=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                calmar_ratio=0.0
            )
        
        # Calculate basic metrics
        pnls = []
        winning_trades = 0
        total_profit = 0.0
        total_loss = 0.0
        
        # Group trades by symbol to calculate P&L
        positions = {}
        
        for trade in trades:
            symbol = trade.symbol
            if symbol not in positions:
                positions[symbol] = {'quantity': 0, 'cost_basis': 0.0}
            
            if trade.action == TradeAction.BUY:
                # Update position
                old_quantity = positions[symbol]['quantity']
                old_cost = positions[symbol]['cost_basis']
                new_quantity = old_quantity + trade.quantity
                
                if new_quantity != 0:
                    positions[symbol]['cost_basis'] = (
                        (old_quantity * old_cost + trade.quantity * trade.price) / new_quantity
                    )
                positions[symbol]['quantity'] = new_quantity
                
            elif trade.action == TradeAction.SELL:
                # Calculate P&L for sold shares
                if positions[symbol]['quantity'] > 0:
                    cost_basis = positions[symbol]['cost_basis']
                    pnl = (trade.price - cost_basis) * trade.quantity - trade.commission
                    pnls.append(pnl)
                    
                    if pnl > 0:
                        winning_trades += 1
                        total_profit += pnl
                    else:
                        total_loss += abs(pnl)
                    
                    # Update position
                    positions[symbol]['quantity'] -= trade.quantity
        
        if not pnls:
            return PerformanceMetrics(
                total_return=0.0,
                annualized_return=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                calmar_ratio=0.0
            )
        
        # Calculate metrics
        total_return = sum(pnls)
        win_rate = winning_trades / len(pnls) if pnls else 0.0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Calculate Sharpe ratio (simplified)
        returns_array = np.array(pnls)
        sharpe_ratio = np.mean(returns_array) / np.std(returns_array) if np.std(returns_array) > 0 else 0.0
        
        # Calculate Sortino ratio (downside deviation)
        negative_returns = returns_array[returns_array < 0]
        downside_std = np.std(negative_returns) if len(negative_returns) > 0 else 0.0
        sortino_ratio = np.mean(returns_array) / downside_std if downside_std > 0 else 0.0
        
        # Calculate max drawdown (simplified)
        cumulative_returns = np.cumsum(returns_array)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0
        
        # Annualized return (assuming daily trades)
        days = (trades[-1].timestamp - trades[0].timestamp).days
        years = days / 365.25 if days > 0 else 1
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
        
        # Calmar ratio
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0.0
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            calmar_ratio=calmar_ratio
        )