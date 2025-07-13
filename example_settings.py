# Signal API Configuration
SIGNAL_URL = 'http://localhost:8080'  # Your signal-cli-rest-api port
SIGNAL_NUMBER = '+123456789'  # Your Signal number

# LLM Configuration using LiteLLM
# LiteLLM supports many providers - uncomment the configuration for your preferred provider

# === OLLAMA (Local) ===
LLM_PROVIDER = 'ollama'
LLM_MODEL = 'ollama/qwen2.5:7b'  # Format: provider/model
LLM_API_BASE = 'http://localhost:11434'
LLM_API_KEY = None  # Not needed for Ollama

# === OPENAI ===
# LLM_PROVIDER = 'openai'
# LLM_MODEL = 'gpt-4o-mini'  # or 'gpt-4', 'gpt-3.5-turbo', etc.
# LLM_API_BASE = None  # Uses default OpenAI endpoint
# LLM_API_KEY = 'sk-your-openai-api-key-here'

# === ANTHROPIC ===
# LLM_PROVIDER = 'anthropic'
# LLM_MODEL = 'claude-3-5-sonnet-20241022'  # or 'claude-3-haiku-20240307', etc.
# LLM_API_BASE = None  # Uses default Anthropic endpoint
# LLM_API_KEY = 'your-anthropic-api-key-here'

# === OPENAI-COMPATIBLE (e.g., vLLM, LocalAI, etc.) ===
# LLM_PROVIDER = 'openai'
# LLM_MODEL = 'your-model-name'
# LLM_API_BASE = 'http://localhost:8000/v1'  # Your custom endpoint
# LLM_API_KEY = 'not-needed'  # Or your custom API key

# === TOGETHER AI ===
# LLM_PROVIDER = 'together_ai'
# LLM_MODEL = 'together_ai/mistralai/Mixtral-8x7B-Instruct-v0.1'
# LLM_API_BASE = None
# LLM_API_KEY = 'your-together-api-key'

# === GROQ ===
# LLM_PROVIDER = 'groq'
# LLM_MODEL = 'groq/llama2-70b-4096'
# LLM_API_BASE = None
# LLM_API_KEY = 'your-groq-api-key'

# === COHERE ===
# LLM_PROVIDER = 'cohere'
# LLM_MODEL = 'command-r-plus'
# LLM_API_BASE = None
# LLM_API_KEY = 'your-cohere-api-key'

# === AZURE OPENAI ===
# LLM_PROVIDER = 'azure'
# LLM_MODEL = 'azure/your-deployment-name'
# LLM_API_BASE = 'https://your-resource.openai.azure.com'
# LLM_API_KEY = 'your-azure-api-key'
# 
# Additional Azure-specific environment variables you may need to set:
# import os
# os.environ['AZURE_API_VERSION'] = '2023-12-01-preview'

# === HUGGING FACE ===
# LLM_PROVIDER = 'huggingface'
# LLM_MODEL = 'huggingface/microsoft/DialoGPT-medium'
# LLM_API_BASE = None
# LLM_API_KEY = 'your-huggingface-api-key'

# === GOOGLE GEMINI ===
# LLM_PROVIDER = 'gemini'
# LLM_MODEL = 'gemini/gemini-pro'
# LLM_API_BASE = None
# LLM_API_KEY = 'your-google-api-key'

# === PERPLEXITY ===
# LLM_PROVIDER = 'perplexity'
# LLM_MODEL = 'perplexity/llama-3.1-sonar-large-128k-online'
# LLM_API_BASE = None
# LLM_API_KEY = 'your-perplexity-api-key'

# === ANYSCALE ===
# LLM_PROVIDER = 'anyscale'
# LLM_MODEL = 'anyscale/meta-llama/Llama-2-7b-chat-hf'
# LLM_API_BASE = None
# LLM_API_KEY = 'your-anyscale-api-key'

# === DEEPINFRA ===
# LLM_PROVIDER = 'deepinfra'
# LLM_MODEL = 'deepinfra/meta-llama/Llama-2-70b-chat-hf'
# LLM_API_BASE = None
# LLM_API_KEY = 'your-deepinfra-api-key'

# === REPLICATE ===
# LLM_PROVIDER = 'replicate'
# LLM_MODEL = 'replicate/meta/llama-2-70b-chat:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3'
# LLM_API_BASE = None
# LLM_API_KEY = 'your-replicate-api-key'

# === PRIVATEMODE.AI (Privacy-first LLM with hardware attestation) ===
# LLM_PROVIDER = 'privatemode'
# LLM_MODEL = 'ibnzterrell/Meta-Llama-3.3-70B-Instruct-AWQ-INT4'  # or 'latest'
# LLM_API_BASE = 'http://localhost:8080/v1'  # PrivateMode proxy endpoint
# LLM_API_KEY = 'your-privatemode-api-key'
# 
# PrivateMode-specific settings:
# PRIVATEMODE_PROXY_PORT = 8080  # Port for PrivateMode proxy
# PRIVATEMODE_VERIFY_ATTESTATION = True  # Enable hardware attestation verification
# PRIVATEMODE_AUTO_START_PROXY = True  # Automatically start proxy with docker-compose

# Note: For complete list of supported providers and models, see:
# https://docs.litellm.ai/docs/providers

# === WHISPER ASR CONFIGURATION ===
# Optional: Set WHISPER_URL for voice message transcription
# If not set, voice messages will not be transcribed
WHISPER_URL = None  # Example: 'http://localhost:9000'

# === PRIVATEMODE.AI CONFIGURATION (Optional) ===
# These settings are only used when LLM_PROVIDER = 'privatemode'
# If not using PrivateMode, these can be ignored

# PrivateMode proxy port (default: 8080)
PRIVATEMODE_PROXY_PORT = 8080

# Enable hardware attestation verification (default: True)
PRIVATEMODE_VERIFY_ATTESTATION = True

# Automatically start PrivateMode proxy with docker-compose (default: True)
PRIVATEMODE_AUTO_START_PROXY = True

# PrivateMode docker-compose file path (relative to signallama directory)
PRIVATEMODE_COMPOSE_FILE = '../docker-compose.yml'