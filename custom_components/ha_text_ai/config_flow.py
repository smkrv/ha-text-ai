"""Config flow for HA Text AI Integration."""  
from __future__ import annotations  

import logging  
from typing import Any  

import voluptuous as vol  
from openai import AsyncOpenAI  
from openai.types.error import APIError  
from openai.exceptions import AuthenticationError, APIConnectionError  

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

@config_entries.HANDLERS.register(DOMAIN)  
class TextAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  
    """Handle a config flow for HA Text AI Integration."""  

    VERSION = 1  
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL  

    def __init__(self) -> None:  
        """Initialize the config flow."""  
        super().__init__()  

    async def async_step_user(  
        self, user_input: dict[str, Any] | None = None  
    ) -> FlowResult:  
        """Handle the initial step."""  
        errors = {}  

        if user_input is not None:  
            try:  
                await self._test_api_key(user_input[CONF_API_KEY], user_input.get(CONF_API_BASE))  
                return self.async_create_entry(  
                    title="HA Text AI",  
                    data=user_input,  
                )  
            except ApiKeyError:  
                errors["base"] = "invalid_api_key"  
            except ApiConnectionError:  
                errors["base"] = "cannot_connect"  
            except Exception:  # pylint: disable=broad-except  
                _LOGGER.exception("Unexpected exception")  
                errors["base"] = "unknown"  

        return self.async_show_form(  
            step_id="user",  
            data_schema=vol.Schema(  
                {  
                    vol.Required(CONF_API_KEY): str,  
                    vol.Optional(CONF_API_BASE, default=DEFAULT_API_BASE): str,  
                    vol.Optional(CONF_REQUEST_INTERVAL, default=DEFAULT_REQUEST_INTERVAL): int,  
                }  
            ),  
            errors=errors,  
        )  

    @staticmethod  
    async def _test_api_key(api_key: str, api_base: str | None) -> None:  
        """Test if the API key is valid."""  
        try:  
            client = AsyncOpenAI(  
                api_key=api_key,  
                base_url=api_base if api_base else DEFAULT_API_BASE  
            )  
            
            models = await client.models.list()  
            if not models.data:  
                raise ApiKeyError  
                
        except AuthenticationError as err:  
            raise ApiKeyError from err  
        except APIConnectionError as err:  
            raise ApiConnectionError from err  
        except APIError as err:  
            if err.status_code == 401:  
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
                    ): int,  
                }  
            ),  
        )  


class ApiKeyError(HomeAssistantError):  
    """Error to indicate there is an invalid API key."""  


class ApiConnectionError(HomeAssistantError):  
    """Error to indicate there is a connection error."""
