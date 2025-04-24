import streamlit as st
st.set_page_config(page_title="Smart Screen Time Tracker", page_icon="🖥️", layout="wide")

import json
import os
import sys
from pathlib import Path
import time
import socket
from collections import defaultdict

import psutil
import pandas as pd
import matplotlib.pyplot as plt
from plyer import notification
import win32gui
import win32process
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from dotenv import load_dotenv

from ai_analyzer import AIAnalyzer
from utils import categorize_app, get_category_emoji, APP_CATEGORIES

# Load environment variables
load_dotenv(override=True)

# Constants
PROFILES_FILE = "profiles.json"

# Email configuration
EMAIL_CONFIG = {
    "sender_email": "srahul1925@gmail.com",
    "sender_password": "zyau hfjq bzhv ujmp",  # App Password
    "recipient_email": "srahul1925@gmail.com",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587
}

# Initialize session state for AI Analyzer
if 'ai_analyzer' not in st.session_state:
    try:
        st.session_state.ai_analyzer = AIAnalyzer()
    except Exception as e:
        st.error(f"Error initializing AI Analyzer: {str(e)}")
        st.session_state.ai_analyzer = None

# Initialize other session states if not present
if 'parent_authenticated' not in st.session_state:
    st.session_state.parent_authenticated = False
if 'show_password_dialog' not in st.session_state:
    st.session_state.show_password_dialog = False
if 'password_error' not in st.session_state:
    st.session_state.password_error = False
if 'exceeded_limits' not in st.session_state:
    st.session_state.exceeded_limits = set()
if 'ai_insights' not in st.session_state:
    st.session_state.ai_insights = None
if 'history' not in st.session_state:
    st.session_state.history = []
if 'total_tracked_time' not in st.session_state:
    st.session_state.total_tracked_time = 0
if 'session_count' not in st.session_state:
    st.session_state.session_count = 0

def load_profiles():
    """Load profiles from JSON file"""
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE, 'r') as f:
            return json.load(f)
    return {
        "kids": {
            "name": "Kids Profile",
            "app_limits": {
                "whatsapp.exe": 1,
                "chrome.exe": 1,
                "facebook.exe": 1
            },
            "is_default": True
        },
        "parent": {
            "name": "Parent Profile",
            "app_limits": {},
            "is_default": False
        }
    }

# Constants
NOTIFICATION_THRESHOLD = 60  # seconds
NOTIFICATION_COOLDOWN = 60  # seconds

# Usage thresholds (in minutes)
USAGE_THRESHOLDS = {
    'Light': 30,      # 30 minutes
    'Moderate': 60,   # 1 hour
    'Heavy': 120,     # 2 hours
    'Excessive': 180  # 3 hours
}

# Category-specific thresholds (percentage of total time)
CATEGORY_THRESHOLDS = {
    'Entertainment': {
        'Moderate': 20,
        'Heavy': 40,
        'Excessive': 60
    },
    'Communication': {
        'Moderate': 20,
        'Heavy': 30,
        'Excessive': 50
    },
    'Browsers': {
        'Moderate': 30,
        'Heavy': 50,
        'Excessive': 70
    },
    'Development': {
        'Light': 20,
        'Moderate': 40,
        'Productive': 60
    },
    'Office': {
        'Light': 20,
        'Moderate': 40,
        'Productive': 60
    }
}

IGNORED_APPS = ['svchost.exe', 'System Idle Process', 'explorer.exe', 'Registry', 
                'csrss.exe', 'wininit.exe', 'Conhost.exe', 'RuntimeBroker.exe',
                'SearchHost.exe', 'ShellExperienceHost.exe', 'StartMenuExperienceHost.exe',
                'TextInputHost.exe', 'dllhost.exe', 'sihost.exe', 'fontdrvhost.exe']

