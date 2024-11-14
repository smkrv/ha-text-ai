"""The HA Text AI Integration."""  
from __future__ import annotations  

import asyncio  
import logging  
from typing import Any  

from openai import AsyncOpenAI  
import voluptuous as vol  

from homeassistant.config_entries import ConfigEntry  
from homeassistant.const import CONF_API_KEY, Platform  
from homeassistant.core import HomeAssistant, ServiceCall  
from homeassistant.helpers import entity_registry as er  
from homeassistant.helpers.entity_component import EntityComponent  
from homeassistant.helpers import config_validation as cv  
from homeassistant.components import input_text  

from .const import (  
    DOMAIN,  
    CONF_API_BASE,  
    CONF_REQUEST_INTERVAL,  
    DEFAULT_API_BASE,  
    DEFAULT_REQUEST_INTERVAL,  
    TEXT_HELPER_PREFIX,  
    TEXT_HELPER_MAX_LENGTH,  
)  

_LOGGER = logging.getLogger(__name__)  

PLATFORMS: list[Platform] = []  

async def async_setup(hass: HomeAssistant, config: dict) -> bool:  
    """Set up the HA Text AI component."""  
    hass.data.setdefault(DOMAIN, {})  
    return True  

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  
    """Set up HA Text AI from a config entry."""  
    client = AsyncOpenAI(  
        api_key=entry.data[CONF_API_KEY],  
        base_url=entry.data.get(CONF_API_BASE, DEFAULT_API_BASE)  
    )  

    hass.data[DOMAIN][entry.entry_id] = {  
        "client": client,  
        CONF_REQUEST_INTERVAL: entry.data.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL),  
        "queue": [],  
        "processing": False,  
    }  

    async def create_text_helper(name: str) -> str:  
        """Create a Text Helper if it doesn't exist."""  
        object_id = f"{TEXT_HELPER_PREFIX}{name}"  
        
        entity_id = f"input_text.{object_id}"  
        entity_registry = er.async_get(hass)  
        
        if entity_registry.async_get(entity_id) is None:  
            await hass.services.async_call(  
                "input_text",  
                "create",  
                {  
                    "name": f"AI Response {name}",  
                    "id": object_id,  
                    "max": TEXT_HELPER_MAX_LENGTH,  
                    "initial": "",  
                },  
            )  
        
        return entity_id  

    async def handle_text_ai_call(call: ServiceCall) -> None:  
        """Handle the text AI service call."""  
        entry_id = list(hass.data[DOMAIN].keys())[0]  # Используем первую настроенную интеграцию  
        
        response_id = call.data.get("response_id", "default")  
        entity_id = await create_text_helper(response_id)  

        request_data = {  
            "prompt": call.data["prompt"],  
            "model": call.data.get("model", "gpt-3.5-turbo"),  
            "temperature": call.data.get("temperature", 0.7),  
            "max_tokens": call.data.get("max_tokens", 150),  
            "top_p": call.data.get("top_p", 1.0),  
            "frequency_penalty": call.data.get("frequency_penalty", 0.0),  
            "presence_penalty": call.data.get("presence_penalty", 0.0),  
            "entity_id": entity_id,  
        }  

        hass.data[DOMAIN][entry_id]["queue"].append(request_data)  
        
        if not hass.data[DOMAIN][entry_id]["processing"]:  
            asyncio.create_task(process_queue(hass, entry_id))  

    async def process_queue(hass: HomeAssistant, entry_id: str) -> None:  
        """Process the queue of requests."""  
        if hass.data[DOMAIN][entry_id]["processing"]:  
            return  

        hass.data[DOMAIN][entry_id]["processing"] = True  
        client = hass.data[DOMAIN][entry_id]["client"]  
        
        while hass.data[DOMAIN][entry_id]["queue"]:  
            request = hass.data[DOMAIN][entry_id]["queue"].pop(0)  
            
            try:  
                response = await client.chat.completions.create(  
                    model=request["model"],  
                    messages=[{"role": "user", "content": request["prompt"]}],  
                    temperature=request["temperature"],  
                    max_tokens=request["max_tokens"],  
                    top_p=request["top_p"],  
                    frequency_penalty=request["frequency_penalty"],  
                    presence_penalty=request["presence_penalty"],  
                )  

                response_text = response.choices[0].message.content  
                await hass.services.async_call(  
                    "input_text",  
                    "set_value",  
                    {  
                        "entity_id": request["entity_id"],  
                        "value": response_text  
                    },  
                )  

            except Exception as e:  
                _LOGGER.error("Error processing request: %s", str(e))  

            await asyncio.sleep(hass.data[DOMAIN][entry_id][CONF_REQUEST_INTERVAL])  

        hass.data[DOMAIN][entry_id]["processing"] = False  

    hass.services.async_register(  
        DOMAIN,  
        "text_ai_call",  
        handle_text_ai_call,  
        schema=vol.Schema({  
            vol.Required("prompt"): cv.string,  
            vol.Optional("response_id", default="default"): cv.string,  
            vol.Optional("model", default="gpt-3.5-turbo"): cv.string,  
            vol.Optional("temperature", default=0.7): vol.Coerce(float),  
            vol.Optional("max_tokens", default=150): vol.Coerce(int),  
            vol.Optional("top_p", default=1.0): vol.Coerce(float),  
            vol.Optional("frequency_penalty", default=0.0): vol.Coerce(float),  
            vol.Optional("presence_penalty", default=0.0): vol.Coerce(float),  
        })  
    )  

    return True  

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  
    """Unload a config entry."""  
    hass.data[DOMAIN].pop(entry.entry_id)  
    return True
