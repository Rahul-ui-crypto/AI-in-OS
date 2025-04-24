import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.llms import HuggingFaceHub
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGAnalyzer:
    def __init__(self, data_dir: str = "data", db_dir: str = "chroma_db"):
        """
        Initialize the RAG analyzer with data and database directories.
        
        Args:
            data_dir: Directory to store usage data
            db_dir: Directory to store the vector database
        """
        self.data_dir = data_dir
        self.db_dir = db_dir
        self.usage_history = []
        self.vector_store = None
        self.llm = None
        
        # Create directories if they don't exist
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(db_dir, exist_ok=True)
        
        # Initialize components
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize the RAG components (embeddings, vector store, LLM)."""
        try:
            # Initialize embeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            
            # Initialize vector store
            self.vector_store = Chroma(
                persist_directory=self.db_dir,
                embedding_function=self.embeddings
            )
            
            # Initialize LLM
            self.llm = HuggingFaceHub(
                repo_id="google/flan-t5-large",
                model_kwargs={"temperature": 0.7, "max_length": 512}
            )
            
            logger.info("RAG components initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing RAG components: {str(e)}")
            raise
    
    def log_usage(self, app_name: str, duration: float, category: str, 
                 timestamp: datetime = None, metadata: Dict = None):
        """
        Log application usage data.
        
        Args:
            app_name: Name of the application
            duration: Duration of usage in minutes
            category: Category of the application
            timestamp: Timestamp of the usage
            metadata: Additional metadata about the usage
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        if metadata is None:
            metadata = {}
            
        usage_entry = {
            "timestamp": timestamp.isoformat(),
            "app_name": app_name,
            "duration": duration,
            "category": category,
            "metadata": metadata
        }
        
        self.usage_history.append(usage_entry)
        self._save_usage_data()
        
    def _save_usage_data(self):
        """Save usage data to disk."""
        try:
            with open(os.path.join(self.data_dir, "usage_history.json"), "w") as f:
                json.dump(self.usage_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving usage data: {str(e)}")
    
    def load_usage_data(self):
        """Load usage data from disk."""
        try:
            with open(os.path.join(self.data_dir, "usage_history.json"), "r") as f:
                self.usage_history = json.load(f)
        except FileNotFoundError:
            logger.info("No existing usage data found")
        except Exception as e:
            logger.error(f"Error loading usage data: {str(e)}")
    
    def generate_weekly_insights(self) -> str:
        """
        Generate weekly insights using RAG.
        
        Returns:
            str: Generated insights
        """
        try:
            # Prepare data for analysis
            df = pd.DataFrame(self.usage_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter for last week
            last_week = datetime.now() - timedelta(days=7)
            weekly_data = df[df['timestamp'] >= last_week]
            
            if weekly_data.empty:
                return "No usage data available for the past week."
            
            # Generate summary statistics
            total_time = weekly_data['duration'].sum()
            category_time = weekly_data.groupby('category')['duration'].sum()
            top_apps = weekly_data.groupby('app_name')['duration'].sum().nlargest(5)
            
            # Create context for RAG
            context = f"""
            Weekly Usage Summary:
            - Total Usage Time: {total_time:.1f} minutes
            - Category Distribution: {category_time.to_dict()}
            - Top Applications: {top_apps.to_dict()}
            """
            
            # Add context to vector store
            self.vector_store.add_texts([context])
            
            # Create prompt template
            prompt = """
            Based on the following usage data, provide personalized insights and recommendations:
            
            {context}
            
            Please include:
            1. Overall usage patterns and trends
            2. Productivity vs. distraction analysis
            3. Specific recommendations for better time management
            4. Health and wellness suggestions based on usage patterns
            5. Tips for maintaining focus and reducing distractions
            
            Keep the response concise, friendly, and actionable.
            """
            
            # Generate insights using RAG
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vector_store.as_retriever()
            )
            
            response = qa_chain.run(prompt.format(context=context))
            return response
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return "Unable to generate insights at this time."
    
    def get_daily_summary(self) -> str:
        """
        Generate a daily summary of usage patterns.
        
        Returns:
            str: Daily summary
        """
        try:
            df = pd.DataFrame(self.usage_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter for today
            today = datetime.now().date()
            daily_data = df[df['timestamp'].dt.date == today]
            
            if daily_data.empty:
                return "No usage data available for today."
            
            # Generate summary
            total_time = daily_data['duration'].sum()
            category_time = daily_data.groupby('category')['duration'].sum()
            
            summary = f"""
            Daily Usage Summary:
            - Total Usage Time: {total_time:.1f} minutes
            - Category Distribution: {category_time.to_dict()}
            """
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {str(e)}")
            return "Unable to generate daily summary."
    
    def get_productivity_score(self) -> float:
        """
        Calculate a productivity score based on usage patterns.
        
        Returns:
            float: Productivity score (0-100)
        """
        try:
            df = pd.DataFrame(self.usage_history)
            
            # Define productive and distracting categories
            productive_categories = ['Development', 'Office', 'Education']
            distracting_categories = ['Entertainment', 'Social Media', 'Gaming']
            
            # Calculate time spent in each category
            productive_time = df[df['category'].isin(productive_categories)]['duration'].sum()
            distracting_time = df[df['category'].isin(distracting_categories)]['duration'].sum()
            total_time = df['duration'].sum()
            
            if total_time == 0:
                return 0.0
            
            # Calculate productivity score
            productivity_score = (productive_time / total_time) * 100
            return min(100.0, max(0.0, productivity_score))
            
        except Exception as e:
            logger.error(f"Error calculating productivity score: {str(e)}")
            return 0.0
    
    def get_usage_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze usage trends over a specified period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict: Usage trends and statistics
        """
        try:
            df = pd.DataFrame(self.usage_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter for specified period
            start_date = datetime.now() - timedelta(days=days)
            period_data = df[df['timestamp'] >= start_date]
            
            if period_data.empty:
                return {"error": "No data available for the specified period"}
            
            # Calculate trends
            daily_usage = period_data.groupby(period_data['timestamp'].dt.date)['duration'].sum()
            category_trends = period_data.groupby(['category', period_data['timestamp'].dt.date])['duration'].sum()
            
            return {
                "daily_usage": daily_usage.to_dict(),
                "category_trends": category_trends.to_dict(),
                "total_time": period_data['duration'].sum(),
                "average_daily_usage": period_data['duration'].sum() / days
            }
            
        except Exception as e:
            logger.error(f"Error analyzing usage trends: {str(e)}")
            return {"error": str(e)}
    
    def get_personalized_recommendations(self) -> List[str]:
        """
        Generate personalized recommendations based on usage patterns.
        
        Returns:
            List[str]: List of recommendations
        """
        try:
            # Get usage trends
            trends = self.get_usage_trends()
            
            if "error" in trends:
                return ["Unable to generate recommendations at this time."]
            
            # Generate recommendations based on trends
            recommendations = []
            
            # Time management recommendations
            if trends["average_daily_usage"] > 480:  # More than 8 hours
                recommendations.append("Consider taking more frequent breaks to maintain productivity.")
            
            # Category-specific recommendations
            category_trends = trends["category_trends"]
            for category, usage in category_trends.items():
                if category in ['Entertainment', 'Social Media'] and sum(usage.values()) > 120:
                    recommendations.append(f"Try to reduce time spent on {category} to improve productivity.")
                elif category in ['Development', 'Office'] and sum(usage.values()) < 60:
                    recommendations.append(f"Consider allocating more time for {category} activities.")
            
            # Health recommendations
            if trends["average_daily_usage"] > 360:  # More than 6 hours
                recommendations.append("Remember to follow the 20-20-20 rule: Every 20 minutes, look 20 feet away for 20 seconds.")
            
            return recommendations[:5]  # Return top 5 recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return ["Unable to generate recommendations at this time."] 