# Application display names with emojis
APP_DISPLAY_NAMES = {
    # Browsers
    'chrome.exe': '🌐 Google Chrome',
    'firefox.exe': '🦊 Firefox',
    'msedge.exe': '🌐 Microsoft Edge',
    'opera.exe': '🌐 Opera',
    'brave.exe': '🦁 Brave',
    'safari.exe': '🌐 Safari',
    
    # Development
    'Code.exe': '💻 Visual Studio Code',
    'devenv.exe': '🎯 Visual Studio',
    'pycharm64.exe': '🐍 PyCharm',
    'idea64.exe': '🧠 IntelliJ IDEA',
    'webstorm64.exe': '🌐 WebStorm',
    'android studio.exe': '🤖 Android Studio',
    'eclipse.exe': '☀️ Eclipse',
    'sublime_text.exe': '📝 Sublime Text',
    'atom.exe': '⚛️ Atom',
    'GitHubDesktop.exe': '🐱 GitHub Desktop',
    'SourceTree.exe': '🌳 SourceTree',
    'postman.exe': '📬 Postman',
    'docker desktop.exe': '🐳 Docker Desktop',
    
    # Databases
    'postgres.exe': '🐘 PostgreSQL',
    'pgadmin4.exe': '🐘 pgAdmin',
    'mysql.exe': '🐬 MySQL',
    'mongodb.exe': '🍃 MongoDB',
    'redis-server.exe': '🔴 Redis',
    
    # Communication
    'discord.exe': '💬 Discord',
    'slack.exe': '💼 Slack',
    'teams.exe': '👥 Microsoft Teams',
    'zoom.exe': '🎥 Zoom',
    'skype.exe': '💬 Skype',
    'telegram.exe': '✈️ Telegram',
    'whatsapp.exe': '💬 WhatsApp',
    'signal.exe': '🔒 Signal',
    
    # Office
    'WINWORD.EXE': '📄 Word',
    'EXCEL.EXE': '📊 Excel',
    'POWERPNT.EXE': '📊 PowerPoint',
    'OUTLOOK.EXE': '📧 Outlook',
    'ONENOTE.EXE': '📔 OneNote',
    'MSACCESS.EXE': '🗄️ Access',
    'MSPUB.EXE': '📰 Publisher',
    'AcroRd32.exe': '📄 Adobe Reader',
    'Acrobat.exe': '📄 Adobe Acrobat',
    'wps.exe': '📝 WPS Office',
    'et.exe': '📊 WPS Spreadsheet',
    'wpp.exe': '📊 WPS Presentation',
    
    # Creative
    'photoshop.exe': '🎨 Photoshop',
    'illustrator.exe': '✒️ Illustrator',
    'premiere.exe': '🎬 Premiere Pro',
    'afterfx.exe': '✨ After Effects',
    'lightroom.exe': '📸 Lightroom',
    'figma.exe': '🎨 Figma',
    'sketch.exe': '💎 Sketch',
    'blender.exe': '🎮 Blender',
    'unity.exe': '🎮 Unity',
    'unreal.exe': '🎮 Unreal Engine',
    
    # Entertainment
    'spotify.exe': '🎵 Spotify',
    'netflix.exe': '🎬 Netflix',
    'steam.exe': '🎮 Steam',
    'epicgameslauncher.exe': '🎮 Epic Games',
    'vlc.exe': '🎥 VLC',
    'wmplayer.exe': '🎵 Windows Media Player',
    
    # Utilities
    'notepad.exe': '📝 Notepad',
    'notepad++.exe': '📝 Notepad++',
    'winrar.exe': '📦 WinRAR',
    '7zg.exe': '📦 7-Zip',
    'calc.exe': '🔢 Calculator',
    'mspaint.exe': '🎨 Paint',
    'snippingtool.exe': '✂️ Snipping Tool',
    
    # System
    'taskmgr.exe': '📊 Task Manager',
    'control.exe': '⚙️ Control Panel',
    'cmd.exe': '⌨️ Command Prompt',
    'powershell.exe': '💻 PowerShell',
    'WindowsTerminal.exe': '💻 Windows Terminal'
}

def get_display_name(app_name):
    """Get the friendly display name for an application."""
    if app_name in APP_DISPLAY_NAMES:
        return APP_DISPLAY_NAMES[app_name]
    
    # Make unknown app names more readable
    name = app_name.replace('.exe', '')
    name = ' '.join(word.capitalize() for word in name.split('_'))
    return f"📱 {name}"

