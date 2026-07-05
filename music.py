# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#          ✨ AYAAN AI ✨
#        !play Music Command
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Complete working music sticker send with GraphQL
# ✅ Added human-like delays to avoid rate limits

import re
import time
import requests
import json
import logging
import random
from typing import Any, Optional, Dict
from instagrapi import Client

# ── Constants ──
GRAPHQL_URL = "https://www.instagram.com/api/graphql"
IG_WEB_APP_ID = "936619743392459"
REQUEST_TIMEOUT = 30
COOLDOWN_SECONDS = 0  # Disabled for speed

# ── Web Session Values ──
COMET_AV = "17841417100740600"
COMET_HS = "20638.HYP:instagram_web_pkg.2.1...0"
COMET_REV = "1042629546"
COMET_HSI = "7658669625254534644"
COMET_DYN = "7xeUjG1mxu1syaxG4Vp41twpUnwgU7SbzEdF8aUco2qwJyEiw9-1DwUx609vCwjE1EEc87m0yE462mcw5Mx62G5UswoEcE7O2l0Fwqo5W1yw9O1lwxwQzXwae4UaEW2G0AEco5G0zK5o4q1qwl81wEbUGdwtUeo9UaQ0Lo6-bwHwKG1pg2fwxyo6O1FwlAcwBwUQp6x6U42UnAwCAxW1oxe6U5q0EoKmUhw4rwXyEcE4y16wAwj83KwRyrg"
COMET_CRN = "comet.igweb.PolarisDirectInboxRoute"

SEND_S = "sf6vvb:4iobru:4g6c80"
SEND_CSR = "gJd1T95P9v79Y_cIV3shkVbpuA8b98YwmfRT_8rikL_h3aGRaFrABuGWFeyd4ytRHa-GmTABy4VGKgyOsDZVlpTRoFfEyu8hArHi8GviFqBACGmyCgKGjlau8HyfWzDAJzuQKiK9yEysx4A9gKdCBCCgyvKin9hUzDBzUNLizpkZ4jzBTAQnF6BhASKHAgSmueGAu468HAx-ahVFEOmbFoCieXK8ghpoPCh238xAAztGFbAVUdE2ow3T8057W01cMw0chm1wxO0eoU0gie0vy0JF98mwhm0d2a0GU7iu0z8O0f8gjxC8w5lw4p83u0KV84O5obU4C0CUzo0yy35aayk5Yw1780EOpPwumbAhAVt0CwtEvoiALoqw3CokwSo05oi0aHw0z2o1k85G1sw5IwYw3YE0tEIM1S8aQ2V7ki"
SEND_HSDP = "g4DZ86yBpqEAga6GTQSy-sFlkdHchF4EEibzh8wXxFaz4i-Ax-oiA8cV8LEUjggAxC7x0IC1om79Emz8V2Q0zOxaVSl2AmezGxW8O93A3Kp7gy4985q216xy1Sxui2aezof898co982zJ16EJ1mfAxC261Px63W2iifAx210CyUjAw_w5vwt8d80Ja0488cU2sxO3u064815u1xw5Sw4Hwai0giew5pw2iQ0d6wde15w9O3Vafg6i0yo1TU9Hw"
SEND_HBLP = "4wg85-78eUG6E9omghKUyfxm4EqguwVzoyl39UCiucAxJ1rg5DDCyUkyEa8O1_iKUCVe8VVAmHWl2-E-eKQmdJxa7KbhGhRzAUG5oc-fx16VEyqiEKfx64EqDJ5xuibxquqmu22aybKq7oW2adglx-2qiaV84mRKqgxaJ5DDzWUpzVeFA1PByUfE8QiEOQ498kwzGHyUF0OzoK1nyo7S1_wRCCK545Edaw5gwsE4yu1Zx-78do1zo3mw5AwwwPw9O78dU0PW17Bg1CE4u1IwOws820wzUcEbE5ifwo8ek322C6EW0VUde0Eei0_UW0iy5ECfw44w56g3zw2e8aoszQ0wUmyEcojw9N0Cxpafg6i1CxfUG69GxhBDU-36m3a59U2bU6-2qU"
SEND_SJSP = "g4DZ8D3QsFmmHp2yxGJZdELDall3qRp6Fqa4DUQg4UqiEN4ihctC4F23eibWe2mi6ou42-E5xo4u6U2gxG0x8eVAu9x20iO14w0oEU"
SEND_QPL_FLOW_IDS = "354954279,67975436"

