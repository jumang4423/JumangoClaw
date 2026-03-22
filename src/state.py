import logging
from queue import Queue

logger = logging.getLogger(__name__)

# --- Conversation State ---
user_conversations = {}
abort_flags = {}

def get_history(user_id):
    if user_id not in user_conversations:
        logger.debug(f"Initializing new conversation history for user_id={user_id}")
        user_conversations[user_id] = []
    return user_conversations[user_id]

def add_message(user_id, message_obj):
    history = get_history(user_id)
    history.append(message_obj)
    logger.debug(f"Added message to history for user_id={user_id}. History length: {len(history)}")

def clear_history(user_id):
    if user_id in user_conversations:
        del user_conversations[user_id]
        logger.info(f"Cleared conversation history for user_id={user_id}")
    abort_flags[user_id] = False
    
    # Also drop queued tasks when memory is wiped
    if user_id in user_queues:
        with user_queues[user_id].mutex:
            user_queues[user_id].queue.clear()
            
    return True

def remove_last_message(user_id):
    if user_id in user_conversations and len(user_conversations[user_id]) > 0:
        user_conversations[user_id].pop()
        logger.debug(f"Removed last message for user_id={user_id}. History length: {len(user_conversations[user_id])}")

def set_abort_flag(user_id, value: bool):
    abort_flags[user_id] = value

def get_abort_flag(user_id) -> bool:
    return abort_flags.get(user_id, False)


# --- Task Queue State ---
user_queues = {}          # user_id -> Queue()
active_tasks = {}         # user_id -> dict representing current task
user_task_counters = {}   # user_id -> int

def get_user_queue(user_id) -> Queue:
    if user_id not in user_queues:
        user_queues[user_id] = Queue()
    return user_queues[user_id]

def enqueue_task(user_id, text: str) -> dict:
    if user_id not in user_task_counters:
        user_task_counters[user_id] = 1
    
    task_id = user_task_counters[user_id]
    user_task_counters[user_id] += 1
    
    name = text[:20] + ("..." if len(text) > 20 else "")
    task = {"id": task_id, "name": name, "text": text, "status": "queued", "logs": []}
    
    get_user_queue(user_id).put(task)
    return task

def get_all_tasks(user_id) -> list:
    tasks = []
    active = active_tasks.get(user_id)
    if active:
        tasks.append(active)
        
    q = get_user_queue(user_id)
    with q.mutex:
        tasks.extend(list(q.queue))
    return tasks

def cancel_task(user_id, task_id: int) -> str:
    """Returns 'running', 'queued', or None based on what was cancelled."""
    active = active_tasks.get(user_id)
    if active and active["id"] == task_id:
        set_abort_flag(user_id, True)
        return "running"
        
    q = get_user_queue(user_id)
    with q.mutex:
        queue_list = list(q.queue)
        for i, t in enumerate(queue_list):
            if t["id"] == task_id:
                del q.queue[i]
                return "queued"
                
    return None

import os
import json

CRONS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace", "crons.json")

def _load_crons():
    if not os.path.exists(CRONS_FILE):
        return []
    try:
        with open(CRONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_crons(crons):
    os.makedirs(os.path.dirname(CRONS_FILE), exist_ok=True)
    with open(CRONS_FILE, "w", encoding="utf-8") as f:
        json.dump(crons, f, indent=4, ensure_ascii=False)

def get_all_crons() -> list:
    return _load_crons()

def add_cron(user_id: int, time_str: str, prompt: str) -> dict:
    crons = _load_crons()
    cron_id = 1 if not crons else max(c.get("id", 0) for c in crons) + 1
    new_cron = {
        "id": cron_id,
        "user_id": user_id,
        "time": time_str,
        "prompt": prompt
    }
    crons.append(new_cron)
    _save_crons(crons)
    return new_cron

def delete_cron(user_id: int, cron_id: int) -> bool:
    crons = _load_crons()
    new_crons = [c for c in crons if not (c["id"] == cron_id and c["user_id"] == user_id)]
    if len(crons) == len(new_crons):
        return False
    _save_crons(new_crons)
    return True

ONESHOTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace", "oneshots.json")

def _load_oneshots():
    if not os.path.exists(ONESHOTS_FILE):
        return []
    try:
        with open(ONESHOTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_oneshots(oneshots):
    os.makedirs(os.path.dirname(ONESHOTS_FILE), exist_ok=True)
    with open(ONESHOTS_FILE, "w", encoding="utf-8") as f:
        json.dump(oneshots, f, indent=4, ensure_ascii=False)

def get_all_oneshots() -> list:
    return _load_oneshots()

def add_oneshot(user_id: int, time_str: str, prompt: str) -> dict:
    oneshots = _load_oneshots()
    oneshot_id = 1 if not oneshots else max(c.get("id", 0) for c in oneshots) + 1
    new_oneshot = {
        "id": oneshot_id,
        "user_id": user_id,
        "time": time_str,
        "prompt": prompt
    }
    oneshots.append(new_oneshot)
    _save_oneshots(oneshots)
    return new_oneshot

def delete_oneshot(user_id: int, oneshot_id: int) -> bool:
    oneshots = _load_oneshots()
    new_oneshots = [c for c in oneshots if not (c["id"] == oneshot_id and c["user_id"] == user_id)]
    if len(oneshots) == len(new_oneshots):
        return False
    _save_oneshots(new_oneshots)
    return True