def get_category_emoji(category):
    """Get the emoji for a category."""
    return APP_CATEGORIES.get(category, {}).get('emoji', '📱')

last_notification = {}
def send_notification(app_name, usage_time, is_limit_reached=False):
    """Send smart notifications with context-aware messages."""
    current_time = time.time()
    if app_name not in last_notification or \
       (current_time - last_notification.get(app_name, 0)) > NOTIFICATION_COOLDOWN:
        
        if is_limit_reached:
            message = f"⚠️ Time limit reached for {app_name}! Please close the application."
        else:
            message = (f"You've been using {app_name} for {usage_time:.1f} sec.\n"
                      f"Time for a quick break! 🎯")
        
        notification.notify(
            title="⏰ Smart Screen Time Alert",
            message=message,
            timeout=10
        )
        last_notification[app_name] = current_time

def get_active_window_process():
    """Get the process name and title of the currently active window."""
    try:
        # Get the window handle
        window = win32gui.GetForegroundWindow()
        # Get the window title
        window_title = win32gui.GetWindowText(window)
        # Get the process ID
        _, pid = win32process.GetWindowThreadProcessId(window)
        # Get the process
        process = psutil.Process(pid)
        return process.name(), window_title
    except Exception as e:
        st.error(f"Error getting active window: {str(e)}")
        return None, None

def send_email_notification(app_name, usage_time, profile_name):
    """Send email notification when time limit is exceeded."""
    try:
        st.write("Attempting to send email notification...")  # Debug info
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = EMAIL_CONFIG['recipient_email']
        msg['Subject'] = f"⚠️ Time Limit Exceeded - {app_name}"

        # Email body
        body = f"""
        Time Limit Alert!

        App: {app_name}
        Usage Time: {usage_time:.1f} minutes
        Profile: {profile_name}
        Device: {socket.gethostname()}
        Time: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

        This is an automated notification from your Screen Time Tracker.
        """
        msg.attach(MIMEText(body, 'plain'))

        st.write("Connecting to SMTP server...")  # Debug info
        
        # Connect to SMTP server with explicit timeout
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], timeout=30)
        server.set_debuglevel(1)  # Enable SMTP debug
        
        st.write("Starting TLS...")  # Debug info
        server.starttls()
        
        st.write("Logging in to email server...")  # Debug info
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        
        st.write("Sending email...")  # Debug info
        server.send_message(msg)
        server.quit()
        
        st.success(f"✅ Email notification sent successfully to {EMAIL_CONFIG['recipient_email']}")
    except smtplib.SMTPAuthenticationError as e:
        st.error(f"❌ Email Authentication Failed: Please check your email credentials. Error: {str(e)}")
    except smtplib.SMTPException as e:
        st.error(f"❌ SMTP Error: {str(e)}")
    except socket.timeout:
        st.error("❌ Email server connection timed out. Please check your internet connection.")
    except Exception as e:
        st.error(f"❌ Failed to send email: {str(e)}")
        st.error(f"Error type: {type(e).__name__}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")