_req_counter = 80
_last_used: Dict[str, float] = {}
_last_request_time: float = 0  # ⬆️ Global request tracker


def _next_req_id() -> str:
    global _req_counter
    _req_counter += 1
    return str(_req_counter)


def get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    try:
        return getattr(obj, attr, default)
    except:
        return default


# ═══════════════════════════════════════════════════════════════
#  HUMAN-LIKE DELAY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def human_like_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Add random delay to look human-like (Disabled for speed)"""
    pass


def ensure_request_gap(min_gap: float = 2.0):
    """Ensure minimum gap between requests (Disabled for speed)"""
    pass


def _get_session_cookie(client: Client) -> tuple[Optional[str], Optional[str]]:
    """Extract sessionid from client"""
    try:
        if hasattr(client, 'cookies') and client.cookies:
            if isinstance(client.cookies, dict):
                if 'sessionid' in client.cookies:
                    return client.cookies['sessionid'], "cookies.dict"
            else:
                for cookie in client.cookies:
                    if cookie.name == "sessionid":
                        return cookie.value, "cookies"
    except:
        pass
    
    try:
        if hasattr(client, 'private') and hasattr(client.private, 'cookies'):
            if isinstance(client.private.cookies, dict):
                if 'sessionid' in client.private.cookies:
                    return client.private.cookies['sessionid'], "private.cookies.dict"
            else:
                for cookie in client.private.cookies:
                    if cookie.name == "sessionid":
                        return cookie.value, "private.cookies"
    except:
        pass
    
    try:
        if hasattr(client, 'sessionid') and client.sessionid:
            return client.sessionid, "attribute"
    except:
        pass
    
    return None, None


