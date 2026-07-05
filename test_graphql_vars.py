import json
import uuid
import time
from instagrapi import Client

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

doc_id = config.get("instagram", {}).get("musicSendDocId", "26548947361463418")
session_file = "session.json"

cl = Client()
cl.load_settings(session_file)

# We just need any valid thread_id and audio_id to test variable names.
# You can replace these with real ones if you want, but for schema testing, 
# even dummy ones might bypass the "missing_required_variable_value" error.
test_thread_id = "340282366841710301281180609439947874545" # from your logs
test_audio_id = "272185964632963" # Freaks

combinations = [
    # 1. target_thread_id instead of thread_id
    {
        "name": "target_thread_id",
        "vars": {
            "target_thread_id": test_thread_id,
            "audio_asset_id": test_audio_id,
            "client_context": str(uuid.uuid4())
        }
    },
    # 2. recipient_users (sometimes used for new threads)
    {
        "name": "recipient_users",
        "vars": {
            "recipient_users": [cl.user_id],
            "audio_asset_id": test_audio_id,
            "client_context": str(uuid.uuid4())
        }
    },
    # 3. action variable included
    {
        "name": "with_action",
        "vars": {
            "thread_id": test_thread_id,
            "audio_asset_id": test_audio_id,
            "client_context": str(uuid.uuid4()),
            "action": "send_item"
        }
    },
    # 4. input wrapper instead of data
    {
        "name": "input_wrapper",
        "vars": {
            "input": {
                "thread_id": test_thread_id,
                "audio_asset_id": test_audio_id,
                "client_context": str(uuid.uuid4())
            }
        }
    },
    # 5. ALL OF THE ABOVE to see if we can trigger "Unknown variable" instead of "missing"
    {
        "name": "kitchen_sink",
        "vars": {
            "thread_id": test_thread_id,
            "thread_ids": [test_thread_id],
            "target_thread_id": test_thread_id,
            "recipient_users": [cl.user_id],
            "audio_asset_id": test_audio_id,
            "audio_id": test_audio_id,
            "music_asset_id": test_audio_id,
            "client_context": str(uuid.uuid4()),
            "mutation_token": str(uuid.uuid4()),
            "action": "send_item",
            "text": "",
            "data": {
                "thread_id": test_thread_id,
                "audio_asset_id": test_audio_id,
                "client_context": str(uuid.uuid4())
            },
            "input": {
                "thread_id": test_thread_id,
                "audio_asset_id": test_audio_id,
                "client_context": str(uuid.uuid4())
            }
        }
    }
]

print(f"Testing GraphQL mutations for doc_id {doc_id}...")
for combo in combinations:
    print(f"\n--- Testing: {combo['name']} ---")
    payload = {
        "doc_id": doc_id,
        "variables": json.dumps(combo["vars"])
    }
    try:
        res = cl.private_request("ads/graphql/", data=payload)
        print("SUCCESS or NO EXCEPTION!")
        print(res)
    except Exception as e:
        print("Error:", e)
        # instagrapi throws error if JSON has 'errors'
    time.sleep(2)