def track_screen_time(duration=60, profile=None):
    """Track screen time usage with enhanced display names and profile limits."""
    screen_time = defaultdict(int)
    window_titles = defaultdict(set)
    start_time = time.time()
    
    # Create placeholders for status updates
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    
    # Add a stop button
    stop_button = st.button("⏹️ Stop Tracking")
    
    try:
        while (time.time() - start_time < duration) and not stop_button:
            # Rerun every 30 seconds to maintain connection
            if (time.time() - start_time) % 30 == 0:
                st.experimental_rerun()
            
            active_app, window_title = get_active_window_process()
            
            # Update progress
            progress = int(((time.time() - start_time) / duration) * 100)
            progress_bar.progress(min(progress, 100))
            
            if active_app and active_app not in IGNORED_APPS:
                # Handle Windows Store apps (like WhatsApp)
                if active_app == "ApplicationFrameHost.exe" and window_title == "WhatsApp":
                    active_app = "whatsapp.exe"  # Treat it as the regular WhatsApp process
                
                screen_time[active_app] += 1
                if window_title:
                    window_titles[active_app].add(window_title)
                
                # Check app limits if profile is provided
                if profile and active_app in profile["app_limits"]:
                    limit_minutes = profile["app_limits"][active_app]
                    current_minutes = screen_time[active_app] / 60
                    
                    # Check if limit is exceeded and notification hasn't been sent
                    if current_minutes >= limit_minutes and active_app not in st.session_state.exceeded_limits:
                        status_placeholder.warning(f"⚠️ Time limit exceeded for {get_display_name(active_app)}!")
                        send_notification(get_display_name(active_app), current_minutes, is_limit_reached=True)
                        
                        # Send email notification
                        status_placeholder.info(f"📧 Sending email notification for {get_display_name(active_app)}...")
                        send_email_notification(get_display_name(active_app), current_minutes, profile["name"])
                        
                        # Add to exceeded limits
                        st.session_state.exceeded_limits.add(active_app)
                        status_placeholder.success(f"✅ Added {active_app} to exceeded limits. Email notification sent.")
                
                # Update status less frequently to reduce UI updates
                if time.time() % 2 == 0:  # Update every 2 seconds instead of every second
                    status_placeholder.info(f"Currently tracking: {get_display_name(active_app)} - {window_title}")
                
                if screen_time[active_app] >= NOTIFICATION_THRESHOLD:
                    send_notification(get_display_name(active_app), screen_time[active_app])
            
            # Sleep for a shorter duration to be more responsive
            time.sleep(0.5)
    except Exception as e:
        status_placeholder.error(f"Error during tracking: {str(e)}")
    finally:
        # Clear placeholders
        status_placeholder.empty()
        progress_bar.empty()
        
        if not screen_time:
            return pd.DataFrame(columns=["Application", "Time_Seconds", "Display_Name", "Time_Minutes"])
        
        # Create DataFrame with window titles
        df = pd.DataFrame(list(screen_time.items()), columns=["Application", "Time_Seconds"])
        df['Display_Name'] = df['Application'].apply(get_display_name)
        df['Window_Titles'] = df['Application'].apply(lambda x: ', '.join(window_titles[x]))
        df['Time_Minutes'] = df['Time_Seconds'] / 60
        df['Category'] = df['Application'].apply(categorize_app)  # Add category directly
        
        return df.sort_values('Time_Minutes', ascending=False).reset_index(drop=True)

def plot_screen_time(data):
    """Enhanced visualization of screen time usage."""
    plt.style.use('default')  # Using default style instead of seaborn
    
    # Create figure with white background
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), facecolor='white')
    fig.patch.set_facecolor('white')
    
    # Prepare data for plotting
    plot_data = data.head(8)
    categories = plot_data['Application'].apply(categorize_app)
    colors = [APP_CATEGORIES.get(cat, {}).get('color', '#95a5a6') for cat in categories]
    
    # Bar chart with category-based colors
    ax1.set_facecolor('white')
    bars = ax1.bar(plot_data['Display_Name'], plot_data['Time_Minutes'], color=colors)
    ax1.set_xlabel("Applications", fontsize=10)
    ax1.set_ylabel("Time (Minutes)", fontsize=10)
    ax1.set_title("Top Applications Usage", fontsize=12, pad=20)
    ax1.grid(True, linestyle='--', alpha=0.7)
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Category distribution pie chart
    ax2.set_facecolor('white')
    category_data = data.copy()
    category_data['Category'] = category_data['Application'].apply(categorize_app)
    category_usage = category_data.groupby('Category')['Time_Minutes'].sum()
    
    colors = [APP_CATEGORIES.get(cat, {}).get('color', '#95a5a6') for cat in category_usage.index]
    wedges, texts, autotexts = ax2.pie(category_usage, 
                                      labels=category_usage.index,
                                      colors=colors,
                                      autopct='%1.1f%%',
                                      startangle=90)
    ax2.set_title("Time Distribution by Category", fontsize=12, pad=20)
    
    # Enhance text contrast
    plt.setp(autotexts, size=8, weight="bold")
    plt.setp(texts, size=9)
    
    plt.tight_layout()
    return fig

