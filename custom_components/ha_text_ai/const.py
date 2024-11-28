"""Constants for the HA text AI integration."""
from typing import Final
import voluptuous as vol
from homeassistant.const import Platform, CONF_API_KEY, CONF_NAME
from homeassistant.helpers import config_validation as cv

# Domain and platforms
DOMAIN: Final = "ha_text_ai"
PLATFORMS: list[str] = ["sensor"]

# Provider configuration
CONF_API_PROVIDER: Final = "api_provider"
API_PROVIDER_OPENAI: Final = "openai"
API_PROVIDER_ANTHROPIC: Final = "anthropic"

API_PROVIDERS: Final = [
    API_PROVIDER_OPENAI,
    API_PROVIDER_ANTHROPIC
]

# Default endpoints
DEFAULT_OPENAI_ENDPOINT: Final = "https://api.openai.com/v1"
DEFAULT_ANTHROPIC_ENDPOINT: Final = "https://api.anthropic.com"

# Configuration constants
CONF_MODEL: Final = "model"
CONF_TEMPERATURE: Final = "temperature"
CONF_MAX_TOKENS: Final = "max_tokens"
CONF_API_ENDPOINT: Final = "api_endpoint"
CONF_REQUEST_INTERVAL: Final = "request_interval"
CONF_INSTANCE: Final = "instance"
CONF_MAX_HISTORY_SIZE: Final = "max_history_size"  # Correct constant name
CONF_IS_ANTHROPIC: Final = "is_anthropic"
CONF_CONTEXT_MESSAGES: Final = "context_messages"

# Default values
DEFAULT_MODEL: Final = "gpt-4o-mini"
DEFAULT_TEMPERATURE: Final = 0.1
DEFAULT_MAX_TOKENS: Final = 1000
DEFAULT_REQUEST_INTERVAL: Final = 1.0
DEFAULT_TIMEOUT: Final = 30
DEFAULT_MAX_HISTORY: Final = 50
DEFAULT_NAME: Final = "HA Text AI"
DEFAULT_NAME_PREFIX = "ha_text_ai"
DEFAULT_CONTEXT_MESSAGES: Final = 5

# Parameter constraints
MIN_TEMPERATURE: Final = 0.0
MAX_TEMPERATURE: Final = 2.0
MIN_MAX_TOKENS: Final = 1
MAX_MAX_TOKENS: Final = 4096
MIN_REQUEST_INTERVAL: Final = 0.1
MAX_REQUEST_INTERVAL: Final = 60.0

# API constants
API_TIMEOUT: Final = 30
API_RETRY_COUNT: Final = 3

# Service names
SERVICE_ASK_QUESTION: Final = "ask_question"
SERVICE_CLEAR_HISTORY: Final = "clear_history"
SERVICE_GET_HISTORY: Final = "get_history"
SERVICE_SET_SYSTEM_PROMPT: Final = "set_system_prompt"

# Attribute keys
ATTR_QUESTION: Final = "question"
ATTR_RESPONSE: Final = "response"
ATTR_INSTANCE: Final = "instance"
ATTR_MODEL: Final = "model"
ATTR_TEMPERATURE: Final = "temperature"
ATTR_MAX_TOKENS: Final = "max_tokens"
ATTR_SYSTEM_PROMPT: Final = "system_prompt"
ATTR_API_STATUS: Final = "api_status"
ATTR_ERROR_COUNT: Final = "error_count"
ATTR_CONVERSATION_HISTORY: Final = "conversation_history"

# Sensor attributes
ATTR_TOTAL_RESPONSES: Final = "total_responses"
ATTR_TOTAL_ERRORS: Final = "total_errors"
ATTR_AVG_RESPONSE_TIME: Final = "average_response_time"
ATTR_LAST_REQUEST_TIME: Final = "last_request_time"
ATTR_LAST_ERROR: Final = "last_error"
ATTR_IS_PROCESSING: Final = "is_processing"
ATTR_IS_RATE_LIMITED: Final = "is_rate_limited"
ATTR_IS_MAINTENANCE: Final = "is_maintenance"
ATTR_API_VERSION: Final = "api_version"
ATTR_ENDPOINT_STATUS: Final = "endpoint_status"
ATTR_PERFORMANCE_METRICS: Final = "performance_metrics"
ATTR_HISTORY_SIZE: Final = "history_size"
ATTR_UPTIME: Final = "uptime"
ATTR_API_PROVIDER: Final = "api_provider"
ATTR_METRICS: Final = "metrics"
ATTR_STATE: Final = "state"
ATTR_LAST_RESPONSE: Final = "last_response"
ATTR_ERROR: Final = "error"
ATTR_TIMESTAMP: Final = "timestamp"

