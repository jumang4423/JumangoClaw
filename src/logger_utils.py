import logging
import json
import os
from datetime import datetime

class JsonRingBufferHandler(logging.Handler):
    def __init__(self, filename, capacity=25):
        super().__init__()
        self.filename = filename
        self.capacity = capacity
        self.log_entries = self._load()
        
    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data[-self.capacity:]
            except Exception:
                pass
        return []

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.log_entries, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
            
    def emit(self, record):
        try:
            # We want short logs
            msg = record.getMessage()
            if len(msg) > 300:
                msg = msg[:300] + "...[truncated]"
                
            entry = {
                "time": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
                "lvl": record.levelname,
                "msg": msg
            }
            
            if record.exc_info:
                exc_text = logging.Formatter().formatException(record.exc_info)
                # compress traceback to save space
                if len(exc_text) > 500:
                    exc_text = exc_text[:500] + "...[truncated]"
                entry["exc"] = exc_text
                
            self.log_entries.append(entry)
            
            if len(self.log_entries) > self.capacity:
                self.log_entries = self.log_entries[-self.capacity:]
                
            self._save()
        except Exception:
            self.handleError(record)
