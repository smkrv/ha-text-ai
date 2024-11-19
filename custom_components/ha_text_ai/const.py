"""Constants for the HA text AI integration."""
from typing import Final
from homeassistant.const import Platform

# Domain
DOMAIN: Final = "ha_text_ai"
PLATFORMS: Final = [Platform.SENSOR]

# Configuration constants
CONF_MODEL: Final = "model"
CONF_TEMPERATURE: Final = "temperature"
CONF_MAX_TOKENS: Final = "max_tokens"
CONF_API_ENDPOINT: Final = "api_endpoint"
CONF_REQUEST_INTERVAL: Final = "request_interval"

# Default values
DEFAULT_MODEL: Final = "gpt-3.5-turbo"
DEFAULT_TEMPERATURE: Final = 0.7
DEFAULT_MAX_TOKENS: Final = 1000
DEFAULT_API_ENDPOINT: Final = "https://api.openai.com/v1"
DEFAULT_REQUEST_INTERVAL: Final = 1.0

# Parameter constraints
MIN_TEMPERATURE: Final = 0.0
MAX_TEMPERATURE: Final = 2.0
MIN_MAX_TOKENS: Final = 1
MAX_MAX_TOKENS: Final = 4096
MIN_REQUEST_INTERVAL: Final = 0.1

# Service names
SERVICE_ASK_QUESTION: Final = "ask_question"
SERVICE_CLEAR_HISTORY: Final = "clear_history"
SERVICE_GET_HISTORY: Final = "get_history"
SERVICE_SET_SYSTEM_PROMPT: Final = "set_system_prompt"

# Service descriptions
SERVICE_ASK_QUESTION_DESCRIPTION: Final = "Ask a question to the AI model"
SERVICE_CLEAR_HISTORY_DESCRIPTION: Final = "Clear conversation history"
SERVICE_GET_HISTORY_DESCRIPTION: Final = "Get conversation history"
SERVICE_SET_SYSTEM_PROMPT_DESCRIPTION: Final = "Set system prompt for AI model"

# Attribute keys
ATTR_QUESTION: Final = "question"
ATTR_RESPONSE: Final = "response"
ATTR_LAST_UPDATED: Final = "last_updated"
ATTR_MODEL: Final = "model"
ATTR_TEMPERATURE: Final = "temperature"
ATTR_MAX_TOKENS: Final = "max_tokens"
ATTR_TOTAL_RESPONSES: Final = "total_responses"
ATTR_SYSTEM_PROMPT: Final = "system_prompt"
ATTR_RESPONSE_TIME: Final = "response_time"

# Error messages
ERROR_INVALID_API_KEY: Final = "invalid_api_key"
ERROR_CANNOT_CONNECT: Final = "cannot_connect"
ERROR_UNKNOWN: Final = "unknown_error"
ERROR_INVALID_MODEL: Final = "invalid_model"
ERROR_RATE_LIMIT: Final = "rate_limit_exceeded"
ERROR_CONTEXT_LENGTH: Final = "context_length_exceeded"
ERROR_API_ERROR: Final = "api_error"

# Configuration descriptions
CONF_MODEL_DESCRIPTION: Final = "AI model to use for responses"
CONF_TEMPERATURE_DESCRIPTION: Final = "Temperature for response generation (0-2)"
CONF_MAX_TOKENS_DESCRIPTION: Final = "Maximum tokens in response (1-4096)"
CONF_API_ENDPOINT_DESCRIPTION: Final = "API endpoint URL"
CONF_REQUEST_INTERVAL_DESCRIPTION: Final = "Minimum time between API requests (seconds)"

# Entity attributes descriptions
ATTR_QUESTION_DESCRIPTION: Final = "Last question asked"
ATTR_RESPONSE_DESCRIPTION: Final = "Last response received"
ATTR_LAST_UPDATED_DESCRIPTION: Final = "Time of last update"
ATTR_MODEL_DESCRIPTION: Final = "Current AI model in use"
ATTR_TEMPERATURE_DESCRIPTION: Final = "Current temperature setting"
ATTR_MAX_TOKENS_DESCRIPTION: Final = "Current max tokens setting"
ATTR_TOTAL_RESPONSES_DESCRIPTION: Final = "Total number of responses"
ATTR_SYSTEM_PROMPT_DESCRIPTION: Final = "Current system prompt"
ATTR_RESPONSE_TIME_DESCRIPTION: Final = "Time taken for last response"

# Entity attributes
ENTITY_NAME: Final = "HA Text AI"
ENTITY_ICON: Final = "mdi:robot"

# Translation keys
TRANSLATION_KEY_CONFIG: Final = "config"
TRANSLATION_KEY_OPTIONS: Final = "options"
TRANSLATION_KEY_ERROR: Final = "error"

# State attributes
STATE_READY: Final = "ready"
STATE_PROCESSING: Final = "processing"
STATE_ERROR: Final = "error"
