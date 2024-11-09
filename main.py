import psutil
import time
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from plyer import notification
from collections import defaultdict


# Constants
NOTIFICATION_THRESHOLD = 30  # seconds
NOTIFICATION_COOLDOWN = 10  # seconds
IGNORED_APPS = ['svchost.exe', 'System Idle Process', 'explorer.exe', 'Registry', 
                'csrss.exe', 'wininit.exe', 'Conhost.exe', 'RuntimeBroker.exe']

# Application display names with emojis
APP_DISPLAY_NAMES = {
    'chrome.exe': '🌐 Google Chrome',
    'firefox.exe': '🦊 Firefox',
    'msedge.exe': '🌐 Microsoft Edge',
    'spotify.exe': '🎵 Spotify',
    'Code.exe': '💻 Visual Studio Code',
    'postgres.exe': '🐘 Postgres',
    'discord.exe': '💬 Discord',
    'slack.exe': '💼 Slack',
    'teams.exe': '👥 Microsoft Teams',
    'code.exe': '💻 VS Code',
    'notepad.exe': '📝 Notepad',
    'excel.exe': '📊 Excel',
    'word.exe': '📄 Word',
    'powerpoint.exe': '📺 PowerPoint',
    'outlook.exe': '📧 Outlook',
    'steam.exe': '🎮 Steam',
    'vlc.exe': '🎥 VLC Media Player',
    'photoshop.exe': '🎨 Photoshop',
    'illustrator.exe': '✒️ Illustrator',
    'zoom.exe': '🎥 Zoom',
    'skype.exe': '💬 Skype',
    'obs64.exe': '🎥 OBS Studio',
    'winrar.exe': '📦 WinRAR',
    '7zg.exe': '📦 7-Zip',
    'telegram.exe': '✈️ Telegram',
    'whatsapp.exe': '💬 WhatsApp',
    'netflix.exe': '🎬 Netflix',
    'conhost.exe':'✨ miscellanies ',
    'GitHubDesktop.exe' : '🐈‍⬛ Github'
}

