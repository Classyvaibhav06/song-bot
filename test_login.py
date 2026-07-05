import json
import os
from instagrapi import Client

def test_login():
    config_path = "config.json"
    session_file = "session.json"

    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found.")
        return

    with open(config_path, "r") as f:
        config = json.load(f)

    instagram_config = config.get("instagram", {})
    session_id = instagram_config.get("sessionid")

    if not session_id or "YOUR_SESSION_ID" in session_id:
        print("Error: Please set a valid sessionid in config.json.")
        return

    print("Attempting to log in using session ID...")
    cl = Client()
    
    # Set a common user agent to prevent suspicious login flags
    cl.set_user_agent("Instagram 410.0.0.0.96 Android (33/13; 480dpi; 1080x2400; xiaomi; M2007J20CG; surya; qcom; en_US; 641123490)")

    try:
        cl.login_by_sessionid(session_id)
        user_info = cl.account_info()
        print("\n🎉 LOGIN SUCCESSFUL!")
        print(f"Logged in as username: {user_info.username}")
        print(f"Full name: {user_info.full_name}")
        print(f"User ID: {user_info.pk}")
        
        # Save session settings to avoid needing to log in next time
        cl.dump_settings(session_file)
        print(f"Session saved successfully to {session_file}.")
    except Exception as e:
        print("\n❌ LOGIN FAILED!")
        print(f"Error details: {e}")
        print("\nPlease make sure your session ID is correct and has not expired.")

if __name__ == "__main__":
    test_login()
