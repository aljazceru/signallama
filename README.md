# signallama

**WARNING - this is under heavy development**

Signal bot to chat with your ollama instance

## Description

Signallama is a bridge between Signal messenger and LLM models. It allows you to chat with AI models through Signal messages. While primarily designed for use with Ollama, it supports multiple LLM providers through LiteLLM.

## Requirements

- Python 3.8+
- [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) - Required for Signal messaging interface
- Ollama or alternative LLM provider
- [Whisper ASR Webservice (onerahmet/openai-whisper-asr-webservice)](https://github.com/onerahmet/openai-whisper-asr-webservice) - Required for voice message transcription (see below)

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

## Configuration

The `settings.py` file contains all necessary configuration:

```python
# Signal API Configuration
SIGNAL_URL = 'http://localhost:8080'  # signal-cli-rest-api endpoint
SIGNAL_NUMBER = '+123456789'  # Your Signal number

# LLM Configuration
LLM_PROVIDER = 'ollama'  # or 'openai', 'anthropic', etc.
LLM_MODEL = 'ollama/model-name'  # Format: provider/model
LLM_API_BASE = 'http://localhost:11434'  # Ollama API endpoint
LLM_API_KEY = None  # API key if required
```

## Running

```bash
python signallama.py
```

The bot will listen for messages through Signal and respond using your configured LLM.