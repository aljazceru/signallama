# signallama

**WARNING - this is under heavy development**

Signal bot to chat with your ollama instance

## Description

Signallama is a bridge between Signal messenger and LLM models. It allows you to chat with AI models through Signal messages. While primarily designed for use with Ollama, it supports multiple LLM providers through LiteLLM, including **PrivateMode.ai** for privacy-first AI with hardware attestation.

## Requirements

- Python 3.9+
- [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) - Required for Signal messaging interface
- Ollama, PrivateMode.ai, or alternative LLM provider
- [Whisper ASR Webservice (onerahmet/openai-whisper-asr-webservice)](https://github.com/onerahmet/openai-whisper-asr-webservice) - Required for voice message transcription (see below)
- Docker and Docker Compose (required for PrivateMode.ai)

## Setup

1. Deploy [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) and set it up with your Signal account
2. Clone this repository
3. Copy `example_settings.py` to `settings.py` and configure your settings:
   - Set your Signal phone number
   - Configure your preferred LLM provider (Ollama by default)
   - Set API details for your LLM
   - (Optional) Set up Whisper ASR for voice message transcription

### Whisper ASR Webservice (Voice Transcription)

To enable transcription of voice messages, you need to run the [onerahmet/openai-whisper-asr-webservice](https://github.com/onerahmet/openai-whisper-asr-webservice) Docker image:

```bash
docker run -d --name whisper-asr -p 9000:9000 onerahmet/openai-whisper-asr-webservice:latest
```

- This will start the ASR service on port 9000 by default.
- You can access the interactive API docs at [http://localhost:9000/docs](http://localhost:9000/docs)

In your `settings.py`, set the Whisper ASR API URL:

```python
WHISPER_URL = 'http://localhost:9000'  # Whisper ASR webservice endpoint
```

If `WHISPER_URL` is set, voice messages sent to the bot will be transcribed and the transcript will be sent as a reply.

### PrivateMode.ai Setup (Privacy-First AI)

PrivateMode.ai provides hardware-attested, confidential AI inference with end-to-end encryption. To use PrivateMode.ai:

1. **Get a PrivateMode.ai API key** from [PrivateMode.ai](https://privatemode.ai/)

2. **Ensure Docker and Docker Compose are installed**:
   ```bash
   docker --version
   docker-compose --version
   ```

3. **Copy the PrivateMode docker-compose.yml** to the parent directory of signallama:
   ```bash
   # From the main privatemode directory
   cp docker-compose.yml /path/to/your/signallama/../
   ```

4. **Configure PrivateMode.ai in your `settings.py`**:
   ```python
   # === PRIVATEMODE.AI (Privacy-first LLM with hardware attestation) ===
   LLM_PROVIDER = 'privatemode'
   LLM_MODEL = 'ibnzterrell/Meta-Llama-3.3-70B-Instruct-AWQ-INT4'  # or 'latest'
   LLM_API_BASE = 'http://localhost:8080/v1'  # PrivateMode proxy endpoint
   LLM_API_KEY = 'your-privatemode-api-key'
   
   # PrivateMode-specific settings:
   PRIVATEMODE_PROXY_PORT = 8080  # Port for PrivateMode proxy
   PRIVATEMODE_VERIFY_ATTESTATION = True  # Enable hardware attestation verification
   PRIVATEMODE_AUTO_START_PROXY = True  # Automatically start proxy with docker-compose
   ```

**PrivateMode.ai Features:**
- **Hardware Attestation**: Cryptographic proof of secure execution environment
- **End-to-End Encryption**: Your messages are encrypted from Signal to AI inference
- **Zero-Knowledge**: Even PrivateMode.ai cannot access your data
- **Confidential Computing**: Processing in hardware-isolated environments
- **Automatic Proxy Management**: Signallama handles proxy startup and shutdown

## Configuration

The `settings.py` file contains all necessary configuration:

```python
# Signal API Configuration
SIGNAL_URL = 'http://localhost:8080'  # signal-cli-rest-api endpoint
SIGNAL_NUMBER = '+123456789'  # Your Signal number

# LLM Configuration
LLM_PROVIDER = 'ollama'  # or 'openai', 'anthropic', 'privatemode', etc.
LLM_MODEL = 'ollama/model-name'  # Format: provider/model
LLM_API_BASE = 'http://localhost:11434'  # Ollama API endpoint
LLM_API_KEY = None  # API key if required

# PrivateMode.ai Configuration (optional, only if using PrivateMode)
PRIVATEMODE_PROXY_PORT = 8080
PRIVATEMODE_VERIFY_ATTESTATION = True
PRIVATEMODE_AUTO_START_PROXY = True
```

## Running

```bash
python signallama.py
```

The bot will listen for messages through Signal and respond using your configured LLM.

### Running with PrivateMode.ai

When using PrivateMode.ai, you'll see additional startup logs:

```
INFO Bridge started using REST polling mode with model: ibnzterrell/Meta-Llama-3.3-70B-Instruct-AWQ-INT4
INFO Starting PrivateMode proxy...
INFO ✓ PrivateMode proxy started successfully
INFO Verifying PrivateMode attestation...
INFO ✓ PrivateMode attestation verified
INFO ✓ PrivateMode OpenAI client initialized

============================================================
PRIVATEMODE SECURITY ATTESTATION
============================================================
✓ CONFIDENTIALITY: End-to-end encryption verified
✓ INTEGRITY: Hardware-enforced isolation confirmed
✓ AUTHENTICITY: Cryptographic signatures validated
✓ VERIFIABILITY: Source code and builds reproducible
============================================================
```

This confirms that:
- Your conversations are end-to-end encrypted
- AI processing occurs in hardware-isolated environments
- The service integrity is cryptographically verified