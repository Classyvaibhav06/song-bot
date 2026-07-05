import json
import os
import time
import datetime
import subprocess
import threading
from collections import defaultdict
from pathlib import Path
from shutil import which
from instagrapi import Client

# Rate Limiter
class RateLimiter:
    def __init__(self, limit_per_hour=30):
        self.limit = limit_per_hour
        self.history = defaultdict(list)

    def is_allowed(self, user_id):
        now = time.time()
        # Filter only timestamps within the last hour (3600 seconds)
        self.history[user_id] = [t for t in self.history[user_id] if now - t < 3600]
        
        if len(self.history[user_id]) >= self.limit:
            return False
            
        self.history[user_id].append(now)
        return True

# Logger
def log_interaction(level, sender_id, command, status, details=None):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "interactions.log")
    
    entry = {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "level": level,
        "senderId": sender_id,
        "command": command,
        "status": status
    }
    if details:
        entry.update(details)
        
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def cleanup_downloads(downloads_dir, max_age_seconds=10):
    if not os.path.exists(downloads_dir):
        return

    now = time.time()
    for entry_name in os.listdir(downloads_dir):
        entry_path = os.path.join(downloads_dir, entry_name)
        try:
            if os.path.isfile(entry_path) and now - os.path.getmtime(entry_path) >= max_age_seconds:
                os.remove(entry_path)
        except Exception as cleanup_err:
            print(f"Failed to remove {entry_path}: {cleanup_err}")

def start_download_cleanup_worker(downloads_dir, interval_seconds=10, max_age_seconds=10):
    def worker():
        while True:
            try:
                cleanup_downloads(downloads_dir, max_age_seconds=max_age_seconds)
            except Exception as cleanup_err:
                print(f"Cleanup worker error: {cleanup_err}")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread

# Audio Search & Download Pipeline
def download_and_convert(query, downloads_dir):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ytdlp_path = os.path.join(base_dir, 'yt-dlp.exe')
    ffmpeg_path = os.path.join(base_dir, 'ffmpeg.exe')
    cookies_path = os.path.join(base_dir, 'cookies.txt')
    
    if not os.path.exists(ytdlp_path):
        ytdlp_path = 'yt-dlp'
    if not os.path.exists(ffmpeg_path):
        ffmpeg_path = 'ffmpeg'
        
    os.makedirs(downloads_dir, exist_ok=True)
    output_template = os.path.join(downloads_dir, "%(id)s.%(ext)s")
    
    ffmpeg_opt = []
    if os.path.exists(ffmpeg_path):
        ffmpeg_opt = ["--ffmpeg-location", base_dir]

    ytdlp_opt = []
    if os.path.exists(cookies_path):
        ytdlp_opt.extend(["--cookies", cookies_path])

    for runtime_name in ("node", "deno"):
        if which(runtime_name):
            ytdlp_opt.extend(["--js-runtimes", runtime_name])
            break
        
    cmd = [
        ytdlp_path,
        f"ytsearch1:{query}",
        "-x",
        "--audio-format", "mp3",
        "--no-playlist",
        "-o", output_template,
        "--print", "filename",
        "--print", "title",
        "--print", "id",
        "--no-simulate"
    ] + ffmpeg_opt + ytdlp_opt
    
    print(f"[{datetime.datetime.now().isoformat()}] Searching YouTube for: \"{query}\"")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(
            "yt-dlp failed with exit code {}\nstdout: {}\nstderr: {}".format(
                result.returncode,
                result.stdout.strip(),
                result.stderr.strip(),
            )
        )
    
    lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
    if len(lines) < 3:
        raise Exception(f"Failed to parse yt-dlp output. stdout: {result.stdout}")
        
    mp3_path = lines[0]
    title = lines[1]
    video_id = lines[2]
    
    # Fallback check if yt-dlp named the file differently
    if not os.path.exists(mp3_path):
        expected_path = os.path.join(downloads_dir, f"{video_id}.mp3")
        if os.path.exists(expected_path):
            mp3_path = expected_path
        else:
            raise Exception(f"Downloaded audio file not found at: {mp3_path}")
            
    print(f"[{datetime.datetime.now().isoformat()}] Downloaded: \"{title}\" (ID: {video_id})")
    
    # Convert to compliant voice note format (m4a, mono, 16000Hz, AAC)
    voice_note_filename = f"{video_id}_voice.m4a"
    voice_note_path = os.path.join(downloads_dir, voice_note_filename)
    
    ffmpeg_cmd = [
        ffmpeg_path,
        "-y",
        "-i", mp3_path,
        "-acodec", "aac",
        "-ac", "1",
        "-ar", "16000",
        "-t", "60", # limit to 60s max duration
        voice_note_path
    ]
    
    print(f"[{datetime.datetime.now().isoformat()}] Converting audio to Voice Note format...")
    subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
    print(f"[{datetime.datetime.now().isoformat()}] Conversion successful: {voice_note_path}")
    
    return voice_note_path, title, mp3_path