# Sensor metrics
METRIC_TOTAL_TOKENS: Final = "total_tokens"
METRIC_PROMPT_TOKENS: Final = "prompt_tokens"
METRIC_COMPLETION_TOKENS: Final = "completion_tokens"
METRIC_SUCCESSFUL_REQUESTS: Final = "successful_requests"
METRIC_FAILED_REQUESTS: Final = "failed_requests"
METRIC_AVERAGE_LATENCY: Final = "average_latency"
METRIC_MAX_LATENCY: Final = "max_latency"
METRIC_MIN_LATENCY: Final = "min_latency"

# Error messages
ERROR_INVALID_API_KEY: Final = "invalid_api_key"
ERROR_CANNOT_CONNECT: Final = "cannot_connect"
ERROR_UNKNOWN: Final = "unknown_error"
ERROR_INVALID_MODEL: Final = "invalid_model"
ERROR_RATE_LIMIT: Final = "rate_limit_exceeded"
ERROR_CONTEXT_LENGTH: Final = "context_length_exceeded"
ERROR_API_ERROR: Final = "api_error"
ERROR_TIMEOUT: Final = "timeout_error"
ERROR_INVALID_INSTANCE: Final = "invalid_instance"
ERROR_NAME_EXISTS: Final = "name_exists"

# Entity attributes
ENTITY_ICON: Final = "mdi:robot"
ENTITY_ICON_ERROR: Final = "mdi:robot-dead"
ENTITY_ICON_PROCESSING: Final = "mdi:robot-excited"

# State attributes
STATE_READY: Final = "ready"
STATE_PROCESSING: Final = "processing"
STATE_ERROR: Final = "error"
STATE_INITIALIZING: Final = "initializing"
STATE_MAINTENANCE: Final = "maintenance"
STATE_RATE_LIMITED: Final = "rate_limited"
STATE_DISCONNECTED: Final = "disconnected"

# Event names
EVENT_RESPONSE_RECEIVED: Final = f"{DOMAIN}_response_received"
EVENT_ERROR_OCCURRED: Final = f"{DOMAIN}_error_occurred"
EVENT_STATE_CHANGED: Final = f"{DOMAIN}_state_changed"

# Service schema constants
SERVICE_SCHEMA_ASK_QUESTION = vol.Schema({
    vol.Required(CONF_INSTANCE): cv.string,
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
    vol.Optional("context_messages"): vol.All(
        vol.Coerce(int),
        vol.Range(min=1, max=20)
    )
})

SERVICE_SCHEMA_SET_SYSTEM_PROMPT = vol.Schema({
    vol.Required(CONF_INSTANCE): cv.string,
    vol.Required("prompt"): cv.string
})

SERVICE_SCHEMA_GET_HISTORY = vol.Schema({
    vol.Required(CONF_INSTANCE): cv.string,
    vol.Optional("limit", default=10): vol.All(
        vol.Coerce(int),
        vol.Range(min=1, max=100),
    ),
    vol.Optional("filter_model"): cv.string
})

# Configuration schema
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_API_PROVIDER): vol.In(API_PROVIDERS),
        vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): cv.string,
        vol.Optional(CONF_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(
            vol.Coerce(float),
            vol.Range(min=MIN_TEMPERATURE, max=MAX_TEMPERATURE)
        ),
        vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_MAX_TOKENS, max=MAX_MAX_TOKENS)
        ),
        vol.Optional(CONF_API_ENDPOINT): cv.string,
        vol.Optional(CONF_REQUEST_INTERVAL, default=DEFAULT_REQUEST_INTERVAL): vol.All(
            vol.Coerce(float),
            vol.Range(min=MIN_REQUEST_INTERVAL, max=MAX_REQUEST_INTERVAL)
        ),
        vol.Optional(CONF_MAX_HISTORY_SIZE, default=DEFAULT_MAX_HISTORY): vol.All(  # Correct usage
            vol.Coerce(int),
            vol.Range(min=1, max=100),
        ),
        vol.Optional(CONF_CONTEXT_MESSAGES, default=DEFAULT_CONTEXT_MESSAGES): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=20)
        )
    })
}, extra=vol.ALLOW_EXTRA)
