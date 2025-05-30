import asyncio
import json
import logging
import re
import signal as py_signal
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from settings import SIGNAL_URL, SIGNAL_NUBMER, OLLAMA_URL, OLLAMA_MODEL

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Changed back to INFO now that we've debugged
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SignalOllamaBridge")

DB_FILE = Path(__file__).parent / "history.db"
MAX_HISTORY = 10  # number of turns to keep per user


def filter_think_tags(text: str) -> str:
    """Remove content between <think></think> tags from text"""
    # Remove <think>...</think> blocks (case insensitive, multiline)
    filtered = re.sub(r'<think>.*?</think>', '', text, flags=re.IGNORECASE | re.DOTALL)
    # Clean up extra whitespace
    filtered = re.sub(r'\n\s*\n\s*\n', '\n\n', filtered)  # Multiple newlines to double
    return filtered.strip()


def init_db(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.commit()
    conn.close()


class ContextManager:
    def __init__(self, db_path: Path, max_history: int = MAX_HISTORY) -> None:
        self.db_path = db_path
        self.max_history = max_history

    def add_message(self, user: str, role: str, content: str) -> None:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute(
            'INSERT INTO history (user, role, content) VALUES (?, ?, ?)',
            (user, role, content)
        )
        conn.commit()
        # prune old
        c.execute(
            '''
            DELETE FROM history
            WHERE id IN (
                SELECT id FROM history
                WHERE user = ?
                ORDER BY timestamp DESC
                LIMIT -1 OFFSET ?
            )
            ''', (user, self.max_history * 2)
        )
        conn.commit()
        conn.close()

    def get_history(self, user: str) -> List[Dict[str, str]]:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute(
            'SELECT role, content FROM history WHERE user = ? ORDER BY timestamp ASC',
            (user,)
        )
        rows = c.fetchall()
        conn.close()
        return [{'role': row[0], 'content': row[1]} for row in rows]


@dataclass
class SignalConfig:
    api_url: str
    number: str
    receive_timeout: int = 10  # seconds
    poll_interval: float = 1.0  # seconds between polls


@dataclass
class OllamaConfig:
    api_url: str
    model: str


class SignalOllamaBridge:
    def __init__(
        self,
        signal_cfg: SignalConfig,
        ollama_cfg: OllamaConfig,
        context_mgr: ContextManager
    ) -> None:
        self.signal_cfg = signal_cfg
        self.ollama_cfg = ollama_cfg
        self.context = context_mgr
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = True

    async def start(self) -> None:
        init_db(self.context.db_path)
        self.session = aiohttp.ClientSession()
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(py_signal.SIGINT, self._stop)
        loop.add_signal_handler(py_signal.SIGTERM, self._stop)
        logger.info("Bridge started using REST polling mode.")
        await self._poll_loop()

    async def _poll_loop(self) -> None:
        # Don't URL encode the number - signal-cli-rest-api expects raw number
        receive_url = f"{self.signal_cfg.api_url}/v1/receive/{self.signal_cfg.number}"
        send_url = f"{self.signal_cfg.api_url}/v2/send"
        
        while self.running:
            try:
                params = {
                    "timeout": self.signal_cfg.receive_timeout,
                    "ignore_attachments": "true",
                    "ignore_stories": "true"
                }
                async with self.session.get(receive_url, params=params) as resp:
                    resp.raise_for_status()
                    text = await resp.text()
                    
                    # Parse response - it's a JSON array
                    if not text.strip():
                        await asyncio.sleep(self.signal_cfg.poll_interval)
                        continue
                    
                    logger.debug("Raw response from signal API: %s", text[:500])
                        
                    try:
                        # Response is a JSON array of messages
                        messages = json.loads(text)
                        if not isinstance(messages, list):
                            messages = [messages]  # Handle single message case
                        logger.debug("Parsed %d messages from API", len(messages))
                    except json.JSONDecodeError as e:
                        logger.error("Failed to parse JSON response: %s", e)
                        logger.debug("Problematic response: %s", text[:200])
                        await asyncio.sleep(self.signal_cfg.poll_interval)
                        continue
                                
            except Exception as e:
                logger.error("Error receiving messages: %s", e)
                await asyncio.sleep(self.signal_cfg.poll_interval)
                continue

            for msg in messages:
                try:
                    # Skip non-dict messages
                    if not isinstance(msg, dict):
                        logger.debug("Skipping non-dict message: %s", type(msg).__name__)
                        continue
                    
                    # Extract envelope
                    envelope = msg.get('envelope', {})
                    if not envelope:
                        logger.debug("No envelope found, skipping message")
                        continue
                    
                    # Only process messages with actual content (dataMessage)
                    data_message = envelope.get('dataMessage')
                    if not data_message:
                        # Skip typing indicators and other non-content messages
                        msg_type = 'typing' if envelope.get('typingMessage') else 'other'
                        logger.debug("Skipping %s message (no dataMessage)", msg_type)
                        continue
                    
                    # Get sender info
                    author = (envelope.get('source') or 
                             envelope.get('sourceNumber') or 
                             envelope.get('sourceName'))
                    
                    # Get message content
                    body = data_message.get('message', '').strip()
                    
                    if not author or not body:
                        logger.debug("Missing author (%s) or body (%s), skipping", author, body)
                        continue
                        
                    logger.info("Received from %s: %s", author, body)
                    reply = await self._get_ai_response(body, author)

                    payload = {
                        'number': self.signal_cfg.number,
                        'recipients': [author],
                        'message': reply,
                        'text_mode': 'normal'
                    }
                    
                    try:
                        async with self.session.post(send_url, json=payload) as resp_send:
                            resp_send.raise_for_status()
                            response_data = await resp_send.json()
                            logger.info("Sent to %s (timestamp: %s)", author, response_data.get('timestamp', 'unknown'))
                    except Exception as e:
                        logger.error("Error sending to %s: %s", author, e)

                except Exception as e:
                    logger.error("Error processing message: %s", e)
                    logger.debug("Problematic message: %s", str(msg)[:200] if 'msg' in locals() else 'N/A')

            await asyncio.sleep(self.signal_cfg.poll_interval)
            
        if self.session:
            await self.session.close()

    async def _get_ai_response(self, prompt: str, user: str) -> str:
        url = f"{self.ollama_cfg.api_url}/api/generate"
        history = self.context.get_history(user)
        
        # Build context from history
        context = ""
        for msg in history:
            role = "Human" if msg['role'] == 'user' else "Assistant"
            context += f"{role}: {msg['content']}\n"
        context += f"Human: {prompt}\nAssistant:"
        
        payload = {
            'model': self.ollama_cfg.model,
            'prompt': context,
            'stream': False
        }
        
        try:
            async with self.session.post(url, json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
                
            # Ollama generate API returns response in 'response' field
            reply = data['response'].strip()
            
            # Filter out <think></think> content before saving and sending
            filtered_reply = filter_think_tags(reply)
            
            self.context.add_message(user, 'user', prompt)
            self.context.add_message(user, 'assistant', filtered_reply)
            
            logger.debug("Original reply length: %d, filtered length: %d", len(reply), len(filtered_reply))
            return filtered_reply
            
        except Exception as e:
            logger.error("Ollama API error: %s", e)
            return "Sorry, I encountered an error."

    def _stop(self) -> None:
        logger.info("Shutdown signal received.")
        self.running = False


async def main() -> None:
    signal_cfg = SignalConfig(
        api_url= SIGNAL_URL,
        number= SIGNAL_NUBMER
    )
    ollama_cfg = OllamaConfig(
        api_url= OLLAMA_URL,
        model= OLLAMA_MODEL
    )
    context_mgr = ContextManager(DB_FILE)
    bridge = SignalOllamaBridge(signal_cfg, ollama_cfg, context_mgr)
    await bridge.start()


if __name__ == '__main__':
    asyncio.run(main())