# Enhanced application categories with more detailed classification
APP_CATEGORIES = {
    'Productivity': {
        'apps': ['excel.exe', 'word.exe', 'powerpoint.exe', 'code.exe', 'notepad.exe'],
        'emoji': '💼',
        'color': '#2ecc71'
    },
    'Communication': {
        'apps': ['teams.exe', 'slack.exe', 'outlook.exe', 'discord.exe', 'skype.exe', 'telegram.exe', 'whatsapp.exe'],
        'emoji': '💬',
        'color': '#3498db'
    },
    'Browsers': {
        'apps': ['chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'safari.exe'],
        'emoji': '🌐',
        'color': '#9b59b6'
    },
    'Entertainment': {
        'apps': ['spotify.exe', 'netflix.exe', 'steam.exe', 'vlc.exe'],
        'emoji': '🎮',
        'color': '#e74c3c'
    },
    'Creative': {
        'apps': ['photoshop.exe', 'illustrator.exe', 'obs64.exe'],
        'emoji': '🎨',
        'color': '#f1c40f'
    }
}

def get_display_name(app_name):
    """Get the friendly display name for an application."""
    return APP_DISPLAY_NAMES.get(app_name, app_name)

def categorize_app(app_name):
    """Categorize an application based on its name with enhanced matching."""
    app_lower = app_name.lower()
    for category, info in APP_CATEGORIES.items():
        if any(app.lower() in app_lower for app in info['apps']):
            return category
    return 'Other'

def get_category_emoji(category):
    """Get the emoji for a category."""
    return APP_CATEGORIES.get(category, {}).get('emoji', '📱')
last_notification = {}
def send_notification(app_name, usage_time):
    """Send smart notifications with context-aware messages."""
    current_time = time.time()
    if app_name not in last_notification or \
       (current_time - last_notification.get(app_name, 0)) > NOTIFICATION_COOLDOWN:
        
        message = (f"You've been using {app_name} for {usage_time:.1f} sec.\n"
                  f"Time for a quick break! 🎯")
        
        notification.notify(
            title="⏰ Smart Screen Time Alert",
            message=message,
            timeout=10
        )
        last_notification[app_name] = current_time
def track_screen_time(duration=60):
    """Track screen time usage with enhanced display names."""
    screen_time = defaultdict(int)
    start_time = time.time()
    
    while time.time() - start_time < duration:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info['name']
                if name in APP_DISPLAY_NAMES and name not in IGNORED_APPS:
                    screen_time[name] += 1
                    
                    if screen_time[name]  >= NOTIFICATION_THRESHOLD*60:
                        send_notification(get_display_name(name), screen_time[name])
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        time.sleep(1)

    df = pd.DataFrame(list(screen_time.items()), columns=["Application", "Time_Seconds"])
    df['Display_Name'] = df['Application'].apply(get_display_name)
    df['Time_Minutes'] = df['Time_Seconds'] / 60
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
        # Calculate advanced metrics
        productivity_ratio = category_usage.get('Productivity', 0) / total_time
        entertainment_ratio = (category_usage.get('Entertainment', 0) + 
                             category_usage.get('Social Media', 0)) / total_time
        communication_ratio = category_usage.get('Communication', 0) / total_time
        
        # Generate dynamic insights based on usage patterns
        if productivity_ratio < 0.3:
            insights.append({
                'type': 'warning',
                'message': "🎯 Low productivity detected. Consider using time-blocking techniques."
            })
        elif productivity_ratio > 0.7:
            insights.append({
                'type': 'info',
                'message': "⚡ High productivity! Remember to take breaks to avoid burnout."
            })
            
        if entertainment_ratio > 0.4:
            insights.append({
                'type': 'warning',
                'message': "⚠️ High entertainment usage. Try setting specific leisure time windows."
            })
            
        if communication_ratio > 0.3:
            insights.append({
                'type': 'info',
                'message': "💬 Consider batching communication tasks to reduce context switching."
            })
            
        # Time management insights
        if total_time > 120:
            insights.append({
                'type': 'health',
                'message': "🧘 Practice the 20-20-20 rule: Every 20 minutes, look 20 feet away for 20 seconds."
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

def analyze_usage_patterns(screen_time_data):
    """Analyze usage patterns with more sophisticated insights."""
    usage_data = screen_time_data.copy()
    usage_data['Category'] = usage_data['Application'].apply(categorize_app)
    category_usage = usage_data.groupby('Category')['Time_Minutes'].sum()
    
    insights = []
    total_time = usage_data['Time_Minutes'].sum()
    
    if total_time > 0:
        # Calculate advanced metrics
        productivity_ratio = category_usage.get('Productivity', 0) / total_time
        entertainment_ratio = (category_usage.get('Entertainment', 0) + 
                             category_usage.get('Social Media', 0)) / total_time
        communication_ratio = category_usage.get('Communication', 0) / total_time
        
        # Generate dynamic insights based on usage patterns
        if productivity_ratio < 0.3:
            insights.append({
                'type': 'warning',
                'message': "🎯 Low productivity detected. Consider using time-blocking techniques."
            })
        elif productivity_ratio > 0.7:
            insights.append({
                'type': 'info',
                'message': "⚡ High productivity! Remember to take breaks to avoid burnout."
            })
            
        if entertainment_ratio > 0.4:
            insights.append({
                'type': 'warning',
                'message': "⚠️ High entertainment usage. Try setting specific leisure time windows."
            })
            
        if communication_ratio > 0.3:
            insights.append({
                'type': 'info',
                'message': "💬 Consider batching communication tasks to reduce context switching."
            })
            
        # Time management insights
        if total_time > 120:
            insights.append({
                'type': 'health',
                'message': "🧘 Practice the 20-20-20 rule: Every 20 minutes, look 20 feet away for 20 seconds."
            })
    
    return insights, category_usage

def main():
    st.set_page_config(page_title="Smart Screen Time Tracker", page_icon="🤖", layout="wide")
    
    st.title("🤖 Smart Screen Time Analytics")
    st.markdown("### AI-Powered Usage Insights & Recommendations")
    
    with st.sidebar:
        st.header("⚙️ Settings")
        track_duration = st.slider(
            "Tracking Duration (seconds)", 
            min_value=10, 
            max_value=3600, 
            value=60
        )
    
    if st.button("Start Smart Tracking", type="primary"):
        with st.spinner("🔍 Analyzing your screen time patterns..."):
            screen_time_data = track_screen_time(duration=track_duration)
            
            # Display usage statistics
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📊 Active Applications")
                significant_usage = screen_time_data[screen_time_data['Time_Minutes'] > 1]
                st.dataframe(
                    significant_usage[['Display_Name', 'Time_Minutes']].style.format({
                        'Time_Minutes': '{:.1f}'
                    })
                )
            
            # Generate and display insights
            insights, category_usage = analyze_usage_patterns(screen_time_data)
            
            # Get recommendations after adding category information
            recommendations = generate_ai_recommendations(screen_time_data, screen_time_data['Time_Minutes'].sum())
            
            with col2:
                st.subheader("🧠 AI Insights")
                for insight in insights:
                    if insight['type'] == 'warning':
                        st.warning(insight['message'])
                    elif insight['type'] == 'info':
                        st.info(insight['message'])
                    else:
                        st.success(insight['message'])
            
            # Display visualizations
            st.subheader("📈 Usage Analytics")
            fig = plot_screen_time(screen_time_data)
            st.pyplot(fig)
            
            # Display recommendations
            st.subheader("💡 Smart Recommendations")
            for i, rec in enumerate(recommendations, 1):
                st.write(f"{i}. {rec}")
            
            # Display alerts for excessive usage
            st.subheader("⚠️ Usage Alerts")
            excessive_usage = screen_time_data[screen_time_data['Time_Minutes'] > NOTIFICATION_THRESHOLD]
            if not excessive_usage.empty:
                for _, row in excessive_usage.iterrows():
                    st.warning(f"Extended usage detected: {row['Display_Name']} ({row['Time_Minutes']:.1f} minutes)")
            else:
                st.success("👏 Great job! No excessive application usage detected.")

    st.markdown("---")
    st.caption("Developed by Mithil and Vaibhav")

main()