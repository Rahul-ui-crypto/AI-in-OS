import streamlit as st
st.set_page_config(page_title="Screen Time Tracker - Admin", page_icon="⚙️", layout="wide")

import json
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path so we can import from main.py
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from main import get_display_name, load_profiles, PROFILES_FILE

def save_profiles(profiles):
    """Save profiles to JSON file"""
    with open(PROFILES_FILE, 'w') as f:
        json.dump(profiles, f, indent=4)

st.title("⚙️ Screen Time Tracker Admin")

# Initialize session states
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False
if 'profiles' not in st.session_state:
    st.session_state.profiles = load_profiles()

# Authentication (simple password protection)
if not st.session_state.admin_authenticated:
    with st.form("auth_form"):
        password = st.text_input("Enter admin password", type="password")
        if st.form_submit_button("Login"):
            if password == "RahuL1925":  # Admin password
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
    st.stop()

# Load existing profiles
profiles = st.session_state.profiles

# Profile management section
st.header("Profile Management")

# Add new profile section
with st.expander("➕ Add New Profile", expanded=False):
    with st.form(key="new_profile_form"):
        new_profile_name = st.text_input("New Profile Name")
        new_profile_id = st.text_input("Profile ID (e.g., kids_profile, parent_profile)")
        
        st.subheader("App Time Limits (minutes)")
        new_app_limits = {}
        common_apps = ["whatsapp.exe", "chrome.exe", "facebook.exe"]
        for app in common_apps:
            new_app_limits[app] = st.number_input(
                f"Time limit for {get_display_name(app)} (minutes)",
                min_value=0,
                value=30
            )
        
        new_is_default = st.checkbox("Set as default profile")
        
        if st.form_submit_button("Create Profile"):
            if new_profile_id and new_profile_name:
                if new_profile_id in profiles:
                    st.error("Profile ID already exists!")
                else:
                    profiles[new_profile_id] = {
                        "name": new_profile_name,
                        "app_limits": new_app_limits,
                        "is_default": new_is_default
                    }
                    
                    if new_is_default:
                        for p in profiles:
                            if p != new_profile_id:
                                profiles[p]["is_default"] = False
                    
                    save_profiles(profiles)
                    st.session_state.profiles = profiles
                    st.success(f"Profile {new_profile_name} created successfully!")
                    st.rerun()
            else:
                st.error("Please fill in both Profile Name and Profile ID!")

# Edit existing profile section
st.subheader("📝 Edit Existing Profile")
col1, col2 = st.columns([3, 1])
with col1:
    selected_profile = st.selectbox("Select Profile to Edit", list(profiles.keys()))
with col2:
    if st.button("🗑️ Delete Profile", type="secondary"):
        if len(profiles) > 1:  # Prevent deleting the last profile
            if profiles[selected_profile].get("is_default", False):
                # If deleting default profile, make another one default
                other_profile = next(p for p in profiles if p != selected_profile)
                profiles[other_profile]["is_default"] = True
            del profiles[selected_profile]
            save_profiles(profiles)
            st.session_state.profiles = profiles
            st.success("Profile deleted successfully!")
            st.rerun()
        else:
            st.error("Cannot delete the last profile!")

with st.form(key="profile_form"):
    # Profile name
    profile_name = st.text_input("Profile Name", value=profiles[selected_profile]["name"])

    # App limits
    st.subheader("App Time Limits (minutes)")
    app_limits = {}
    
    # Common apps to limit
    common_apps = ["whatsapp.exe", "chrome.exe", "facebook.exe"]
    for app in common_apps:
        current_limit = profiles[selected_profile]["app_limits"].get(app, 0)
        app_limits[app] = st.number_input(
            f"Time limit for {get_display_name(app)} (minutes)",
            min_value=0,
            value=current_limit
        )

    # Set as default profile
    is_default = st.checkbox(
        "Set as default profile",
        value=profiles[selected_profile]["is_default"]
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.form_submit_button("Save Changes"):
            # Update profile data
            profiles[selected_profile] = {
                "name": profile_name,
                "app_limits": app_limits,
                "is_default": is_default
            }

            # If this profile is set as default, unset others
            if is_default:
                for p in profiles:
                    if p != selected_profile:
                        profiles[p]["is_default"] = False

            # Save profiles
            save_profiles(profiles)
            st.session_state.profiles = profiles
            st.success(f"Profile {profile_name} updated successfully!")

# Display current profiles
st.header("👥 Current Profiles")
st.info("These are all the currently configured profiles and their settings.")
st.json(profiles)

# Add a logout button in the sidebar
with st.sidebar:
    st.markdown("---")
    if st.button("🚪 Logout", type="primary"):
        st.session_state.admin_authenticated = False
        st.rerun() 