# signallama

Signal bot to chat with your ollama instance

## Description

Signallama is a bridge between Signal messenger and LLM models. It allows you to chat with AI models through Signal messages. While primarily designed for use with Ollama, it supports multiple LLM providers through LiteLLM.

## Requirements

- Python 3.8+
- [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) - Required for Signal messaging interface
- Ollama or alternative LLM provider

## Setup

1. Deploy [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) and set it up with your Signal account
2. Clone this repository
3. Copy `example_settings.py` to `settings.py` and configure your settings:
   - Set your Signal phone number
   - Configure your preferred LLM provider (Ollama by default)
   - Set API details for your LLM

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