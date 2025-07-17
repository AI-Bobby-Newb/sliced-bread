"""Machine learning prediction service for stock returns."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import os

from src.models.core import PredictionResult


logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Feature engineering for ML models."""
    
    @staticmethod
    def create_features(data: pd.DataFrame) -> pd.DataFrame:
        """
        Create features from OHLC data.
        
        Args:
            data: DataFrame with OHLC data
            
        Returns:
            DataFrame with engineered features
        """
        df = data.copy()
        
        # Price-based features
        df['price_change'] = df['close'].pct_change()
        df['high_low_ratio'] = df['high'] / df['low']
        df['open_close_ratio'] = df['open'] / df['close']
        
        # Volume features
        df['volume_change'] = df['volume'].pct_change()
        df['price_volume'] = df['close'] * df['volume']
        
        # Rolling statistics (5-day window)
        df['price_mean_5'] = df['close'].rolling(5).mean()
        df['price_std_5'] = df['close'].rolling(5).std()
        df['volume_mean_5'] = df['volume'].rolling(5).mean()
        
        # Rolling statistics (10-day window)
        df['price_mean_10'] = df['close'].rolling(10).mean()
        df['price_std_10'] = df['close'].rolling(10).std()
        df['volume_mean_10'] = df['volume'].rolling(10).mean()
        
        # Technical indicators (simple versions)
        df['sma_5'] = df['close'].rolling(5).mean()
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        
        # Price relative to moving averages
        df['price_vs_sma_5'] = df['close'] / df['sma_5'] - 1
        df['price_vs_sma_10'] = df['close'] / df['sma_10'] - 1
        df['price_vs_sma_20'] = df['close'] / df['sma_20'] - 1
        
        # Volatility features
        df['volatility_5'] = df['price_change'].rolling(5).std()
        df['volatility_10'] = df['price_change'].rolling(10).std()
        
        # Lag features
        for lag in [1, 2, 3, 5]:
            df[f'price_change_lag_{lag}'] = df['price_change'].shift(lag)
            df[f'volume_change_lag_{lag}'] = df['volume_change'].shift(lag)
        
        return df
    
    @staticmethod
    def create_target(data: pd.DataFrame, horizon: int = 1) -> pd.Series:
        """
        Create target variable (future returns).
        
        Args:
            data: DataFrame with price data
            horizon: Number of days ahead to predict
            
        Returns:
            Series with future returns
        """
        return data['close'].pct_change(horizon).shift(-horizon)


class ModelTrainingResult:
    """Result of model training."""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.train_score = 0.0
        self.test_score = 0.0
        self.cv_scores = []
        self.feature_importance = {}
        self.training_date = datetime.now()


class ModelPerformanceReport:
    """Model performance evaluation report."""
    
    def __init__(self):
        self.r2_score = 0.0
        self.mse = 0.0
        self.rmse = 0.0
        self.mae = 0.0
        self.prediction_accuracy = 0.0
        self.last_updated = datetime.now()