def analyze_usage_patterns(screen_time_data):
    """Analyze usage patterns with more sophisticated insights."""
    usage_data = screen_time_data.copy()
    usage_data['Category'] = usage_data['Application'].apply(categorize_app)
    category_usage = usage_data.groupby('Category')['Time_Minutes'].sum()
    
    insights = []
    total_time = usage_data['Time_Minutes'].sum()
    
    if total_time > 0:
        # Overall usage level
        usage_level = "Light"
        for level, threshold in USAGE_THRESHOLDS.items():
            if total_time >= threshold:
                usage_level = level
        
        if usage_level in ['Heavy', 'Excessive']:
            insights.append({
                'type': 'warning',
                'message': f"⚠️ {usage_level} overall usage detected ({total_time:.1f} minutes). Consider taking a longer break."
            })
        
        # Category-specific analysis
        for category, usage_time in category_usage.items():
            if category in CATEGORY_THRESHOLDS:
                usage_percent = (usage_time / total_time) * 100
                thresholds = CATEGORY_THRESHOLDS[category]
                
                if category in ['Entertainment', 'Communication', 'Browsers']:
                    if usage_percent >= thresholds['Excessive']:
                        insights.append({
                            'type': 'warning',
                            'message': f"⚠️ Excessive {category} usage ({usage_percent:.1f}%). Consider setting strict time limits."
                        })
                    elif usage_percent >= thresholds['Heavy']:
                        insights.append({
                            'type': 'warning',
                            'message': f"⚡ Heavy {category} usage ({usage_percent:.1f}%). Try to balance with other activities."
                        })
                elif category in ['Development', 'Office']:
                    if usage_percent >= thresholds['Productive']:
                        insights.append({
                            'type': 'info',
                            'message': f"💪 High {category} focus ({usage_percent:.1f}%). Remember to take regular breaks."
                        })
        
        # Time management insights
        if total_time > USAGE_THRESHOLDS['Moderate']:
            insights.append({
                'type': 'health',
                'message': "🧘 Extended computer use detected. Practice the 20-20-20 rule: Every 20 minutes, look 20 feet away for 20 seconds."
            })
            
            if total_time > USAGE_THRESHOLDS['Heavy']:
                insights.append({
                    'type': 'health',
                    'message': "💆 Consider taking a 5-minute break to stretch and move around."
                })
    
    return insights, category_usage

def generate_ai_recommendations(usage_data, total_time):
    """Generate personalized AI recommendations based on usage patterns."""
    recommendations = []
    
    # Add category column before grouping
    usage_data_with_category = usage_data.copy()
    usage_data_with_category['Category'] = usage_data_with_category['Application'].apply(categorize_app)
    category_usage = usage_data_with_category.groupby('Category')['Time_Minutes'].sum()
    
    # Work-life balance recommendations
    if 'Productivity' in category_usage:
        prod_time = category_usage['Productivity']
        if prod_time > total_time * 0.7:
            recommendations.append("🎯 Consider implementing regular break intervals using the Pomodoro Technique")
        elif prod_time < total_time * 0.3:
            recommendations.append("💪 Try setting specific focus hours for deep work")
    
    # Digital wellness recommendations
    if 'Entertainment' in category_usage and category_usage['Entertainment'] > total_time * 0.4:
        recommendations.append("⏰ Use app timers to maintain balanced screen time")
        recommendations.append("🌟 Schedule specific entertainment time slots")
    
    # Communication optimization
    if 'Communication' in category_usage and category_usage['Communication'] > total_time * 0.3:
        recommendations.append("📧 Set specific times for checking emails and messages")
        recommendations.append("🎯 Use 'Do Not Disturb' mode during focus periods")
    
    # Browser usage optimization
    if 'Browsers' in category_usage and category_usage['Browsers'] > total_time * 0.5:
        recommendations.append("🌐 Use browser extensions to block distracting websites")
        recommendations.append("📚 Try browser tab management techniques")
    
    # Always include some general recommendations
    default_recommendations = [
        "🧘 Practice mindful computing by closing unnecessary applications",
        "💡 Use the built-in blue light filter during evening hours",
        "🎯 Set specific goals for each work session",
        "⚡ Take regular micro-breaks (2 minutes every 30 minutes)"
    ]
    
    # Combine specific and general recommendations
    recommendations.extend(default_recommendations)
    
    # Return top 5 most relevant recommendations, ensuring we always have recommendations
    return recommendations[:5] if recommendations else default_recommendations[:5]