def main():
    config_path = "config.json"
    session_file = "session.json"
    processed_file = "processed_messages.json"
    downloads_dir = "downloads"
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"{config_path} is missing.")
        
    with open(config_path, "r") as f:
        config = json.load(f)
        
    instagram_config = config.get("instagram", {})
    session_id = instagram_config.get("sessionid")
    limit_per_hour = config.get("limits", {}).get("commandsPerHour", 30)
    
    if not session_id or "YOUR_SESSION_ID" in session_id:
        raise ValueError("Please provide a valid sessionid in config.json")
        
    # Init client
    cl = Client()
    cl.set_user_agent("Instagram 410.0.0.0.96 Android (33/13; 480dpi; 1080x2400; xiaomi; M2007J20CG; surya; qcom; en_US; 641123490)")
    
    # Login Flow
    logged_in = False
    if os.path.exists(session_file):
        try:
            print("Loading existing session settings...")
            cl.load_settings(session_file)
            cl.account_info() # verify if session is still valid
            logged_in = True
            print("Logged in successfully using saved session.")
        except Exception as e:
            print(f"Saved session invalid: {e}. Re-authenticating...")
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                except Exception:
                    pass
            cl = Client()
            cl.set_user_agent("Instagram 410.0.0.0.96 Android (33/13; 480dpi; 1080x2400; xiaomi; M2007J20CG; surya; qcom; en_US; 641123490)")
            
    if not logged_in:
        print("Authenticating with Instagram using session ID...")
        try:
            cl.login_by_sessionid(session_id)
            cl.dump_settings(session_file)
            print("Logged in successfully. Saved new session settings.")
        except Exception as e:
            print(f"Failed to login via session ID: {e}")
            return
            
    bot_user_id = str(cl.user_id)
    print(f"Bot active. User ID: {bot_user_id}")
    
    rate_limiter = RateLimiter(limit_per_hour)
    start_download_cleanup_worker(downloads_dir, interval_seconds=10, max_age_seconds=10)
    
    # Load processed messages tracker
    processed_data = {}
    if os.path.exists(processed_file):
        try:
            with open(processed_file, "r") as f:
                processed_data = json.load(f)
        except Exception:
            processed_data = {}
            
    print("Starting direct message polling loop...")
    while True:
        try:
            threads = cl.direct_threads(amount=15)
            for thread in threads:
                thread_id = str(thread.id)
                last_processed_id = processed_data.get(thread_id)
                
                messages = thread.messages
                if not messages:
                    continue
                    
                # Identify new messages that are NOT sent by the bot
                new_messages = []
                if not last_processed_id:
                    # Thread not tracked yet. Only process the single most recent message to prevent spamming history
                    latest_msg = messages[0]
                    if str(latest_msg.user_id) != bot_user_id:
                        new_messages = [latest_msg]
                else:
                    for msg in messages:
                        if str(msg.id) == last_processed_id:
                            break
                        if str(msg.user_id) != bot_user_id:
                            new_messages.append(msg)
                    # Reverse to process from oldest to newest
                    new_messages.reverse()
                    
                for msg in new_messages:
                    # Mark thread as seen up to this message
                    try:
                        cl.direct_send_seen(msg.id)
                    except Exception as e:
                        print(f"Could not send seen receipt: {e}")
                        
                    text = msg.text.strip() if msg.text else ""
                    sender_id = str(msg.user_id)
                    
                    if text.startswith("$play "):
                        query = text[6:].strip()
                        
                        if not query:
                            cl.direct_send("Send $play followed by a song title. Example: $play midnight city", thread_ids=[thread_id])
                            log_interaction("info", sender_id, "$play", "missing_query")
                            processed_data[thread_id] = str(msg.id)
                            continue
                            
                        if not rate_limiter.is_allowed(sender_id):
                            cl.direct_send("You have hit the hourly command limit. Please try again later.", thread_ids=[thread_id])
                            log_interaction("warn", sender_id, "$play", "rate_limited", {"query": query})
                            processed_data[thread_id] = str(msg.id)
                            continue
                            
                        print(f"Processing command '$play {query}' from user {sender_id}")
                        log_interaction("info", sender_id, "$play", "searching", {"query": query})
                        
                        # Let the user know the bot is looking for the song
                        cl.direct_send(f"🎵 Searching for \"{query}\"...", thread_ids=[thread_id])
                        
                        try:
                            # Run ytsearch + conversion pipeline
                            voice_path, title, orig_mp3 = download_and_convert(query, downloads_dir)
                            
                            # Send voice note
                            print(f"Sending voice note: {voice_path}")
                            cl.direct_send_voice(Path(voice_path), thread_ids=[thread_id])
                            
                            cl.direct_send(f"Found: {title}", thread_ids=[thread_id])
                            
                            log_interaction("info", sender_id, "$play", "sent", {"query": query, "title": title})
                                
                        except Exception as pipeline_err:
                            print(f"Pipeline error: {pipeline_err}")
                            cl.direct_send(f"Sorry, I could not download or process \"{query}\" right now.", thread_ids=[thread_id])
                            log_interaction("error", sender_id, "$play", "failed", {"query": query, "error": str(pipeline_err)})
                            
                    elif text == "$help":
                        help_text = "Commands:\n$play [song name] - search YouTube and send it as a voice note\n$help - show this message"
                        cl.direct_send(help_text, thread_ids=[thread_id])
                        log_interaction("info", sender_id, "$help", "sent")
                        
                    elif text.startswith("$"):
                        cl.direct_send("Unknown command. Type $help for usage.", thread_ids=[thread_id])
                        log_interaction("info", sender_id, text, "unknown_command")
                        
                    # Update tracking
                    processed_data[thread_id] = str(msg.id)
                    with open(processed_file, "w") as f:
                        json.dump(processed_data, f, indent=2)
                        
        except Exception as loop_err:
            print(f"Error in polling loop iteration: {loop_err}")
            
        time.sleep(15) # Poll every 15 seconds to stay safe from rate limits

if __name__ == "__main__":
    main()
