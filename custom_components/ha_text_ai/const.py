"""Constants for the HA text AI integration."""
from typing import Final
import voluptuous as vol
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

# Domain and platforms
DOMAIN: Final = "ha_text_ai"
PLATFORMS: Final = [Platform.SENSOR]
CONF_NAME = "name"
DEFAULT_NAME = "HA Text AI"

# New constants for providers
CONF_API_PROVIDER: Final = "api_provider"
API_PROVIDER_OPENAI: Final = "openai"
API_PROVIDER_ANTHROPIC: Final = "anthropic"

API_PROVIDERS: Final = [
    API_PROVIDER_OPENAI,
    API_PROVIDER_ANTHROPIC
]

# Default endpoints
DEFAULT_OPENAI_ENDPOINT: Final = "https://api.openai.com/v1"
DEFAULT_ANTHROPIC_ENDPOINT: Final = "https://api.anthropic.com/v1"

# Configuration constants
CONF_MODEL: Final = "model"
CONF_TEMPERATURE: Final = "temperature"
CONF_MAX_TOKENS: Final = "max_tokens"
CONF_API_ENDPOINT: Final = "api_endpoint"
CONF_REQUEST_INTERVAL: Final = "request_interval"

# Default values
DEFAULT_MODEL: Final = "gpt-4o-mini"
DEFAULT_TEMPERATURE: Final = 0.1
DEFAULT_MAX_TOKENS: Final = 1000
DEFAULT_API_ENDPOINT: Final = DEFAULT_OPENAI_ENDPOINT
DEFAULT_REQUEST_INTERVAL: Final = 1.0
DEFAULT_TIMEOUT: Final = 30

# Parameter constraints
MIN_TEMPERATURE: Final = 0.0
MAX_TEMPERATURE: Final = 2.0
MIN_MAX_TOKENS: Final = 1
MAX_MAX_TOKENS: Final = 4096
MIN_REQUEST_INTERVAL: Final = 0.1

# API constants
API_CHAT_PATH: Final = "chat/completions"
API_TIMEOUT: Final = 30
API_RETRY_COUNT: Final = 3

# History constants
HISTORY_FILTER_MODEL: Final = "filter_model"
HISTORY_FILTER_DATE: Final = "start_date"
HISTORY_SORT_ORDER: Final = "sort_order"
HISTORY_INCLUDE_METADATA: Final = "include_metadata"

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
ATTR_API_VERSION: Final = "api_version"
ATTR_ENDPOINT_STATUS: Final = "endpoint_status"
ATTR_REQUEST_COUNT: Final = "request_count"
ATTR_TOKENS_USED: Final = "tokens_used"
ATTR_RETRY_COUNT: Final = "retry_count"
ATTR_QUEUE_POSITION: Final = "queue_position"
ATTR_ESTIMATED_WAIT: Final = "estimated_wait"

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
ERROR_INVALID_PARAMETERS: Final = "invalid_parameters"
ERROR_SERVICE_UNAVAILABLE: Final = "service_unavailable"

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
ATTR_API_VERSION_DESCRIPTION: Final = "Current API version"
ATTR_ENDPOINT_STATUS_DESCRIPTION: Final = "Current endpoint status"
ATTR_REQUEST_COUNT_DESCRIPTION: Final = "Total number of API requests"
ATTR_TOKENS_USED_DESCRIPTION: Final = "Total tokens used"

# Entity attributes
ENTITY_NAME: Final = "HA Text AI"
ENTITY_ICON: Final = "mdi:robot"
ENTITY_ICON_ERROR: Final = "mdi:robot-dead"
ENTITY_ICON_PROCESSING: Final = "mdi:robot-excited"
ENTITY_ICON_OFFLINE: Final = "mdi:robot-off"
ENTITY_ICON_QUEUE: Final = "mdi:robot-confused"

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
STATE_MAINTENANCE: Final = "maintenance"
STATE_RETRYING: Final = "retrying"
STATE_QUEUED: Final = "queued"
STATE_UPDATING: Final = "updating"

# Logging
LOGGER_NAME: Final = "custom_components.ha_text_ai"
LOG_LEVEL_DEFAULT: Final = "INFO"

# Queue constants
QUEUE_TIMEOUT: Final = 5
QUEUE_MAX_SIZE: Final = 100

# Retry constants
MAX_RETRIES: Final = 3
RETRY_DELAY: Final = 1.0

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

# Service schema constants
SERVICE_SCHEMA_ASK_QUESTION = vol.Schema({
    vol.Required("question"): cv.string,
    vol.Optional("system_prompt"): cv.string,
    vol.Optional("model"): cv.string,
    vol.Optional("temperature"): vol.All(
        vol.Coerce(float),
        vol.Range(min=MIN_TEMPERATURE, max=MAX_TEMPERATURE)
    ),
    vol.Optional("max_tokens"): vol.All(
        vol.Coerce(int),
        vol.Range(min=MIN_MAX_TOKENS, max=MAX_MAX_TOKENS)
    ),
    vol.Optional("priority"): cv.boolean,
})

# set_system_prompt
SERVICE_SCHEMA_SET_SYSTEM_PROMPT = vol.Schema({
    vol.Required("prompt"): cv.string,
})

# get_history
SERVICE_SCHEMA_GET_HISTORY = vol.Schema({
    vol.Optional("limit", default=10): vol.All(
        vol.Coerce(int),
        vol.Range(min=1, max=100)
    ),
#    vol.Optional("filter_model"): vol.In(SUPPORTED_MODELS),
    vol.Optional("start_date"): cv.datetime,
    vol.Optional("include_metadata"): cv.boolean,
})
