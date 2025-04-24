# Application categories with more detailed classification
APP_CATEGORIES = {
    'Development': {
        'apps': ['code.exe', 'devenv.exe', 'pycharm64.exe', 'idea64.exe', 'webstorm64.exe', 
                'android studio.exe', 'eclipse.exe', 'sublime_text.exe', 'atom.exe',
                'GitHubDesktop.exe', 'SourceTree.exe', 'postman.exe', 'docker desktop.exe'],
        'emoji': '💻',
        'color': '#2ecc71'
    },
    'Databases': {
        'apps': ['postgres.exe', 'pgadmin4.exe', 'mysql.exe', 'mongodb.exe', 'redis-server.exe'],
        'emoji': '🗄️',
        'color': '#e67e22'
    },
    'Office': {
        'apps': ['WINWORD.EXE', 'EXCEL.EXE', 'POWERPNT.EXE', 'OUTLOOK.EXE', 'ONENOTE.EXE',
                'MSACCESS.EXE', 'MSPUB.EXE', 'AcroRd32.exe', 'Acrobat.exe', 'wps.exe',
                'et.exe', 'wpp.exe'],
        'emoji': '💼',
        'color': '#3498db'
    },
    'Communication': {
        'apps': ['teams.exe', 'slack.exe', 'discord.exe', 'skype.exe', 'telegram.exe',
                'whatsapp.exe', 'signal.exe', 'zoom.exe'],
        'emoji': '💬',
        'color': '#9b59b6'
    },
    'Browsers': {
        'apps': ['chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'brave.exe', 'safari.exe'],
        'emoji': '🌐',
        'color': '#e74c3c'
    },
    'Entertainment': {
        'apps': ['spotify.exe', 'netflix.exe', 'steam.exe', 'epicgameslauncher.exe',
                'vlc.exe', 'wmplayer.exe'],
        'emoji': '🎮',
        'color': '#f1c40f'
    },
    'Creative': {
        'apps': ['photoshop.exe', 'illustrator.exe', 'premiere.exe', 'afterfx.exe',
                'lightroom.exe', 'figma.exe', 'sketch.exe', 'blender.exe', 'unity.exe',
                'unreal.exe'],
        'emoji': '🎨',
        'color': '#1abc9c'
    },
    'Utilities': {
        'apps': ['notepad.exe', 'notepad++.exe', 'winrar.exe', '7zg.exe', 'calc.exe',
                'mspaint.exe', 'snippingtool.exe'],
        'emoji': '🔧',
        'color': '#95a5a6'
    },
    'System': {
        'apps': ['taskmgr.exe', 'control.exe', 'cmd.exe', 'powershell.exe', 'WindowsTerminal.exe'],
        'emoji': '⚙️',
        'color': '#34495e'
    }
}

def categorize_app(app_name):
    """Categorize an application based on its name with enhanced matching."""
    app_lower = app_name.lower()
    
    # Check predefined categories first
    for category, info in APP_CATEGORIES.items():
        if any(app.lower() in app_lower for app in info['apps']):
            return category
    
    # Keyword-based categorization for unknown apps
    keywords = {
        'Productivity': ['office', 'doc', 'sheet', 'calc', 'write', 'edit', 'note', 'text'],
        'Communication': ['chat', 'mail', 'message', 'meet', 'call', 'voice', 'team'],
        'Browsers': ['browser', 'web', 'internet'],
        'Entertainment': ['game', 'play', 'media', 'music', 'video', 'stream'],
        'Development': ['code', 'studio', 'dev', 'git', 'ide', 'debug', 'compiler'],
        'Creative': ['design', 'photo', 'art', 'draw', 'paint', 'edit'],
        'System': ['control', 'panel', 'setup', 'config', 'system', 'task', 'service']
    }
    
    for category, keyword_list in keywords.items():
        if any(keyword in app_lower for keyword in keyword_list):
            return category
            
    return 'Other'

def get_category_emoji(category):
    """Get the emoji for a category."""
    return APP_CATEGORIES.get(category, {}).get('emoji', '📱') 