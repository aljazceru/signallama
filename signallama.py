import asyncio
import json
import logging
import re
import signal as py_signal
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from settings import SIGNAL_URL, SIGNAL_NUMBER, LLM_MODEL, LLM_API_BASE, LLM_API_KEY, LLM_PROVIDER, WHISPER_URL

import aiohttp
import litellm
import tempfile
import os

# Required packages:
# pip install litellm aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SignalLLMBridge")

# Configure LiteLLM
litellm.set_verbose = False  # Set to True for debugging

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
class LLMConfig:
    model: str
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    provider: Optional[str] = None


@dataclass
class WhisperConfig:
    api_url: str
    enabled: bool = True


class SignalLLMBridge:
    def __init__(
        self,
        signal_cfg: SignalConfig,
        llm_cfg: LLMConfig,
        whisper_cfg: WhisperConfig,
        context_mgr: ContextManager
    ) -> None:
        self.signal_cfg = signal_cfg
        self.llm_cfg = llm_cfg
        self.whisper_cfg = whisper_cfg
        self.context = context_mgr
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = True
        
        # Configure LiteLLM settings
        if llm_cfg.api_base:
            litellm.api_base = llm_cfg.api_base
        if llm_cfg.api_key:
            litellm.api_key = llm_cfg.api_key

    async def start(self) -> None:
        init_db(self.context.db_path)
        self.session = aiohttp.ClientSession()
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(py_signal.SIGINT, self._stop)
        loop.add_signal_handler(py_signal.SIGTERM, self._stop)
        logger.info("Bridge started using REST polling mode with model: %s (Whisper: %s)", 
                   self.llm_cfg.model, 
                   "enabled" if self.whisper_cfg.enabled else "disabled")
        await self._poll_loop()

    async def _poll_loop(self) -> None:
        # Don't URL encode the number - signal-cli-rest-api expects raw number
        receive_url = f"{self.signal_cfg.api_url}/v1/receive/{self.signal_cfg.number}"
        send_url = f"{self.signal_cfg.api_url}/v2/send"
        
        while self.running:
            try:
                params = {
                    "timeout": self.signal_cfg.receive_timeout,
                    "ignore_attachments": "false",
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
                    body = (data_message.get('message') or '').strip()
                    
                    if not author:
                        logger.debug("Missing author, skipping message")
                        continue
                    
                    # Check if this is a voice message
                    if self._is_voice_message(data_message):
                        try:
                            handled = await self._process_voice_message(data_message, author)
                            if handled:
                                continue
                        except Exception as e:
                            logger.error("Error processing voice message from %s: %s", author, e)
                            await self._send_reply(author, "Sorry, I encountered an error processing your voice message.")
                            continue
                    
                    # Handle regular text messages
                    if not body:
                        logger.debug("No text content in message, skipping")
                        continue
                        
                    logger.info("Received from %s: %s", author, body)
                    reply = await self._get_ai_response(body, author)
                    await self._send_reply(author, reply)

                except Exception as e:
                    logger.error("Error processing message: %s", e)
                    logger.debug("Problematic message: %s", str(msg)[:200] if 'msg' in locals() else 'N/A')

            await asyncio.sleep(self.signal_cfg.poll_interval)
            
        if self.session:
            await self.session.close()

    def _is_voice_message(self, data_message: Dict[str, Any]) -> bool:
        """Check if message contains voice attachments"""
        attachments = data_message.get('attachments', [])
        if not attachments:
            return False
        
        voice_mime_types = [
            'audio/aac',
            'audio/mp4',
            'audio/mpeg',
            'audio/ogg',
            'audio/wav',
            'audio/webm',
            'audio/3gpp',
            'audio/amr'
        ]
        
        for attachment in attachments:
            content_type = attachment.get('contentType', '').lower()
            if content_type in voice_mime_types:
                return True
        return False

    async def _download_attachment(self, attachment_id: str) -> Optional[bytes]:
        """Download attachment from Signal API"""
        try:
            download_url = f"{self.signal_cfg.api_url}/v1/attachments/{attachment_id}"
            async with self.session.get(download_url) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    logger.error("Failed to download attachment %s: HTTP %d", attachment_id, resp.status)
                    return None
        except Exception as e:
            logger.error("Error downloading attachment %s: %s", attachment_id, e)
            return None

    async def _transcribe_audio(self, audio_data: bytes, filename: str = "audio.ogg") -> Optional[str]:
        """Transcribe audio using the new /asr endpoint"""
        if not self.whisper_cfg.enabled:
            return None
        
        try:
            # Create temporary file for audio data
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # Prepare multipart form data for /asr endpoint
                with open(temp_file_path, 'rb') as audio_file:
                    form_data = aiohttp.FormData()
                    form_data.add_field('audio_file', audio_file, filename=filename)
                    # You can add more fields here if needed (e.g., task, language, etc.)
                    asr_url = f"{self.whisper_cfg.api_url}/asr?output=json"
                    try:
                        async with self.session.post(asr_url, data=form_data) as resp:
                            response_text = await resp.text()
                            if resp.status == 200:
                                try:
                                    result = json.loads(response_text)
                                    logger.info("ASR API 200 response JSON: %s", result)
                                    return result.get('text', '').strip()
                                except Exception as parse_exc:
                                    logger.error("Failed to parse ASR API JSON response: %s", parse_exc, exc_info=True)
                                    logger.error("Raw response text: %s", response_text)
                                    return None
                            else:
                                logger.error("ASR transcription failed: HTTP %d - %s", resp.status, response_text)
                                return None
                    except aiohttp.ClientConnectorError:
                        logger.error("Cannot connect to ASR service at %s - is it running?", self.whisper_cfg.api_url, exc_info=True)
                        return None
                    except asyncio.TimeoutError:
                        logger.error("ASR transcription timed out", exc_info=True)
                        return None
                    except aiohttp.ClientError as e:
                        logger.error("Aiohttp client error: %s", e, exc_info=True)
                        return None
                    except Exception as e:
                        logger.error("Unexpected error during ASR transcription: %s", e, exc_info=True)
                        return None
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass
        except Exception as e:
            logger.error("Error transcribing audio: %s", e)
            return None

    async def _process_voice_message(self, data_message: Dict[str, Any], author: str) -> bool:
        """Process voice message and send transcription. Returns True if handled."""
        attachments = data_message.get('attachments', [])
        
        for attachment in attachments:
            content_type = attachment.get('contentType', '').lower()
            attachment_id = attachment.get('id')
            
            if not attachment_id:
                continue
                
            voice_mime_types = [
                'audio/aac', 'audio/mp4', 'audio/mpeg', 'audio/ogg', 
                'audio/wav', 'audio/webm', 'audio/3gpp', 'audio/amr'
            ]
            
            if content_type in voice_mime_types:
                logger.info("Processing voice message from %s (type: %s)", author, content_type)
                
                # Download the audio file
                audio_data = await self._download_attachment(attachment_id)
                if not audio_data:
                    await self._send_reply(author, "Sorry, I couldn't download your voice message.")
                    return True
                
                # Transcribe the audio
                filename = f"voice_message.{content_type.split('/')[-1]}"
                transcription = await self._transcribe_audio(audio_data, filename)
                
                if transcription:
                    reply = f"Voice message transcription:\n\n{transcription}"
                    logger.info("Transcribed voice message from %s: %s", author, transcription)
                else:
                    reply = "Sorry, I couldn't transcribe your voice message."
                    
                await self._send_reply(author, reply)
                return True
        
        return False

    async def _send_reply(self, recipient: str, message: str) -> None:
        """Send a reply message"""
        send_url = f"{self.signal_cfg.api_url}/v2/send"
        payload = {
            'number': self.signal_cfg.number,
            'recipients': [recipient],
            'message': message,
            'text_mode': 'normal'
        }
        
        try:
            async with self.session.post(send_url, json=payload) as resp_send:
                resp_send.raise_for_status()
                response_data = await resp_send.json()
                logger.info("Sent to %s (timestamp: %s)", recipient, response_data.get('timestamp', 'unknown'))
        except Exception as e:
            logger.error("Error sending to %s: %s", recipient, e)

    async def _get_ai_response(self, prompt: str, user: str) -> str:
        history = self.context.get_history(user)
        
        # Build messages in OpenAI format for LiteLLM
        messages = []
        
        # Add conversation history
        for msg in history:
            messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        # Add current user message
        messages.append({
            'role': 'user',
            'content': prompt
        })
        
        try:
            # Use LiteLLM async completion
            response = await litellm.acompletion(
                model=self.llm_cfg.model,
                messages=messages,
                api_base=self.llm_cfg.api_base,
                api_key=self.llm_cfg.api_key
            )
            
            # Extract reply from LiteLLM response
            reply = response.choices[0].message.content.strip()
            
            # Filter out <think></think> content before saving and sending
            filtered_reply = filter_think_tags(reply)
            
            self.context.add_message(user, 'user', prompt)
            self.context.add_message(user, 'assistant', filtered_reply)
            
            logger.debug("Original reply length: %d, filtered length: %d", len(reply), len(filtered_reply))
            return filtered_reply
            
        except Exception as e:
            logger.error("LLM API error: %s", e)
            return "Sorry, I encountered an error processing your request."

    def _stop(self) -> None:
        logger.info("Shutdown signal received.")
        self.running = False


async def main() -> None:
    signal_cfg = SignalConfig(
        api_url=SIGNAL_URL,
        number=SIGNAL_NUMBER
    )
    llm_cfg = LLMConfig(
        model=LLM_MODEL,
        api_base=LLM_API_BASE,
        api_key=LLM_API_KEY,
        provider=LLM_PROVIDER
    )
    whisper_cfg = WhisperConfig(
        api_url=WHISPER_URL,
        enabled=bool(WHISPER_URL)  # Enable if URL is provided
    )
    context_mgr = ContextManager(DB_FILE)
    bridge = SignalLLMBridge(signal_cfg, llm_cfg, whisper_cfg, context_mgr)
    await bridge.start()


if __name__ == '__main__':
    asyncio.run(main())
