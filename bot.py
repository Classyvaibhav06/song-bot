import json
import uuid
import os
import time
import datetime
import subprocess
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence
from instagrapi import Client

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using existing environment variables.")

try:
    from youtubesearchpython import VideosSearch
except Exception:
    VideosSearch = None

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


import music

# Send Instagram Native Music Attachment (Using music.py configuration)
def send_music_attachment(cl, thread_id, query, sender_id):
    try:
        # Call the new robust Web GraphQL implementation from music.py
        result = music.play_song(query, str(sender_id), "User", thread_id, cl)
        
        # If it returns a string, that means GraphQL failed and it provided an iTunes fallback
        if result and isinstance(result, str):
            cl.direct_send(result, thread_ids=[thread_id])
            
    except Exception as e:
        print(f"[{datetime.datetime.now().isoformat()}] Error sending music attachment: {e}")
        cl.direct_send(f"Sorry, I could not send the music card for \"{query}\" right now.", thread_ids=[thread_id])
        log_interaction("error", sender_id, "/music", "failed", {"query": query, "error": str(e)})

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

@dataclass
class YouTubeDownloadError(Exception):
    message: str
    fallback_link: Optional[str] = None

    def __str__(self):
        return self.message


class YouTubeDownloader:
    def __init__(
        self,
        downloads_dir: str = "downloads",
        cookies_path: str = "cookies.txt",
        player_profiles: Sequence[Sequence[str]] = (
            ("android", "web"),
            ("android_music", "web"),
            ("tv_embedded", "web"),
            ("mweb", "web"),
            ("ios", "web"),
            ("web",),
        ),
        js_runtimes: Sequence[str] = ("node", "deno"),
    ):
        self.base_dir = Path(__file__).resolve().parent
        self.downloads_dir = Path(downloads_dir)
        self.cookies_path = self.base_dir / cookies_path
        self.ytdlp_path = self._resolve_binary(self.base_dir / "yt-dlp.exe", "yt-dlp")
        self.ffmpeg_path = self._resolve_binary(self.base_dir / "ffmpeg.exe", "ffmpeg")
        self.player_profiles = tuple(tuple(profile) for profile in player_profiles)
        self.js_runtimes = tuple(js_runtimes)
        self._cookies_validated = False
        self._cookies_enabled = False
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_binary(self, local_path: Path, fallback_name: str) -> str:
        if local_path.exists():
            return str(local_path)
        return which(fallback_name) or fallback_name

    def _cookie_args(self) -> list[str]:
        if self._cookies_enabled and self.cookies_path.exists() and self.cookies_path.stat().st_size > 0:
            return ["--cookies", str(self.cookies_path)]
        return []

    def _looks_like_netscape_cookie_file(self) -> bool:
        if not self.cookies_path.exists() or self.cookies_path.stat().st_size == 0:
            return False

        try:
            with self.cookies_path.open("r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    return len(stripped.split("\t")) >= 7
        except Exception:
            return False

        return False

    def _js_runtime_args(self) -> list[str]:
        for runtime_name in self.js_runtimes:
            if which(runtime_name):
                return ["--js-runtimes", runtime_name]
        return []

    def _player_client_args(self, profile: Sequence[str]) -> list[str]:
        if not profile:
            return []
        return ["--extractor-args", f"youtube:player_client={','.join(profile)}"]

    def _search_link(self, query: str) -> Optional[str]:
        if VideosSearch is None:
            return None
        try:
            result = VideosSearch(query, limit=1).result()
            items = result.get("result", [])
            if not items:
                return None
            return items[0].get("link")
        except Exception:
            return None

    def _resolve_target(self, query: str) -> tuple[str, Optional[str]]:
        link = self._search_link(query)
        if link:
            return link, link
        return f"ytsearch1:{query}", None

    def validate_cookies(self) -> bool:
        if not self._looks_like_netscape_cookie_file():
            return False

        test_cmd = [
            self.ytdlp_path,
            "--quiet",
            "--no-warnings",
            "--skip-download",
            "--cookies",
            str(self.cookies_path),
            "--print",
            "title",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ] + self._js_runtime_args() + self._player_client_args(("android", "web"))

        result = subprocess.run(test_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            self._cookies_validated = True
            self._cookies_enabled = True
            return True

        print(
            "Cookie validation failed; continuing without cookies. "
            "stdout: {} stderr: {}".format(result.stdout.strip(), result.stderr.strip())
        )
        self._cookies_enabled = False
        return False

    def _build_download_cmd(self, target: str, profile: Sequence[str]) -> list[str]:
        output_template = str(self.downloads_dir / "%(id)s.%(ext)s")
        cmd = [
            self.ytdlp_path,
            target,
            "-x",
            "--audio-format",
            "mp3",
            "--no-playlist",
            "--no-cache-dir",
            "--retries",
            "3",
            "--fragment-retries",
            "3",
            "--socket-timeout",
            "30",
            "-o",
            output_template,
            "--print",
            "filename",
            "--print",
            "title",
            "--print",
            "id",
            "--no-simulate",
        ]

        if self.ffmpeg_path and Path(self.ffmpeg_path).exists():
            cmd.extend(["--ffmpeg-location", str(Path(self.ffmpeg_path).parent)])

        cmd.extend(self._cookie_args())
        cmd.extend(self._js_runtime_args())
        cmd.extend(self._player_client_args(profile))
        return cmd

    def _run_download(self, cmd: list[str]) -> subprocess.CompletedProcess:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise YouTubeDownloadError(
                "yt-dlp failed with exit code {}\nstdout: {}\nstderr: {}".format(
                    result.returncode,
                    result.stdout.strip(),
                    result.stderr.strip(),
                )
            )
        return result

    def download_and_convert(self, query: str, attempts: int = 2):
        if not self._cookies_validated:
            self.validate_cookies()

        last_error: Optional[Exception] = None
        target, fallback_link = self._resolve_target(query)

        for profile in self.player_profiles:
            for attempt in range(1, attempts + 1):
                try:
                    result = self._run_download(self._build_download_cmd(target, profile))
                    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                    if len(lines) < 3:
                        raise YouTubeDownloadError(f"Failed to parse yt-dlp output:\n{result.stdout}")

                    mp3_path = Path(lines[0])
                    title = lines[1]
                    video_id = lines[2]

                    if not mp3_path.exists():
                        candidate = self.downloads_dir / f"{video_id}.mp3"
                        if candidate.exists():
                            mp3_path = candidate
                        else:
                            raise YouTubeDownloadError(f"Downloaded audio file not found at: {mp3_path}")

                    voice_note_path = self.downloads_dir / f"{video_id}_voice.m4a"
                    ffmpeg_cmd = [
                        self.ffmpeg_path,
                        "-y",
                        "-i",
                        str(mp3_path),
                        "-acodec",
                        "aac",
                        "-ac",
                        "1",
                        "-ar",
                        "16000",
                        "-t",
                        "60",
                        str(voice_note_path),
                    ]
                    ffmpeg_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                    if ffmpeg_result.returncode != 0:
                        raise YouTubeDownloadError(
                            "ffmpeg failed with exit code {}\nstdout: {}\nstderr: {}".format(
                                ffmpeg_result.returncode,
                                ffmpeg_result.stdout.strip(),
                                ffmpeg_result.stderr.strip(),
                            )
                        )

                    return voice_note_path, title, mp3_path

                except YouTubeDownloadError as exc:
                    last_error = exc
                    error_text = str(exc).lower()
                    if any(marker in error_text for marker in ("sign in to confirm", "cookies", "not a bot", "login", "403", "bot")):
                        break
                    if attempt < attempts:
                        time.sleep(2 * attempt)
                        continue
                    break

        if isinstance(last_error, YouTubeDownloadError):
            if not last_error.fallback_link and fallback_link:
                last_error.fallback_link = fallback_link
            raise last_error

        raise YouTubeDownloadError("Download failed", fallback_link=fallback_link)


downloader = YouTubeDownloader()


def download_and_convert(query, downloads_dir):
    return downloader.download_and_convert(query)

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
    try:
        # Get actual username from the session or API, not config
        bot_username = cl.username if hasattr(cl, 'username') and cl.username else cl.user_info(cl.user_id).username
    except Exception:
        bot_username = "penguin.7599967" # fallback
    print(f"Bot active. User ID: {bot_user_id}, Username: {bot_username}")
    
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
                    # Best-effort seen receipt; some Instagram endpoints reject this call intermittently.
                    try:
                        cl.direct_send_seen(thread_id=thread.id)
                    except Exception:
                        pass
                        
                    text = msg.text.strip() if msg.text else ""
                    sender_id = str(msg.user_id)
                    
                    # Detect AI Chat Triggers
                    is_chat = False
                    chat_prompt = ""
                    
                    if text.startswith("%talk "):
                        is_chat = True
                        chat_prompt = text[6:].strip()
                    elif bot_username and f"@{bot_username.lower()}" in text.lower():
                        is_chat = True
                        chat_prompt = text
                    else:
                        try:
                            # Use model_dump for Pydantic V2, fallback to dict for V1
                            msg_dict = getattr(msg, "model_dump", getattr(msg, "dict", lambda: {}))()
                            replied_msg = msg_dict.get('replied_to_message') or msg_dict.get('replied_to_action')
                            if replied_msg and isinstance(replied_msg, dict):
                                if str(replied_msg.get('user_id', '')) == bot_user_id:
                                    is_chat = True
                                    chat_prompt = text
                                elif 'item' in replied_msg and str(replied_msg['item'].get('user_id', '')) == bot_user_id:
                                    is_chat = True
                                    chat_prompt = text
                        except Exception:
                            pass
                    
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
                            fallback_link = getattr(pipeline_err, "fallback_link", None)
                            if fallback_link:
                                cl.direct_send(
                                    f"I could not send audio for \"{query}\" right now, but here is the YouTube link:\n{fallback_link}",
                                    thread_ids=[thread_id],
                                )
                            else:
                                cl.direct_send(
                                    f"Sorry, I could not download or process \"{query}\" right now.",
                                    thread_ids=[thread_id],
                                )
                            log_interaction("error", sender_id, "$play", "failed", {"query": query, "error": str(pipeline_err)})
                            
                    elif text.startswith("#at "):
                        query = text[4:].strip()
                        
                        if not query:
                            cl.direct_send("Send #at followed by a song title. Example: #at midnight city", thread_ids=[thread_id])
                            log_interaction("info", sender_id, "#at", "missing_query")
                            processed_data[thread_id] = str(msg.id)
                            continue
                            
                        if not rate_limiter.is_allowed(sender_id):
                            cl.direct_send("You have hit the hourly command limit. Please try again later.", thread_ids=[thread_id])
                            log_interaction("warn", sender_id, "#at", "rate_limited", {"query": query})
                            processed_data[thread_id] = str(msg.id)
                            continue
                            
                        send_music_attachment(cl, thread_id, query, sender_id)
                        
                    elif is_chat:
                        if not chat_prompt:
                            cl.direct_send("Send %talk followed by your message. Example: %talk tell me a joke", thread_ids=[thread_id])
                            log_interaction("info", sender_id, "%talk", "missing_query")
                            processed_data[thread_id] = str(msg.id)
                            continue
                            
                        print(f"[{datetime.datetime.now().isoformat()}] Chat request from {sender_id}: {chat_prompt}")
                        cl.direct_send("Thinking...", thread_ids=[thread_id])
                        
                        try:
                            import requests
                            url = "https://api.groq.com/openai/v1/chat/completions"
                            groq_api_key = os.getenv("GROQ_API_KEY", "")
                            headers = {
                                "Authorization": f"Bearer {groq_api_key}",
                                "Content-Type": "application/json"
                            }
                            payload = {
                                "model": "llama-3.1-8b-instant",
                                "messages": [
                                    {"role": "system", "content": "You are Ayaan AI, a helpful, cool, and concise AI assistant on Instagram."},
                                    {"role": "user", "content": chat_prompt}
                                ],
                                "max_tokens": 300
                            }
                            ai_res = requests.post(url, headers=headers, json=payload, timeout=10)
                            if ai_res.status_code == 200:
                                reply = ai_res.json()["choices"][0]["message"]["content"]
                            else:
                                print(f"Groq API Error {ai_res.status_code}: {ai_res.text}")
                                reply = f"Sorry, AI is currently unavailable (Error {ai_res.status_code})."
                            
                            cl.direct_send(reply, thread_ids=[thread_id])
                            log_interaction("info", sender_id, "%talk", "sent")
                        except Exception as e:
                            print(f"Error calling Groq API: {e}")
                            cl.direct_send("Sorry, I encountered an error connecting to my brain.", thread_ids=[thread_id])
                        
                    elif text == "$help" or text == "/help":
                        help_text = "Commands:\n$play [song] - send voice note\n#at [song] - share native music card\n%talk [message] - chat with Ayaan AI\n$help - show this message"
                        cl.direct_send(help_text, thread_ids=[thread_id])
                        log_interaction("info", sender_id, "$help", "sent")
                        
                    elif text.startswith("$") or text.startswith("/") or text.startswith("#") or text.startswith("%") or text.startswith("!"):
                        cl.direct_send("Unknown command. Type $help for usage.", thread_ids=[thread_id])
                        log_interaction("info", sender_id, text, "unknown_command")
                        
                    # Update tracking
                    processed_data[thread_id] = str(msg.id)
                    with open(processed_file, "w") as f:
                        json.dump(processed_data, f, indent=2)
                        
        except Exception as loop_err:
            print(f"Error in polling loop iteration: {loop_err}")
            
        time.sleep(3) # Poll every 3 seconds to stay safe from rate limits

if __name__ == "__main__":
    main()
