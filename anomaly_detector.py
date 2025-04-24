import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime, timedelta
import json

class AnomalyDetector:
    def __init__(self, history_file="tracking_history.json"):
        self.history_file = history_file
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.history = self._load_history()
        
    def _load_history(self):
        """Load session history from JSON file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
                    # Convert timestamp strings back to datetime objects
                    for session in history:
                        session['timestamp'] = datetime.strptime(session['timestamp'], '%Y-%m-%d %H:%M:%S')
                    return history
            return []
        except Exception as e:
            print(f"Error loading history: {e}")
            return []
    
    def _save_history(self):
        """Save tracking history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f)
    
    def _extract_features(self, session_data):
        """Extract relevant features from session data"""
        features = []
        
        # Basic usage metrics
        total_time = session_data['Time_Minutes'].sum()
        app_count = len(session_data)
        avg_time_per_app = total_time / app_count if app_count > 0 else 0
        
        # Category distribution
        categories = session_data['Category'].value_counts(normalize=True)
        category_features = [categories.get(cat, 0) for cat in ['Development', 'Office', 'Entertainment', 'Communication', 'Browsers']]
        
        # Time distribution features
        time_std = session_data['Time_Minutes'].std()
        time_max = session_data['Time_Minutes'].max()
        time_min = session_data['Time_Minutes'].min()
        
        # Combine all features
        features = [
            total_time,
            app_count,
            avg_time_per_app,
            time_std,
            time_max,
            time_min
        ] + category_features
        
        return features
    
    def _prepare_training_data(self):
        """Prepare training data from history"""
        if not self.history:
            return None
        
        X = []
        for session in self.history:
            features = self._extract_features(session['data'])
            X.append(features)
        
        return np.array(X)
    
    def train(self):
        """Train the anomaly detection model"""
        X = self._prepare_training_data()
        if X is None or len(X) < 2:
            return False
        
        # Scale the features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train the model
        self.model.fit(X_scaled)
        return True
    
    def detect_anomaly(self, current_session):
        """Detect anomalies in the current session"""
        if not self.history:
            return False, "Insufficient historical data for anomaly detection", 0.0
        
        # Extract features from current session
        current_features = self._extract_features(current_session)
        current_features_scaled = self.scaler.transform([current_features])
        
        # Predict anomaly
        prediction = self.model.predict(current_features_scaled)
        is_anomaly = prediction[0] == -1
        
        # Calculate anomaly score
        anomaly_score = self.model.score_samples(current_features_scaled)[0]
        
        # Generate anomaly description
        description = self._generate_anomaly_description(current_session, current_features)
        
        return is_anomaly, description, anomaly_score
    
    def _generate_anomaly_description(self, current_session, current_features):
        """Generate a human-readable description of the anomaly"""
        descriptions = []
        
        # Compare with historical averages
        historical_data = self._prepare_training_data()
        if historical_data is not None:
            avg_total_time = np.mean(historical_data[:, 0])
            current_total_time = current_features[0]
            
            if current_total_time > avg_total_time * 1.5:
                descriptions.append(f"Unusually long session duration: {current_total_time:.1f} minutes")
            
            avg_app_count = np.mean(historical_data[:, 1])
            current_app_count = current_features[1]
            
            if current_app_count > avg_app_count * 1.5:
                descriptions.append(f"Unusually high number of applications: {current_app_count}")
        
        # Check category distribution
        categories = current_session['Category'].value_counts(normalize=True)
        for cat, percentage in categories.items():
            if percentage > 0.7:  # If one category takes more than 70% of time
                descriptions.append(f"Unusual concentration in {cat} category: {percentage:.1%}")
        
        return " | ".join(descriptions) if descriptions else "Unusual pattern detected"
    
    def update_history(self, session_data, timestamp):
        """Update tracking history with new session data"""
        # Convert timestamp to string format
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        self.history.append({
            'timestamp': timestamp_str,
            'data': session_data.to_dict('records')
        })
        
        # Keep only last 100 sessions
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        self._save_history()
        
        # Retrain model periodically
        if len(self.history) % 10 == 0:  # Retrain every 10 sessions
            self.train() 