# Add email testing function
def test_email_connection():
    """Test the email connection and settings."""
    try:
        st.info("Testing email connection...")
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], timeout=30)
        server.set_debuglevel(1)
        st.write("Connected to SMTP server")
        
        server.starttls()
        st.write("TLS started")
        
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        st.write("Login successful")
        
        server.quit()
        st.success("✅ Email connection test successful!")
        return True
    except Exception as e:
        st.error(f"❌ Email connection test failed: {str(e)}")
        return False

def send_test_email():
    """Send a test email immediately to verify the configuration."""
    try:
        st.write("🔄 Creating test email...")
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = EMAIL_CONFIG['recipient_email']
        msg['Subject'] = "Test Email - Screen Time Tracker"

        body = f"""
        This is a test email from your Screen Time Tracker.
        Sent at: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        If you received this email, your email notifications are working correctly.
        """
        msg.attach(MIMEText(body, 'plain'))

        st.write("🔄 Connecting to Gmail SMTP server...")
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], timeout=30)
        server.set_debuglevel(1)  # Enable debug output
        
        st.write("🔄 Starting TLS encryption...")
        server.starttls()
        
        st.write("🔄 Attempting to log in...")
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        
        st.write("🔄 Sending test email...")
        server.send_message(msg)
        server.quit()
        
        st.success("✅ Test email sent! Please check your inbox (and spam folder)")
        return True
    except smtplib.SMTPAuthenticationError as e:
        st.error(f"❌ Authentication Failed: Gmail rejected the login attempt. Error: {str(e)}")
        st.error("Please verify your App Password is correct and 2FA is enabled on your Gmail account.")
        return False
    except Exception as e:
        st.error(f"❌ Failed to send test email: {str(e)}")
        st.error(f"Error type: {type(e).__name__}")
        return False

