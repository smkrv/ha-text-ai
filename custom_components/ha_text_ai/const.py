"""Constants for the HA text AI integration."""
from homeassistant.const import Platform

DOMAIN = "ha-text-ai"
PLATFORMS = [Platform.SENSOR]

# Configuration
CONF_MODEL = "model"
CONF_TEMPERATURE = "temperature"
CONF_MAX_TOKENS = "max_tokens"
CONF_API_ENDPOINT = "api_endpoint"
CONF_REQUEST_INTERVAL = "request_interval"

# Defaults
DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000
DEFAULT_API_ENDPOINT = "https://api.openai.com/v1"
DEFAULT_REQUEST_INTERVAL = 1.0

# Services
SERVICE_ASK_QUESTION = "ask_question"
SERVICE_CLEAR_HISTORY = "clear_history"
SERVICE_GET_HISTORY = "get_history"
SERVICE_SET_SYSTEM_PROMPT = "set_system_prompt"

# Attributes
ATTR_QUESTION = "question"
ATTR_RESPONSE = "response"
ATTR_LAST_UPDATED = "last_updated"
