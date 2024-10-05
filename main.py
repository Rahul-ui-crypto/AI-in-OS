import psutil
import time
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from plyer import notification
from collections import defaultdict

screen_time = {}
usage_history = defaultdict(list)

NOTIFICATION_THRESHOLD = 30
NOTIFICATION_COOLDOWN = 300

last_notification = {}

IGNORED_APPS = ['svchost.exe', 'System Idle Process', 'explorer.exe', 'Registry', 
                'csrss.exe', 'wininit.exe', 'Conhost.exe', 'RuntimeBroker.exe']

APP_CATEGORIES = {
    'Productivity': ['excel.exe', 'word.exe', 'powerpoint.exe', 'code.exe', 'notepad.exe'],
    'Communication': ['teams.exe', 'slack.exe', 'outlook.exe', 'discord.exe', 'skype.exe'],
    'Browsers': ['chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'safari.exe'],
    'Entertainment': ['spotify.exe', 'netflix.exe', 'steam.exe', 'vlc.exe'],
    'Social Media': ['twitter.exe', 'instagram.exe', 'facebook.exe']
}

def categorize_app(app_name):
    for category, apps in APP_CATEGORIES.items():
        if any(app.lower() in app_name.lower() for app in apps):
            return category
    return 'Other'

def analyze_usage_patterns(screen_time_data):
    usage_data = screen_time_data[['Application', 'Time_Minutes']].copy()
    usage_data['Category'] = usage_data['Application'].apply(categorize_app)
    
    category_usage = usage_data.groupby('Category')['Time_Minutes'].sum()
    
    insights = []
    total_time = usage_data['Time_Minutes'].sum()
    
    if total_time > 0:
        prod_time = category_usage.get('Productivity', 0)
        entertainment_time = category_usage.get('Entertainment', 0) + category_usage.get('Social Media', 0)
        
        if prod_time / total_time < 0.3:
            insights.append("🎯 Your productivity apps usage is low. Consider focusing more on work-related tasks.")
        
        if entertainment_time / total_time > 0.5:
            insights.append("⚠️ High entertainment app usage detected. Try to maintain a better work-life balance.")
        
        if total_time > 120:
            insights.append("🧘‍♀️ Remember to take regular breaks using the 20-20-20 rule: Every 20 minutes, look at something 20 feet away for 20 seconds.")
    
    return insights, category_usage

def generate_ai_recommendations(category_usage):
    recommendations = []
    
    high_usage_categories = category_usage[category_usage > 30].index
    
    for category in high_usage_categories:
        if category == 'Productivity':
            recommendations.append("🎯 Consider using time-blocking techniques to maintain high productivity while avoiding burnout.")
        elif category in ['Entertainment', 'Social Media']:
            recommendations.append("⏰ Try setting specific time slots for entertainment to maintain better focus during work hours.")
        elif category == 'Communication':
            recommendations.append("📧 Consider batch-processing emails and messages at set times to reduce constant context switching.")
    
    recommendations.append("🎯 Use the Pomodoro Technique: 25 minutes of focused work followed by 5-minute breaks.")
    recommendations.append("🧘‍♀️ Practice mindful computing by closing unnecessary tabs and applications.")
    
    return recommendations

def send_notification(app_name, usage_time):
    current_time = time.time()
    if app_name not in last_notification or \
       (current_time - last_notification.get(app_name, 0)) > NOTIFICATION_COOLDOWN:
        notification.notify(
            title="⏰ Smart Screen Time Alert",
            message=f"You've been using {app_name} for {usage_time:.1f} minutes.\nAI suggests taking a break!",
            timeout=10
        )
        last_notification[app_name] = current_time

def track_screen_time(duration=60):
    start_time = time.time()
    while time.time() - start_time < duration:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info['name']
                
                if name in IGNORED_APPS:
                    continue
                
                if name not in screen_time:
                    screen_time[name] = 0
                screen_time[name] += 1
                
                minutes_used = screen_time[name] / 60
                if minutes_used >= NOTIFICATION_THRESHOLD:
                    send_notification(name, minutes_used)
                
                usage_history[name].append(minutes_used)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        time.sleep(1)
    
    df = pd.DataFrame(list(screen_time.items()), columns=["Application", "Time_Seconds"])
    df['Time_Minutes'] = df['Time_Seconds'] / 60
    return df.sort_values('Time_Minutes', ascending=False).reset_index(drop=True)

def plot_screen_time(data):
    plot_data = data.head(10)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    ax1.bar(plot_data['Application'], plot_data['Time_Minutes'], color='skyblue')
    ax1.set_xlabel("Top Applications")
    ax1.set_ylabel("Time (Minutes)")
    ax1.set_title("Screen Time - Top 10 Applications")
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    category_data = data.copy()
    category_data['Category'] = category_data['Application'].apply(categorize_app)
    category_usage = category_data.groupby('Category')['Time_Minutes'].sum()
    
    ax2.pie(category_usage, labels=category_usage.index, autopct='%1.1f%%')
    ax2.set_title("Time Distribution by Category")
    
    plt.tight_layout()
    st.pyplot(fig)

st.title("🤖 AI-Powered Screen Time Tracker")
st.write("Smart tracking with AI insights and personalized recommendations!")

st.sidebar.header("⚙️ Settings")
track_duration = st.sidebar.slider(
    "Tracking Duration (seconds)", 
    min_value=10, 
    max_value=3600, 
    value=60
)

if st.button("Start Smart Tracking"):
    with st.spinner("AI is analyzing your screen time..."):
        screen_time_data = track_screen_time(duration=track_duration)
        
        insights, category_usage = analyze_usage_patterns(screen_time_data)
        recommendations = generate_ai_recommendations(category_usage)
        
        st.write("### 📊 Usage Analysis:")
        significant_usage = screen_time_data[screen_time_data['Time_Minutes'] > 1]
        st.dataframe(
            significant_usage[['Application', 'Time_Minutes']].style.format({
                'Time_Minutes': '{:.1f}'
            })
        )
        
        st.write("### 📈 Smart Usage Analytics:")
        plot_screen_time(screen_time_data)
        
        st.subheader("🤖 AI Insights")
        for insight in insights:
            st.info(insight)
        
        st.subheader("💡 Personalized Recommendations")
        for i, rec in enumerate(recommendations, 1):
            st.write(f"{i}. {rec}")
        
        st.subheader("⚠️ Usage Alerts")
        excessive_usage = screen_time_data[screen_time_data['Time_Minutes'] > NOTIFICATION_THRESHOLD]
        if not excessive_usage.empty:
            for _, row in excessive_usage.iterrows():
                st.warning(f"Extended usage: {row['Application']} ({row['Time_Minutes']:.1f} minutes)")
        else:
            st.success("No excessive app usage detected! Keep up the good work! 🌟")

st.markdown("---")
st.caption("Developed by Mithil and Vaibhav.")