def main():
    # Add session state for tracking status
    if 'is_tracking' not in st.session_state:
        st.session_state.is_tracking = False
    
    # Load profiles
    profiles = load_profiles()
    
    # Profile selection
    st.sidebar.header("👤 Profile Selection")
    default_profile = next((k for k, v in profiles.items() if v["is_default"]), "kids")
    
    # Profile selection radio
    selected_profile_key = st.sidebar.radio(
        "Choose Profile",
        options=list(profiles.keys()),
        index=list(profiles.keys()).index(default_profile)
    )

    # Handle parent profile authentication
    if selected_profile_key == "parent":
        if not st.session_state.parent_authenticated:
            st.session_state.show_password_dialog = True
            selected_profile_key = default_profile
    
    # Show password dialog
    if st.session_state.show_password_dialog:
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 🔐 Parent Profile Authentication")
            with st.form("parent_auth", clear_on_submit=True):
                password = st.text_input("Enter Parent Password", type="password", key="parent_password")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.form_submit_button("Login", use_container_width=True):
                        if password == "Parent123":
                            st.session_state.parent_authenticated = True
                            st.session_state.show_password_dialog = False
                            st.session_state.password_error = False
                            selected_profile_key = "parent"
                            st.rerun()
                        else:
                            st.session_state.password_error = True
                            selected_profile_key = default_profile
                with col2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state.show_password_dialog = False
                        st.session_state.password_error = False
                        selected_profile_key = default_profile
                        st.rerun()
            
            if st.session_state.password_error:
                st.error("Password incorrect. Using the default profile.")
            st.markdown("---")
    
    selected_profile = profiles[selected_profile_key]
    
    st.title(f"🖥️ Smart Screen Time Tracker - {selected_profile['name']}")
    st.write("Track and analyze your application usage in real-time!")

    # Add logout button for parent profile
    if st.session_state.parent_authenticated:
        if st.sidebar.button("🔒 Logout from Parent Profile", use_container_width=True):
            st.session_state.parent_authenticated = False
            st.session_state.show_password_dialog = False
            selected_profile_key = default_profile
            selected_profile = profiles[selected_profile_key]
            st.rerun()

    # Display active limits for the selected profile
    if selected_profile["app_limits"]:
        st.sidebar.header("⏰ Active Time Limits")
        for app, limit in selected_profile["app_limits"].items():
            st.sidebar.info(f"{get_display_name(app)}: {limit} minutes")

    # Sidebar configuration
    st.sidebar.header("⚙️ Settings")
    
    # Track duration setting
    duration = st.sidebar.slider(
        "Tracking Duration (seconds)",
        min_value=10,
        max_value=3600,
        value=60,
        step=10,
        help="How long to track your application usage"
    )
    
    # Notification settings
    with st.sidebar.expander("🔔 Notification Settings"):
        notification_threshold = st.slider(
            "Notification Threshold (minutes)",
            min_value=1,
            max_value=60,
            value=5,
            help="Get notified when you spend more than this time on an app"
        )
        
        # Add email test section
        st.write("---")
        st.write("📧 Email Notification Test")
        st.info("Click below to send a test email to verify your configuration")
        if st.button("Send Test Email Now", type="primary", use_container_width=True):
            send_test_email()
        
    # Category filters
    with st.sidebar.expander("🏷️ Category Filters"):
        selected_categories = st.multiselect(
            "Show only these categories",
            options=list(APP_CATEGORIES.keys()),
            default=list(APP_CATEGORIES.keys())
        )

    # Modify the tracking button behavior
    if st.button("🎯 Start Smart Tracking", type="primary", disabled=st.session_state.is_tracking):
        st.session_state.is_tracking = True
        st.session_state.session_count += 1
        st.info("Starting to track your application usage... Please continue using your computer normally.")
        
        # Track screen time with profile
        df = track_screen_time(duration, selected_profile)
        st.session_state.is_tracking = False  # Reset tracking status
        
        if not df.empty:
            # Add to history
            st.session_state.history.append({
                'timestamp': pd.Timestamp.now(),
                'data': df,
                'duration': duration
            })
            st.session_state.total_tracked_time += duration

            # Summary statistics
            st.header("📊 Usage Summary")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Apps Tracked", len(df))
            with col2:
                total_time = df['Time_Minutes'].sum()
                st.metric("Session Time (min)", f"{total_time:.1f}")
            with col3:
                if len(df) > 0:
                    most_used = df.iloc[0]['Display_Name']
                    st.metric("Most Used App", most_used)
            with col4:
                st.metric("Total Sessions", st.session_state.session_count)

            # Session History
            if len(st.session_state.history) > 1:
                st.header("📅 Session History")
                history_tab1, history_tab2 = st.tabs(["📈 Trend", "📋 Details"])
                
                with history_tab1:
                    # Create trend chart
                    history_data = pd.concat([h['data'] for h in st.session_state.history])
                    history_data['Session'] = [f"Session {i+1}" for i in range(len(st.session_state.history)) for _ in range(len(st.session_state.history[i]['data']))]
                    
                    fig = plt.figure(figsize=(12, 6))
                    plt.plot(history_data.groupby('Session')['Time_Minutes'].sum())
                    plt.title("Usage Trend Across Sessions")
                    plt.xticks(rotation=45)
                    st.pyplot(fig)
                    
                with history_tab2:
                    for i, session in enumerate(st.session_state.history):
                        with st.expander(f"Session {i+1} - {session['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"):
                            st.dataframe(session['data'][['Display_Name', 'Time_Minutes', 'Window_Titles']])

            # Current Session Analysis
            st.header("📊 Current Session Analysis")
            analysis_tab1, analysis_tab2, analysis_tab3, analysis_tab4 = st.tabs(["📑 Details", "📈 Charts", "🤖 Insights", "🧠 AI Analysis"])
            
            with analysis_tab1:
                # Show all apps by default
                st.subheader("All Tracked Applications")
                st.dataframe(
                    df[['Display_Name', 'Time_Minutes', 'Window_Titles']].rename(columns={
                        'Display_Name': 'Application',
                        'Time_Minutes': 'Time (Minutes)',
                        'Window_Titles': 'Window Titles'
                    })
                )
                
                # Optional category filtering
                if st.checkbox("Filter by Categories"):
                    st.subheader("Filtered by Selected Categories")
                    filtered_df = df[df['Application'].apply(lambda x: categorize_app(x) in selected_categories)]
                    st.dataframe(
                        filtered_df[['Display_Name', 'Time_Minutes', 'Window_Titles']].rename(columns={
                            'Display_Name': 'Application',
                            'Time_Minutes': 'Time (Minutes)',
                            'Window_Titles': 'Window Titles'
                        })
                    )

            with analysis_tab2:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("All Applications Usage")
                    fig = plot_screen_time(df)
                    st.pyplot(fig)
                    
                    if st.checkbox("Show Filtered View"):
                        filtered_df = df[df['Application'].apply(lambda x: categorize_app(x) in selected_categories)]
                        st.subheader("Filtered Applications Usage")
                        fig_filtered = plot_screen_time(filtered_df)
                        st.pyplot(fig_filtered)
                        
                with col2:
                    # Add productivity score
                    productivity_data = df.copy()
                    productivity_data['Category'] = productivity_data['Application'].apply(categorize_app)
                    productive_categories = ['Development', 'Office', 'Databases']
                    productivity_score = (
                        productivity_data[productivity_data['Category'].isin(productive_categories)]['Time_Minutes'].sum() /
                        productivity_data['Time_Minutes'].sum() * 100
                    )
                    st.metric("Productivity Score", f"{productivity_score:.1f}%")

            with analysis_tab3:
                # AI Insights
                insights, category_usage = analyze_usage_patterns(df)  # Using full dataset for insights
                
                for insight in insights:
                    if insight['type'] == 'warning':
                        st.warning(insight['message'])
                    elif insight['type'] == 'info':
                        st.info(insight['message'])
                    elif insight['type'] == 'health':
                        st.success(insight['message'])

                # Recommendations
                st.subheader("💡 Recommendations")
                recommendations = generate_ai_recommendations(df, total_time)  # Using full dataset for recommendations
                for i, rec in enumerate(recommendations, 1):
                    st.write(f"{i}. {rec}")

            with analysis_tab4:
                st.subheader("🧠 AI-Powered Analysis")
                
                # Get static analysis for the current session
                with st.spinner("Analyzing your usage patterns..."):
                    analysis = st.session_state.ai_analyzer.analyze_current_session(df.to_dict('records'))
                    
                if 'error' in analysis:
                    st.error(analysis['error'])
                else:
                    st.write("Analysis timestamp:", analysis['timestamp'])
                    st.markdown(analysis['insights'])
                    
                    # Category-specific recommendations
                    st.subheader("📱 Category-Specific Insights")
                    categories = df['Category'].unique()
                    selected_category = st.selectbox(
                        "Choose a category for detailed recommendations:",
                        categories
                    )
                    
                    if selected_category:
                        with st.spinner(f"Generating recommendations for {selected_category}..."):
                            recommendations = st.session_state.ai_analyzer.get_focused_recommendations(selected_category)
                            st.markdown(recommendations)
                
                # Update vector store with current session
                st.session_state.ai_analyzer.update_with_session(df.to_dict('records'))
        else:
            st.warning("No application usage was detected during the tracking period. Try increasing the duration or ensure you're actively using applications.")

    # Add a note about connection stability
    if st.session_state.is_tracking:
        st.warning("⚠️ Tracking in progress. Please keep this browser tab open. If the connection drops, the data will be saved automatically.")

    # Help section
    with st.sidebar.expander("ℹ️ Help"):
        st.write("""
        **How to use:**
        1. Set your desired tracking duration
        2. Adjust notification settings if needed
        3. Select categories to focus on
        4. Click 'Start Smart Tracking'
        5. Continue using your computer normally
        6. View your usage statistics and insights
        
        **Features:**
        - Real-time tracking of active windows
        - Session history and trends
        - Category-based analysis
        - Productivity scoring
        - AI-powered insights and recommendations
        
        **Note:** The tracker monitors actively focused windows only.
        """)

if __name__ == "__main__":
    main()