import subprocess
import logging
import os
import re

logger = logging.getLogger(__name__)

def execute_bash(command: str) -> str:
    """Executes a bash command and returns truncated output."""
    logger.info(f"Executing bash command: {command}")
    
    if re.search(r'\b(rm|mv|reboot|shutdown)\b', command):
        msg = "Error: Command execution aborted. The 'rm', 'mv', 'reboot', and 'shutdown' commands are currently restricted for safety reasons."
        logger.warning(f"Blocked dangerous command: {command}")
        return msg
        
    if "twitter post" in command:
        msg = "Error: Command execution aborted. Automated 'twitter post' commands are currently restricted for safety reasons."
        logger.warning(f"Blocked dangerous command: {command}")
        return msg
        
    env = os.environ.copy()
    local_bin = os.path.expanduser("~/.local/bin")
    if local_bin not in env.get("PATH", ""):
        env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=300,
            env=env,
            executable="/bin/bash"
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\n--- STDERR ---\n{result.stderr}"
            
        if not output.strip():
            return "Command executed successfully with no output."
            
        MAX_LEN = 4096
        if len(output) > MAX_LEN:
            half = MAX_LEN // 2
            return output[:half] + "\n\n...[TRUNCATED]...\n\n" + output[-half:]
            
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out after 300 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

BASH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_bash",
        "description": "Executes a bash command on the host machine and returns the output. Use this to interact with the system, read files, or run scripts. The user relies on you to do things for them using this. Return a summary of what you did and found.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command string to execute."
                }
            },
            "required": ["command"]
        }
    }
}

SEND_FILE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_file",
        "description": "Sends a file directly to the user's Telegram chat. Always use this to deliver generated PDFs, images, Excel sheets, or documents to the user. Provide the exact path to the file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to be sent to the user (e.g. workspace/report.pdf)."
                }
            },
            "required": ["file_path"]
        }
    }
}

ADD_CRON_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "add_cron",
        "description": "Schedules a new recurring daily task (cron) that runs at a specific time every day. Use this when the user asks to do something 'every day' or 'every morning' at a certain time.",
        "parameters": {
            "type": "object",
            "properties": {
                "time": {
                    "type": "string",
                    "description": "The daily time to execute the task in HH:MM format (24-hour clock timezone JST, e.g., '08:00', '15:30')."
                },
                "prompt": {
                    "type": "string",
                    "description": "The exact prompt/instruction that the agent will execute at that time (e.g., 'Scrape JLCPCB and send me the PDF')."
                }
            },
            "required": ["time", "prompt"]
        }
    }
}

DELETE_CRON_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "delete_cron",
        "description": "Deletes a scheduled daily cron task by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "cron_id": {
                    "type": "integer",
                    "description": "The ID of the cron task to delete."
                }
            },
            "required": ["cron_id"]
        }
    }
}

ADD_ONESHOT_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "add_oneshot",
        "description": "Schedules a one-shot (single execution) task that runs at a specific date and time in the future. This tool is primarily used as a REMINDER system for the user. Use this proactively whenever the user asks to be reminded of something, to remember something (覚えて), or to do something once at a later time (e.g., 'remind me in 5 minutes', 'do this on April 6th morning').",
        "parameters": {
            "type": "object",
            "properties": {
                "datetime": {
                    "type": "string",
                    "description": "The exact date and time to execute the task in YYYY-MM-DD HH:MM format (timezone JST, e.g., '2026-04-06 08:00', '2026-03-22 17:45')."
                },
                "prompt": {
                    "type": "string",
                    "description": "The exact prompt/instruction that the agent will execute at that time."
                }
            },
            "required": ["datetime", "prompt"]
        }
    }
}

DELETE_ONESHOT_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "delete_oneshot",
        "description": "Deletes a scheduled one-shot task by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "oneshot_id": {
                    "type": "integer",
                    "description": "The ID of the one-shot task to delete."
                }
            },
            "required": ["oneshot_id"]
        }
    }
}
