"""Constants for the HA text AI integration."""
from typing import Final
from homeassistant.const import Platform

# Domain and platforms
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
DEFAULT_TIMEOUT: Final = 30
DEFAULT_QUEUE_SIZE: Final = 100
DEFAULT_HISTORY_LIMIT: Final = 50

# Parameter constraints
MIN_TEMPERATURE: Final = 0.0
MAX_TEMPERATURE: Final = 2.0
MIN_MAX_TOKENS: Final = 1
MAX_MAX_TOKENS: Final = 4096
MIN_REQUEST_INTERVAL: Final = 0.1
MIN_TIMEOUT: Final = 5
MAX_TIMEOUT: Final = 120

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
ATTR_QUEUE_SIZE: Final = "queue_size"
ATTR_API_STATUS: Final = "api_status"
ATTR_ERROR_COUNT: Final = "error_count"
ATTR_LAST_ERROR: Final = "last_error"

# Error messages
ERROR_INVALID_API_KEY: Final = "invalid_api_key"
ERROR_CANNOT_CONNECT: Final = "cannot_connect"
ERROR_UNKNOWN: Final = "unknown_error"
ERROR_INVALID_MODEL: Final = "invalid_model"
ERROR_RATE_LIMIT: Final = "rate_limit_exceeded"
ERROR_CONTEXT_LENGTH: Final = "context_length_exceeded"
ERROR_API_ERROR: Final = "api_error"
ERROR_TIMEOUT: Final = "timeout_error"
ERROR_QUEUE_FULL: Final = "queue_full"
ERROR_INVALID_PROMPT: Final = "invalid_prompt"

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
ATTR_QUEUE_SIZE_DESCRIPTION: Final = "Current size of question queue"
ATTR_API_STATUS_DESCRIPTION: Final = "Current API connection status"
ATTR_ERROR_COUNT_DESCRIPTION: Final = "Total number of errors"
ATTR_LAST_ERROR_DESCRIPTION: Final = "Last error message"

# Entity attributes
ENTITY_NAME: Final = "HA Text AI"
ENTITY_ICON: Final = "mdi:robot"
ENTITY_ICON_ERROR: Final = "mdi:robot-dead"
ENTITY_ICON_PROCESSING: Final = "mdi:robot-excited"

# Translation keys
TRANSLATION_KEY_CONFIG: Final = "config"
TRANSLATION_KEY_OPTIONS: Final = "options"
TRANSLATION_KEY_ERROR: Final = "error"
TRANSLATION_KEY_STATE: Final = "state"
TRANSLATION_KEY_SERVICES: Final = "services"

# State attributes
STATE_READY: Final = "ready"
STATE_PROCESSING: Final = "processing"
STATE_ERROR: Final = "error"
STATE_DISCONNECTED: Final = "disconnected"
STATE_RATE_LIMITED: Final = "rate_limited"
STATE_INITIALIZING: Final = "initializing"

# Logging
LOGGER_NAME: Final = "custom_components.ha_text_ai"
LOG_LEVEL_DEFAULT: Final = "INFO"

# Queue constants
QUEUE_TIMEOUT: Final = 5
QUEUE_MAX_SIZE: Final = 100

# API constants
API_TIMEOUT: Final = 30
API_RETRY_COUNT: Final = 3
API_BACKOFF_FACTOR: Final = 1.5

# Service schema constants
SCHEMA_QUESTION: Final = "question"
SCHEMA_MODEL: Final = "model"
SCHEMA_TEMPERATURE: Final = "temperature"
SCHEMA_MAX_TOKENS: Final = "max_tokens"
SCHEMA_PROMPT: Final = "prompt"
SCHEMA_LIMIT: Final = "limit"

# Event names
EVENT_RESPONSE_RECEIVED: Final = f"{DOMAIN}_response_received"
EVENT_ERROR_OCCURRED: Final = f"{DOMAIN}_error_occurred"
EVENT_STATE_CHANGED: Final = f"{DOMAIN}_state_changed"
