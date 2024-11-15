"""Config flow for HA Text AI Integration."""  
from __future__ import annotations  

import logging  
from typing import Any  

import voluptuous as vol  
from openai import AsyncOpenAI  
from openai import OpenAIError, AuthenticationError, APIConnectionError  

from homeassistant import config_entries  
from homeassistant.core import HomeAssistant, callback  
from homeassistant.data_entry_flow import FlowResult  
from homeassistant.exceptions import HomeAssistantError  

from .const import (  
    DOMAIN,  
    CONF_API_KEY,  
    CONF_API_BASE,  
    CONF_REQUEST_INTERVAL,  
    DEFAULT_API_BASE,  
    DEFAULT_REQUEST_INTERVAL,  
)  

_LOGGER = logging.getLogger(__name__)  

STEP_USER_DATA_SCHEMA = vol.Schema(  
    {  
        vol.Required(CONF_API_KEY): str,  
        vol.Optional(CONF_API_BASE, default=DEFAULT_API_BASE): str,  
        vol.Optional(  
            CONF_REQUEST_INTERVAL,  
            default=DEFAULT_REQUEST_INTERVAL  
        ): vol.All(int, vol.Range(min=1, max=3600)),  
    }  
)  

class TextAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  
    """Handle a config flow for HA Text AI Integration."""  

    VERSION = 1  

    async def async_step_user(  
        self, user_input: dict[str, Any] | None = None  
    ) -> FlowResult:  
        """Handle the initial step."""  
        errors = {}  

        if user_input is not None:  
            try:  
                await self._test_api_key(  
                    user_input[CONF_API_KEY],  
                    user_input.get(CONF_API_BASE, DEFAULT_API_BASE)  
                )  
                
                await self.async_set_unique_id(user_input[CONF_API_KEY])  
                self._abort_if_unique_id_configured()  
                
                return self.async_create_entry(  
                    title="HA Text AI",  
                    data=user_input,  
                )  
            except ApiKeyError:  
                errors["base"] = "invalid_api_key"  
                errors[CONF_API_KEY] = "invalid_api_key"  
            except ApiConnectionError as err:  
                errors["base"] = "cannot_connect"  
                errors[CONF_API_BASE] = "cannot_connect"  
                _LOGGER.error("Connection error: %s", str(err))  
            except vol.Invalid:  
                errors[CONF_REQUEST_INTERVAL] = "invalid_interval"  
            except Exception as err:  # pylint: disable=broad-except  
                _LOGGER.exception("Unexpected exception")  
                errors["base"] = "unknown"  
                _LOGGER.error("Unknown error: %s", str(err))  

        return self.async_show_form(  
            step_id="user",  
            data_schema=STEP_USER_DATA_SCHEMA,  
            errors=errors,  
            description_placeholders={  
                "default_interval": str(DEFAULT_REQUEST_INTERVAL),  
                "min_interval": "1",  
                "max_interval": "3600",  
            },  
        )  

    @staticmethod  
    async def _test_api_key(api_key: str, api_base: str) -> None:  
        """Test if the API key is valid."""  
        try:  
            client = AsyncOpenAI(  
                api_key=api_key,  
                base_url=api_base  
            )  
            
            models = await client.models.list()  
            if not models.data:  
                _LOGGER.error("No models available with provided API key")  
                raise ApiKeyError("No models available")  
                
        except AuthenticationError as err:  
            _LOGGER.error("Authentication error: %s", str(err))  
            raise ApiKeyError from err  
        except APIConnectionError as err:  
            _LOGGER.error("API Connection error: %s", str(err))  
            raise ApiConnectionError from err  
        except OpenAIError as err:  
            _LOGGER.error("OpenAI API error: %s", str(err))  
            if getattr(err, 'status_code', None) == 401:  
                raise ApiKeyError from err  
            raise ApiConnectionError from err  

    @staticmethod  
    @callback  
    def async_get_options_flow(  
        config_entry: config_entries.ConfigEntry,  
    ) -> TextAIOptionsFlow:  
        """Get the options flow for this handler."""  
        return TextAIOptionsFlow(config_entry)  


class TextAIOptionsFlow(config_entries.OptionsFlow):  
    """Handle options flow for HA Text AI Integration."""  

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:  
        """Initialize options flow."""  
        self.config_entry = config_entry  

    async def async_step_init(  
        self, user_input: dict[str, Any] | None = None  
    ) -> FlowResult:  
        """Manage options."""  
        if user_input is not None:  
            return self.async_create_entry(title="", data=user_input)  

        return self.async_show_form(  
            step_id="init",  
            data_schema=vol.Schema(  
                {  
                    vol.Optional(  
                        CONF_REQUEST_INTERVAL,  
                        default=self.config_entry.options.get(  
                            CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL  
                        ),  
                    ): vol.All(int, vol.Range(min=1, max=3600)),  
                }  
            ),  
            description_placeholders={  
                "current_interval": str(self.config_entry.options.get(  
                    CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL  
                )),  
            },  
        )  


class ApiKeyError(HomeAssistantError):  
    """Error to indicate there is an invalid API key."""  


class ApiConnectionError(HomeAssistantError):  
    """Error to indicate there is a connection error."""
