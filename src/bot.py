import logging
import telebot
import json
import threading
from src.config import TELEGRAM_KEY
from src.state import (
    clear_history, add_message, get_history, remove_last_message, 
    set_abort_flag, get_abort_flag, get_user_queue, enqueue_task, 
    get_all_tasks, cancel_task, active_tasks, get_all_crons, add_cron, delete_cron
)
import time
from datetime import datetime
from src.llm import get_ai_response
from src.tools import execute_bash

logger = logging.getLogger(__name__)

user_workers = {}

def create_bot():
    logger.info("Initializing Telegram bot instance...")
    bot = telebot.TeleBot(TELEGRAM_KEY)

    def worker_loop(user_id, bot_instance):
        q = get_user_queue(user_id)
        while True:
            task = q.get()
            if task is None: 
                break
            
            task["status"] = "running"
            active_tasks[user_id] = task
            set_abort_flag(user_id, False)
            
            logger.info(f"Worker started task #{task['id']} for user_id={user_id}")
            
            try:
                # We execute the task context sharing serially here instead of at the handler
                add_message(user_id, {"role": "user", "content": task["text"]})
                
                final_text = ""
                
                # Agent loop logic (Suppressing intermediate messages on Telegram)
                step_count = 0
                max_steps = 128
                
                while True:
                    step_count += 1
                    if step_count > max_steps:
                        final_text = f"🛑 Task #{task['id']} reached the maximum limit of {max_steps} steps. Aborting to prevent infinite loop."
                        break
                        
                    if get_abort_flag(user_id):
                        final_text = f"🛑 Task #{task['id']} was aborted."
                        break

                    messages = get_history(user_id)
                    assistant_message = get_ai_response(messages)
                    
                    msg_dict = assistant_message.model_dump(exclude_unset=True, exclude_none=True)
                    if hasattr(assistant_message, 'reasoning_details') and assistant_message.reasoning_details is not None:
                        msg_dict["reasoning_details"] = assistant_message.reasoning_details
                        
                    if assistant_message.content:
                        final_text = assistant_message.content # Always store latest text as final output
                    
                    add_message(user_id, msg_dict)
                    
                    if not assistant_message.tool_calls:
                        # Finished tools
                        break
                    
                    for tool_call in assistant_message.tool_calls:
                        if tool_call.function.name == "execute_bash":
                            try:
                                args = json.loads(tool_call.function.arguments)
                                cmd = args.get("command", "")
                                
                                task["last_action"] = f"bash: {cmd[:30]}"
                                active_tasks[user_id] = task
                                
                                logger.info(f"Task #{task['id']} execute_bash: {cmd}")
                                output = execute_bash(cmd)
                                
                                # Log formatting for /logs command
                                log_entry = f"> bash: `{cmd[:60]}`...\n```\n{output[:200]}...\n```"
                                task.setdefault("logs", []).append(log_entry)
                                
                                add_message(user_id, {"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": output})
                            except Exception as e:
                                add_message(user_id, {"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": f"Execute failed: {str(e)}"})
                                
                        elif tool_call.function.name == "send_file":
                            try:
                                import os
                                args = json.loads(tool_call.function.arguments)
                                file_path = args.get("file_path", "")
                                
                                task["last_action"] = f"send_file: {file_path[:20]}"
                                active_tasks[user_id] = task
                                
                                logger.info(f"Task #{task['id']} send_file: {file_path}")
                                
                                if os.path.exists(file_path):
                                    with open(file_path, "rb") as doc:
                                        bot_instance.send_document(user_id, doc)
                                    output = f"Successfully sent file to user: {file_path}"
                                    task.setdefault("logs", []).append(f"> send_file: `{file_path}`\n(Success)")
                                else:
                                    output = f"Error: File does not exist: {file_path}"
                                    task.setdefault("logs", []).append(f"> send_file: `{file_path}`\n(Error: Not Found)")
                                    
                                add_message(user_id, {"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": output})
                            except Exception as e:
                                add_message(user_id, {"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": f"Send file failed: {str(e)}"})

                        elif tool_call.function.name == "add_cron":
                            try:
                                args = json.loads(tool_call.function.arguments)
                                time_str = args.get("time", "")
                                prompt = args.get("prompt", "")
                                
                                task["last_action"] = f"add_cron ({time_str})"
                                active_tasks[user_id] = task
                                
                                c = add_cron(user_id, time_str, prompt)
                                output = f"Successfully added cron #{c['id']} at {time_str} for prompt: {prompt}"
                                logger.info(output)
                                task.setdefault("logs", []).append(f"> add_cron {time_str} -> {prompt[:20]}...\n(Success)")
                                
                                add_message(user_id, {"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": output})
                            except Exception as e:
                                add_message(user_id, {"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": f"Add cron failed: {str(e)}"})
                                
                        elif tool_call.function.name == "delete_cron":
                            try:
                                args = json.loads(tool_call.function.arguments)
                                cron_id = args.get("cron_id")
                                
                                task["last_action"] = f"delete_cron #{cron_id}"
                                active_tasks[user_id] = task
                                
                                if delete_cron(user_id, cron_id):
                                    output = f"Successfully deleted cron #{cron_id}"
                                    task.setdefault("logs", []).append(f"> delete_cron #{cron_id}\n(Success)")
                                else:
                                    output = f"Error: Cron #{cron_id} not found or you don't own it."
                                    task.setdefault("logs", []).append(f"> delete_cron #{cron_id}\n(Error)")
                                    
                                logger.info(output)
                                add_message(user_id, {"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": output})
                            except Exception as e:
                                add_message(user_id, {"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": f"Delete cron failed: {str(e)}"})

                # Finish Task
                if final_text:
                    base_header = f"✅ [Task #{task['id']} Finished]\n\n"
                    chunks = [final_text[i:i+4000] for i in range(0, len(final_text), 4000)]
                    
                    for i, chunk in enumerate(chunks):
                        try:
                            if i == 0:
                                bot_instance.send_message(user_id, f"✅ *[Task #{task['id']} Finished]*\n\n{chunk}", parse_mode='Markdown')
                            else:
                                bot_instance.send_message(user_id, chunk)
                        except telebot.apihelper.ApiTelegramException:
                            if i == 0:
                                bot_instance.send_message(user_id, base_header + chunk)
                            else:
                                bot_instance.send_message(user_id, chunk)
                else:
                    bot_instance.send_message(user_id, f"✅ *[Task #{task['id']} Finished]* with no final response.", parse_mode='Markdown')

            except Exception as e:
                logger.error(f"Worker error for user_id={user_id}: {e}", exc_info=True)
                try:
                    bot_instance.send_message(user_id, f"❌ *[Task #{task['id']} Failed]*\n{str(e)}", parse_mode='Markdown')
                except telebot.apihelper.ApiTelegramException:
                    bot_instance.send_message(user_id, f"❌ [Task #{task['id']} Failed]\n{str(e)}")
                if len(get_history(user_id)) > 0:
                    remove_last_message(user_id)
            finally:
                active_tasks.pop(user_id, None)
                set_abort_flag(user_id, False)
                q.task_done()

    def start_worker_if_needed(user_id):
        if user_id not in user_workers or not user_workers[user_id].is_alive():
            t = threading.Thread(target=worker_loop, args=(user_id, bot), daemon=True)
            user_workers[user_id] = t
            t.start()

    def cron_checker_loop():
        # Dedicated thread to trigger cron tasks
        last_triggered_minute = None
        while True:
            now = datetime.now()
            current_min_str = now.strftime("%Y-%m-%d %H:%M")
            
            if last_triggered_minute != current_min_str:
                last_triggered_minute = current_min_str
                current_time_str = now.strftime("%H:%M")
                
                crons = get_all_crons()
                for c in crons:
                    if c.get("time") == current_time_str:
                        user_id = c["user_id"]
                        logger.info(f"Triggering cron #{c['id']} for user {user_id}")
                        prompt = f"[Cron Triggered Automatically] The scheduled time {current_time_str} has arrived. Please execute this instructional task immediately and report the results: {c['prompt']}"
                        task = enqueue_task(user_id, prompt)
                        try:
                            bot.send_message(user_id, f"⏰ *[Cron Triggered]* Started scheduled task #{task['id']} for {current_time_str}.", parse_mode='Markdown')
                        except telebot.apihelper.ApiTelegramException:
                            pass
                        start_worker_if_needed(user_id)
            
            time.sleep(10)
            
    threading.Thread(target=cron_checker_loop, daemon=True).start()

    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        logger.info(f"Received /{message.text.lstrip('/')} command from user_id={message.from_user.id}")
        bot.reply_to(message, "Hello! I am JumangoClaw, an async AI bot powered by OpenRouter.\nSend me a message to start a background task!\n\nCommands:\n/tasks - View active tasks\n/stop <ID> - Abort a task\n/new - Reset conversation memory")

    @bot.message_handler(commands=['new'])
    def handle_new(message):
        user_id = message.from_user.id
        logger.info(f"Received /new command from user_id={user_id}")
        clear_history(user_id)
        bot.reply_to(message, "Conversation history and queue reset. Starting a new session!")

    @bot.message_handler(commands=['logs'])
    def handle_logs(message):
        user_id = message.from_user.id
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: `/logs <task_id>`", parse_mode='Markdown')
            return
            
        try:
            task_id = int(parts[1])
        except ValueError:
            bot.reply_to(message, "Task ID must be a number.")
            return
            
        tasks = get_all_tasks(user_id)
        target_task = next((t for t in tasks if t["id"] == task_id), None)
        
        if not target_task:
            bot.reply_to(message, f"⚠️ Task #{task_id} not found in active or queued tasks.")
            return
            
        logs = target_task.get("logs", [])
        if not logs:
            bot.reply_to(message, f"📜 *[Task #{task_id} Logs]*\nNo tools executed yet.", parse_mode='Markdown')
            return
            
        log_text = f"📜 *[Task #{task_id} Logs (Last 10 steps)]*\n\n" + "\n\n".join(logs[-10:])
        try:
            bot.reply_to(message, log_text, parse_mode='Markdown')
        except telebot.apihelper.ApiTelegramException:
            bot.reply_to(message, log_text)

    @bot.message_handler(commands=['crons'])
    def handle_crons(message):
        user_id = message.from_user.id
        crons = get_all_crons()
        user_crons = [c for c in crons if c["user_id"] == user_id]
        
        if not user_crons:
            bot.reply_to(message, "No active cron tasks.", parse_mode='Markdown')
            return
            
        lines = [f"`#{c['id']}` : 🕒 `{c['time']}` -> {c['prompt']}" for c in user_crons]
        try:
            bot.reply_to(message, "⏰ *Scheduled Daily Tasks*\n" + "\n".join(lines), parse_mode='Markdown')
        except telebot.apihelper.ApiTelegramException:
            bot.reply_to(message, "⏰ Scheduled Daily Tasks\n" + "\n".join(lines))

    @bot.message_handler(commands=['tasks'])
    def handle_tasks(message):
        user_id = message.from_user.id
        tasks = get_all_tasks(user_id)
        if not tasks:
            bot.reply_to(message, "No active or queued tasks.")
            return
            
        lines = []
        for t in tasks:
            status = "🏃 Running" if t["status"] == "running" else "⏳ Queued"
            action = f" ({t.get('last_action', 'Thinking...')})" if t["status"] == "running" else ""
            lines.append(f"`#{t['id']}` : {t['name']} [{status}]{action}")
            
        try:
            bot.reply_to(message, "📋 *Current Tasks*\n" + "\n".join(lines), parse_mode='Markdown')
        except telebot.apihelper.ApiTelegramException:
            bot.reply_to(message, "📋 Current Tasks\n" + "\n".join(lines))

    @bot.message_handler(commands=['stop'])
    def handle_stop(message):
        user_id = message.from_user.id
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: `/stop <task_id>`\nUse `/tasks` to see task IDs.", parse_mode='Markdown')
            return
            
        try:
            task_id = int(parts[1])
        except ValueError:
            bot.reply_to(message, "Task ID must be a number.")
            return
            
        res = cancel_task(user_id, task_id)
        if res == "running":
            bot.reply_to(message, f"🛑 Stop request sent to running Task #{task_id}. It will abort shortly.")
        elif res == "queued":
            bot.reply_to(message, f"🗑️ Queued Task #{task_id} has been removed.")
        else:
            bot.reply_to(message, f"⚠️ Task #{task_id} not found in running or queued list.")

    @bot.message_handler(func=lambda m: True)
    def chat_with_ai(message):
        user_id = message.from_user.id
        user_input = message.text or message.caption or ""
        
        # If the user is specifically replying to a previous message, append that context
        reply = message.reply_to_message
        if reply:
            reply_text = reply.text or reply.caption or "[File/Media without text]"
            if len(reply_text) > 1024:
                reply_text = reply_text[:1024] + "... [truncated]"
            user_input = f'[Context: User is replying directly to the following past message: "{reply_text}"]\n\n{user_input}'
        
        task = enqueue_task(user_id, user_input)
        try:
            bot.reply_to(message, f"📥 *[Task #{task['id']} Queued]*\nTask added to background queue.", parse_mode='Markdown')
        except telebot.apihelper.ApiTelegramException:
            bot.reply_to(message, f"📥 [Task #{task['id']} Queued]\nTask added to background queue.")
        start_worker_if_needed(user_id)

    return bot