class MLPredictionService:
    """Machine learning prediction service."""
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.feature_engineer = FeatureEngineer()
        
        # Create model directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
    
    def train_model(self, data: pd.DataFrame, symbol: str = "default") -> ModelTrainingResult:
        """
        Train ML model for return prediction.
        
        Args:
            data: DataFrame with OHLC data
            symbol: Stock symbol for model naming
            
        Returns:
            ModelTrainingResult with training metrics
        """
        try:
            logger.info(f"Training ML model for {symbol}")
            
            # Feature engineering
            df_features = self.feature_engineer.create_features(data)
            target = self.feature_engineer.create_target(df_features)
            
            # Select feature columns (exclude OHLC and metadata)
            feature_cols = [col for col in df_features.columns 
                          if col not in ['open', 'high', 'low', 'close', 'volume', 'symbol', 'timestamp']]
            
            # Prepare data
            X = df_features[feature_cols].copy()
            y = target.copy()
            
            # Remove rows with NaN values
            mask = ~(X.isnull().any(axis=1) | y.isnull())
            X = X[mask]
            y = y[mask]
            
            if len(X) < 50:
                raise ValueError(f"Insufficient data for training: {len(X)} samples")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, shuffle=False
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
            
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            train_score = model.score(X_train_scaled, y_train)
            test_score = model.score(X_test_scaled, y_test)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
            
            # Feature importance
            feature_importance = dict(zip(feature_cols, model.feature_importances_))
            feature_importance = dict(sorted(feature_importance.items(), 
                                           key=lambda x: x[1], reverse=True))
            
            # Store model and scaler
            self.model = model
            self.scaler = scaler
            self.feature_names = feature_cols
            
            # Save model
            model_path = os.path.join(self.model_dir, f"{symbol}_model.joblib")
            scaler_path = os.path.join(self.model_dir, f"{symbol}_scaler.joblib")
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            
            # Create result
            result = ModelTrainingResult()
            result.model = model
            result.scaler = scaler
            result.feature_names = feature_cols
            result.train_score = train_score
            result.test_score = test_score
            result.cv_scores = cv_scores
            result.feature_importance = feature_importance
            
            logger.info(f"Model trained successfully. Train R²: {train_score:.3f}, "
                       f"Test R²: {test_score:.3f}, CV mean: {cv_scores.mean():.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            raise
    
    def predict_returns(self, data: pd.DataFrame, symbol: str = "default") -> PredictionResult:
        """
        Predict future returns using trained model.
        
        Args:
            data: DataFrame with recent OHLC data
            symbol: Stock symbol
            
        Returns:
            PredictionResult with prediction and confidence
        """
        try:
            # Load model if not in memory
            if self.model is None:
                self.load_model(symbol)
            
            if self.model is None:
                raise ValueError(f"No trained model found for {symbol}")
            
            # Feature engineering
            df_features = self.feature_engineer.create_features(data)
            
            # Get latest features
            latest_features = df_features[self.feature_names].iloc[-1:].copy()
            
            # Check for missing values
            if latest_features.isnull().any().any():
                logger.warning("Missing values in features, filling with median")
                latest_features = latest_features.fillna(latest_features.median())
            
            # Scale features
            features_scaled = self.scaler.transform(latest_features)
            
            # Make prediction
            prediction = self.model.predict(features_scaled)[0]
            
            # Calculate confidence interval (simplified)
            # Use model's prediction variance from training
            if hasattr(self.model, 'estimators_'):
                # For RandomForest, get prediction from all trees
                tree_predictions = [tree.predict(features_scaled)[0] 
                                  for tree in self.model.estimators_]
                prediction_std = np.std(tree_predictions)
                confidence_lower = prediction - 1.96 * prediction_std
                confidence_upper = prediction + 1.96 * prediction_std
            else:
                # Fallback confidence interval
                confidence_lower = prediction - 0.02  # ±2%
                confidence_upper = prediction + 0.02
            
            # Feature importance for this prediction
            feature_importance = dict(zip(self.feature_names, 
                                        latest_features.iloc[0].values * self.model.feature_importances_))
            
            result = PredictionResult(
                symbol=symbol,
                timestamp=datetime.now(),
                predicted_return=prediction,
                confidence_interval=(confidence_lower, confidence_upper),
                feature_importance=feature_importance,
                model_version="RandomForest_v1.0"
            )
            
            logger.info(f"Predicted return for {symbol}: {prediction:.3f} "
                       f"({confidence_lower:.3f}, {confidence_upper:.3f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error making prediction: {str(e)}")
            raise
    
    def load_model(self, symbol: str = "default"):
        """Load trained model from disk."""
        try:
            model_path = os.path.join(self.model_dir, f"{symbol}_model.joblib")
            scaler_path = os.path.join(self.model_dir, f"{symbol}_scaler.joblib")
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                logger.info(f"Loaded model for {symbol}")
            else:
                logger.warning(f"No saved model found for {symbol}")
                
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
    
    def evaluate_model_performance(self, data: pd.DataFrame, symbol: str = "default") -> ModelPerformanceReport:
        """
        Evaluate model performance on recent data.
        
        Args:
            data: DataFrame with OHLC data
            symbol: Stock symbol
            
        Returns:
            ModelPerformanceReport with performance metrics
        """
        try:
            if self.model is None:
                self.load_model(symbol)
            
            if self.model is None:
                raise ValueError(f"No trained model found for {symbol}")
            
            # Feature engineering
            df_features = self.feature_engineer.create_features(data)
            target = self.feature_engineer.create_target(df_features)
            
            # Prepare data
            X = df_features[self.feature_names].copy()
            y = target.copy()
            
            # Remove rows with NaN values
            mask = ~(X.isnull().any(axis=1) | y.isnull())
            X = X[mask]
            y = y[mask]
            
            if len(X) < 10:
                raise ValueError("Insufficient data for evaluation")
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Make predictions
            y_pred = self.model.predict(X_scaled)
            
            # Calculate metrics
            r2 = r2_score(y, y_pred)
            mse = mean_squared_error(y, y_pred)
            rmse = np.sqrt(mse)
            mae = np.mean(np.abs(y - y_pred))
            
            # Prediction accuracy (percentage of correct direction predictions)
            direction_actual = np.sign(y)
            direction_pred = np.sign(y_pred)
            accuracy = np.mean(direction_actual == direction_pred)
            
            report = ModelPerformanceReport()
            report.r2_score = r2
            report.mse = mse
            report.rmse = rmse
            report.mae = mae
            report.prediction_accuracy = accuracy
            
            logger.info(f"Model performance - R²: {r2:.3f}, RMSE: {rmse:.3f}, "
                       f"Direction Accuracy: {accuracy:.3f}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error evaluating model: {str(e)}")
            raise