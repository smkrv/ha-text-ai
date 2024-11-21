async def async_check_api(session, endpoint: str, headers: dict, is_anthropic: bool = False) -> bool:
    """Check API availability for different providers."""
    try:
        # Определяем, является ли это VSE GPT endpoint
        is_vsegpt = "vsegpt" in endpoint.lower()

        if is_vsegpt:
            # Для VSE GPT используем специальный endpoint
            check_url = f"{endpoint.rstrip('/')}/v1/models"
            headers["Authorization"] = f"Bearer {headers.get('x-api-key', '')}"
        elif is_anthropic:
            check_url = f"{endpoint}/v1/models"
        else:
            check_url = f"{endpoint}/{API_VERSION}/{API_MODELS_PATH}"

        async with timeout(API_TIMEOUT):
            async with session.get(check_url, headers=headers) as response:
                if response.status == 200:
                    return True
                elif response.status == 404 and is_vsegpt:
                    # VSE GPT может возвращать 404 для /models endpoint
                    return True
                elif response.status == 401:
                    raise ConfigEntryNotReady("Invalid API key")
                elif response.status == 429:
                    _LOGGER.warning("Rate limit exceeded during API check")
                    return False
                else:
                    _LOGGER.error("API check failed with status: %d", response.status)
                    return False
    except Exception as ex:
        _LOGGER.error("API check error: %s", str(ex))
        return False

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA Text AI from a config entry."""
    try:
        session = aiohttp_client.async_get_clientsession(hass)

        # Determine API type based on model and endpoint
        model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        endpoint = entry.data.get(CONF_API_ENDPOINT, DEFAULT_API_ENDPOINT).rstrip('/')
        api_key = entry.data[CONF_API_KEY]

        is_vsegpt = "vsegpt" in endpoint.lower()
        is_anthropic = any(m in model.lower() for m in ["claude", "anthropic"]) or is_vsegpt

        # Configure headers based on API type
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if is_vsegpt:
            headers["Authorization"] = f"Bearer {api_key}"
            if is_anthropic:
                headers["anthropic-version"] = "2023-06-01"
        elif is_anthropic:
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {api_key}"

        # Check API with retries
        for attempt in range(API_RETRY_COUNT):
            if await async_check_api(session, endpoint, headers, is_anthropic):
                break
            if attempt < API_RETRY_COUNT - 1:
                delay = API_BACKOFF_FACTOR * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                raise ConfigEntryNotReady("Failed to connect to API")

        # Create coordinator
        coordinator = HATextAICoordinator(
            hass,
            api_key=api_key,
            endpoint=endpoint,
            model=model,
            temperature=entry.data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
            max_tokens=entry.data.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
            request_interval=entry.data.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL),
            session=session,
            is_anthropic=is_anthropic
        )

        # Initialize the coordinator
        await coordinator.async_initialize()

        # Perform first refresh
        await coordinator.async_config_entry_first_refresh()

        # Check coordinator status
        if coordinator.endpoint_status == "auth_error":
            raise ConfigEntryNotReady("Authentication failed")
        elif coordinator.endpoint_status == "rate_limited":
            _LOGGER.warning("API rate limited during setup")
        elif coordinator.endpoint_status == "maintenance":
            raise ConfigEntryNotReady("API is in maintenance mode")
        elif coordinator.endpoint_status == "error":
            raise ConfigEntryNotReady("API error during setup")
        elif not coordinator.last_update_success:
            raise ConfigEntryNotReady("Failed to initialize coordinator")

        hass.data[DOMAIN][entry.entry_id] = coordinator