def _get_fb_dtsg_and_lsd(client: Client) -> tuple[Optional[str], Optional[str]]:
    """Scrape fb_dtsg and lsd from Instagram web page"""
    try:
        # ✅ Human-like delay before web request
        human_like_delay(1.5, 3.5)
        ensure_request_gap(2.0)
        
        sessionid, _ = _get_session_cookie(client)
        if not sessionid:
            return None, None
        
        session = requests.Session()
        session.cookies.set("sessionid", sessionid, domain=".instagram.com")
        
        csrf_token = None
        try:
            for cookie in client.private.cookies:
                if cookie.name == "csrftoken":
                    csrf_token = cookie.value
                    break
        except:
            pass
        
        if csrf_token:
            session.cookies.set("csrftoken", csrf_token, domain=".instagram.com")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        response = session.get(
            "https://www.instagram.com/direct/inbox/",
            headers=headers,
            timeout=15
        )
        
        html = response.text
        
        fb_dtsg = None
        patterns = [
            r'"fb_dtsg":"([^"]+)"',
            r'"DTSGInitialData",\s*\[\],\s*{\s*"token":"([^"]+)"',
            r'"f\+/BAn"\s*:\s*"([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                fb_dtsg = match.group(1)
                break
        
        lsd = None
        patterns = [
            r'"LSD",\s*\[\],\s*{\s*"token":"([^"]+)"',
            r'"lsd":"([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                lsd = match.group(1)
                break
        
        return fb_dtsg, lsd
        
    except Exception as e:
        logging.error(f"Failed to get fb_dtsg/lsd: {e}")
        return None, None


def send_music_sticker_graphql_api(
    client: Client, thread_id: str, track: Any) -> bool:
    """Send music sticker using GraphQL with proper form_data"""
    try:
        title = (
            get_attr(track, "title")
            or get_attr(track, "display_title")
            or "Unknown title"
        )
        artist = (
            get_attr(track, "display_artist")
            or get_attr(track, "subtitle")
            or "Unknown artist"
        )
        audio_cluster_id = (
            get_attr(track, "audio_cluster_id") 
            or get_attr(track, "id") 
            or ""
        )

        if not audio_cluster_id:
            logging.error("Missing audio cluster id")
            return False

        # ✅ Human-like delay before getting session
        human_like_delay(0.5, 1.5)
        ensure_request_gap(1.5)

        sessionid, _sid_source = _get_session_cookie(client)
        if not sessionid:
            logging.error("No sessionid available")
            return False

        fb_dtsg, lsd = _get_fb_dtsg_and_lsd(client)
        if not fb_dtsg or not lsd:
            logging.error("Failed to get fb_dtsg or lsd")
            return False

        logging.info(f"Got fb_dtsg: {fb_dtsg[:20]}...")
        logging.info(f"Got lsd: {lsd}")

        csrf_token = None
        try:
            for cookie in client.private.cookies:
                if cookie.name == "csrftoken":
                    csrf_token = cookie.value
                    break
        except:
            pass

        jazoest = "2" + str(sum(ord(c) for c in fb_dtsg))
        logging.info(f"Calculated jazoest: {jazoest}")

        variables_obj = {
            "send_data": {
                "thread_id": str(thread_id),
                "offline_threading_id": str(int(time.time() * 1000))
            },
            "data": {
                "audio_asset_id": str(audio_cluster_id)
            }
        }

        analytics_tags = [f"qpl_active_flow_ids={SEND_QPL_FLOW_IDS}"]

        form_data = {
            "av": COMET_AV,
            "__d": "www",
            "__user": "0",
            "__a": "1",
            "__req": _next_req_id(),
            "__hs": COMET_HS,
            "dpr": "1",
            "__ccg": "GOOD",
            "__rev": COMET_REV,
            "__s": SEND_S,
            "__hsi": COMET_HSI,
            "__dyn": COMET_DYN,
            "__csr": SEND_CSR,
            "__hsdp": SEND_HSDP,
            "__hblp": SEND_HBLP,
            "__sjsp": SEND_SJSP,
            "__comet_req": "7",
            "fb_dtsg": fb_dtsg,
            "jazoest": jazoest,
            "lsd": lsd,
            "__spin_r": COMET_REV,
            "__spin_b": "trunk",
            "__spin_t": str(int(time.time())),
            "__crn": COMET_CRN,
            "qpl_active_flow_ids": SEND_QPL_FLOW_IDS,
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "IGDirectMusicStickerShareMutation",
            "server_timestamps": "true",
            "doc_id": "26883421864608852",
            "variables": json.dumps(variables_obj),
            "fb_api_analytics_tags": json.dumps(analytics_tags),
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://www.instagram.com/direct/inbox/",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "x-ig-app-id": IG_WEB_APP_ID,
            "x-asbd-id": "359341",
        }

        if csrf_token:
            headers["x-csrftoken"] = csrf_token

        session = requests.Session()
        session.cookies.set("sessionid", sessionid, domain=".instagram.com")
        if csrf_token:
            session.cookies.set("csrftoken", csrf_token, domain=".instagram.com")

        doc_ids = ["26883421864608852", "26548947361463418"]

        for doc_id in doc_ids:
            try:
                # ✅ Human-like delay before each request
                human_like_delay(0.5, 1.5)
                ensure_request_gap(1.0)
                
                form_data["doc_id"] = doc_id
                
                logging.info(f"Sending request with doc_id: {doc_id}")
                
                response = session.post(
                    GRAPHQL_URL,
                    data=form_data,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )

                text = response.text
                if text.startswith('for (;;);'):
                    text = text[9:]

                logging.info(f"Response status: {response.status_code}")
                logging.info(f"Response preview: {text[:200]}")

                result = json.loads(text)
                
                if "errors" not in result:
                    logging.info(f"✅ Music sticker sent successfully with doc_id {doc_id}")
                    return True
                else:
                    error_msg = result.get("errors", [{}])[0].get("message", "Unknown")
                    logging.warning(f"GraphQL error: {error_msg}")
                    
            except json.JSONDecodeError as e:
                logging.warning(f"Non-JSON response: {e}")
                continue
            except Exception as e:
                logging.warning(f"Error with doc_id {doc_id}: {e}")
                continue

        return False

    except Exception as e:
        logging.error(f"GraphQL music sticker send failed: {e}")
        return False


def search_track(cl: Client, query: str) -> Optional[tuple]:
    """Search for a track with human-like delays"""
    try:
        # ✅ Human-like delay before search
        human_like_delay(1.0, 2.5)
        ensure_request_gap(1.5)
        
        tracks = cl.search_music(query)
    except Exception as e:
        print(f"  ⚠️ Search failed: {e}")
        return None

    if not tracks:
        return None

    track = tracks[0]
    audio_asset_id = getattr(track, "id", None)
    if not audio_asset_id:
        return None

    title = getattr(track, "title", None) or query
    artist = getattr(track, "display_artist", None) or "Unknown Artist"
    
    return track, str(audio_asset_id), title, artist


def get_itunes_fallback(query: str) -> str:
    """Get iTunes preview link"""
    ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
    try:
        # ✅ Human-like delay before iTunes request
        human_like_delay(0.5, 1.5)
        ensure_request_gap(1.0)
        
        response = requests.get(
            ITUNES_SEARCH_URL,
            params={"term": query, "media": "music", "entity": "song", "limit": 1},
            timeout=15,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except Exception as e:
        print(f"  ⚠️ iTunes fallback failed: {e}")
        return f"❌ No results found for {query}"

    if not results:
        return f"❌ No results found for {query}"

    track = results[0]
    preview_url = track.get("previewUrl", "")
    track_view_url = track.get("trackViewUrl", "")
    
    response_text = f"🎵 **{track.get('trackName', query)}** — {track.get('artistName', '')}\n"
    if preview_url:
        response_text += f"🎧 [Preview] {preview_url}\n"
    if track_view_url:
        response_text += f"🔗 [Apple Music] {track_view_url}"
    
    return response_text


def play_song(query: str, user_id: str, username: str, thread_id: str, cl: Client) -> Optional[str]:
    """
    Main function to handle !play command
    Called from server.py
    """
    query = query.strip()
    if not query:
        return "⚠️ Please specify a song.\nExample: !play Blinding Lights"

    # Check cooldown
    last = _last_used.get(user_id)
    if last is not None:
        elapsed = time.monotonic() - last
        if elapsed < COOLDOWN_SECONDS:
            return f"⏳ Slow down @{username}! Try again in {round(COOLDOWN_SECONDS - elapsed, 1)}s."
    _last_used[user_id] = time.monotonic()

    print(f"\n🔍 Searching for: {query}")
    
    # Search for track
    result = search_track(cl, query)
    if not result:
        return f"❌ No results found for {query}"

    track, audio_asset_id, title, artist = result
    print(f"  🎵 Found: {title} by {artist} (ID: {audio_asset_id})")

    # Try GraphQL
    print(f"  📤 Sending music sticker...")
    try:
        sent = send_music_sticker_graphql_api(cl, thread_id, track)
        if sent:
            print(f"  ✅ Music sticker sent successfully!")
            return None
    except Exception as e:
        print(f"  ⚠️ GraphQL send failed: {e}")

    # Fallback to iTunes link
    print(f"  ℹ️ Using iTunes fallback")
    return get_itunes_fallback(query)


# For backwards compatibility with server.py
def handle_play_command(query: str, user_id: str, username: str, thread_id: str, cl: Client) -> Optional[str]:
    """Alias for play_song - used by server.py"""
    return play_song(query, user_id, username, thread_id, cl)


# ── Standalone Test ──
if __name__ == "__main__":
    import sys
    import os
    
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    
    try:
        import config
    except ImportError:
        print("❌ config.py not found")
        sys.exit(1)
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("""
╔═══════════════════════════════════════╗
║     🎵 AYAAN AI - Music Player       ║
║       Standalone Test Mode           ║
╚═══════════════════════════════════════╝
    """)
    
    session_id = config.SESSION_ID.split(",")[0].strip() if hasattr(config, 'SESSION_ID') else None
    if not session_id:
        print("❌ No SESSION_ID found")
        sys.exit(1)

    print("🔑 Logging in...")
    
    cl = Client()
    try:
        cl.login_by_sessionid(session_id)
        print(f"✅ Logged in as pk={cl.user_id}")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        sys.exit(1)
    
    print("\n" + "─" * 50)
    thread_id = input("📱 Enter thread_id: ").strip()
    song = input("🎵 Enter song name: ").strip()
    
    print("\n▶️ Testing play_song...")
    print("─" * 50)
    
    result = play_song(song, "test_user", "tester", thread_id, cl)
    
    print("─" * 50)
    if result is None:
        print("🎉 SUCCESS! Music sticker sent to the chat!")
    else:
        print(f"ℹ️ Response sent:\n{result}")
    
    print("\n✨ Test complete!")