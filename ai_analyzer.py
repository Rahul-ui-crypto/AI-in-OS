import google.generativeai as genai
from datetime import datetime, timedelta
import pandas as pd
import json
import os
from dotenv import load_dotenv
import streamlit as st
import time
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from utils import categorize_app, APP_CATEGORIES
from pathlib import Path

# Load environment variables at module level with override
env_path = Path('.env')
parent_env_path = Path('..') / '.env'

if env_path.exists():
    load_dotenv(env_path, override=True)
    st.success("✅ Found .env file in current directory")
elif parent_env_path.exists():
    load_dotenv(parent_env_path, override=True)
    st.success("✅ Found .env file in parent directory")
else:
    st.error("❌ No .env file found!")

class AIAnalyzer:
    def __init__(self, history_file="tracking_history.json"):
        self.history_file = history_file
        self.model = None
        self.initialized = False
        self.init_error = None
        
        # Load environment variables
        self.api_key = os.getenv('GOOGLE_API_KEY')
        
        if not self.api_key:
            raise ValueError("Google API Key not found in environment variables!")
        elif len(self.api_key) < 30:  # Basic validation for API key format
            raise ValueError(f"Invalid API key format. Current key: {self.api_key[:5]}...")
        
        try:
            # Configure the Generative AI client
            genai.configure(api_key=self.api_key)
            
            # Test the connection with a simple prompt
            try:
                self.model = genai.GenerativeModel('gemini-1.5-pro')
                test_response = self.model.generate_content("Test connection")
                if test_response and test_response.text:
                    st.success("✅ Successfully connected to Gemini API!")
                else:
                    raise Exception("No response from API test")
            except Exception as model_error:
                raise Exception(f"Failed to initialize Gemini model: {str(model_error)}")
                
            self.initialized = True
            
        except Exception as e:
            self.init_error = str(e)
            st.error(f"""
            ❌ Error initializing AI Analyzer: {str(e)}
            
            Please follow these steps:
            1. Go to https://makersuite.google.com/app/apikey to verify your API key
            2. Make sure the Gemini API is enabled at: https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com
            3. Wait a few minutes after enabling the API
            4. Check that your API key has access to the Gemini API
            5. Update your .env file with the correct API key
            
            Current working directory: {os.getcwd()}
            API key status: {'Found' if self.api_key else 'Not found'}
            """)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _generate_content(self, prompt: str) -> Optional[str]:
        """Generate content using Gemini AI with retry logic"""
        try:
            if not self.initialized or not self.model:
                raise ValueError("AI Analyzer not properly initialized")
                
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            st.warning(f"Error generating content: {str(e)}")
            raise

    def _get_static_analysis(self, df: pd.DataFrame) -> str:
        """Generate static analysis based on usage summary"""
        total_time = df['Time_Minutes'].sum()
        num_apps = len(df)
        categories = df['Category'].unique()
        most_used_app = df.nlargest(1, 'Time_Minutes').iloc[0]
        
        analysis = f"""
        📊 Session Summary Analysis:
        
        Usage Overview:
        - Total screen time: {total_time:.1f} minutes
        - Number of applications used: {num_apps}
        - Categories accessed: {', '.join(categories)}
        
        Key Insights:
        1. Most used application: {most_used_app['Display_Name']} ({most_used_app['Time_Minutes']:.1f} minutes)
        2. Average time per application: {(total_time/num_apps):.1f} minutes
        
        Recommendations:
        1. Consider taking regular breaks every 20-30 minutes
        2. Set specific time limits for frequently used apps
        3. Use built-in screen time management tools
        4. Balance your digital activities across different categories
        5. Monitor and adjust usage patterns based on productivity goals
        
        Health Tips:
        - Remember the 20-20-20 rule: Every 20 minutes, look at something 20 feet away for 20 seconds
        - Maintain good posture while using devices
        - Ensure proper lighting to reduce eye strain
        - Stay hydrated and take regular movement breaks
        """
        return analysis

    def analyze_current_session(self, current_data):
        """Analyze current session using static analysis"""
        try:
            # Prepare current session data
            df = pd.DataFrame(current_data)
            return {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'insights': self._get_static_analysis(df),
                'has_historical_context': False
            }
        except Exception as e:
            print(f"Error in analyze_current_session: {str(e)}")
            return {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'insights': "Unable to analyze session data. Please try again later.",
                'has_historical_context': False
            }

    def get_focused_recommendations(self, category):
        """Get category-specific recommendations using Gemini AI"""
        try:
            prompt = f"""
            Please provide recommendations for optimizing {category} application usage:

            Please provide:
            1. Specific recommendations for optimizing {category} app usage
            2. Best practices for this category
            3. Potential productivity improvements
            4. Health and wellness considerations
            5. Time management strategies

            Focus on practical, actionable advice.
            """

            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            return f"Failed to generate recommendations: {str(e)}"

    def analyze_usage_patterns(self, history: List[Dict[str, Any]]) -> str:
        """Analyze usage patterns with retry logic for connection issues"""
        if not self.initialized:
            return f"AI Analysis unavailable: {self.init_error}"
            
        try:
            if not history:
                return "No usage history available for analysis."
                
            # Format the history data for analysis
            usage_data = "\n".join([
                f"App: {record['app']}, Duration: {record['duration']} minutes, "
                f"Time: {record['timestamp']}, Profile: {record['profile']}"
                for record in history
            ])
            
            prompt = f"""
            Analyze the following screen time usage data and provide insights:
            {usage_data}
            
            Please provide:
            1. Usage patterns and trends
            2. Potential concerns or recommendations
            3. Positive behaviors to encourage
            Keep the response concise and actionable.
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"Error in analyze_usage_patterns: {str(e)}")
            return f"Unable to generate insights: {str(e)}"

    def update_with_session(self, session_data):
        """Update with new session data - simplified version"""
        try:
            df = pd.DataFrame(session_data)
            
            # Add categories if they don't exist
            if 'Category' not in df.columns:
                df['Category'] = df['Application'].apply(categorize_app)
            
            # Log the update for debugging
            print(f"Session data updated: {len(df)} records processed")
            
        except Exception as e:
            print(f"Error updating session data: {str(e)}")
            st.error(f"Failed to update session data: {str(e)}")