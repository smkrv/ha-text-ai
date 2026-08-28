# HA Text AI for Home Assistant

<div align="center">  

  ![GitHub release](https://img.shields.io/github/v/release/smkrv/ha-text-ai?style=flat-square) ![GitHub last commit](https://img.shields.io/github/last-commit/smkrv/ha-text-ai?style=flat-square) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://opensource.org/licenses/MIT) [![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
  ![Deutsch](https://img.shields.io/badge/lang-DE-blue?style=flat-square) ![English](https://img.shields.io/badge/lang-EN-blue?style=flat-square) ![Español](https://img.shields.io/badge/lang-ES-blue?style=flat-square) ![हिन्दी](https://img.shields.io/badge/lang-HI-blue?style=flat-square) ![Italiano](https://img.shields.io/badge/lang-IT-blue?style=flat-square) ![Русский](https://img.shields.io/badge/lang-RU-blue?style=flat-square) ![Српски](https://img.shields.io/badge/lang-SR-blue?style=flat-square) ![中文](https://img.shields.io/badge/lang-ZH-blue?style=flat-square)


  <img src="https://github.com/smkrv/ha-text-ai/blob/main/custom_components/ha_text_ai/icons/logo%402x.png" alt="HA Text AI" style="width: 50%; max-width: 256px; max-height: 128px; aspect-ratio: 2/1; object-fit: contain;"/>

### Multi-provider LLM integration for [Home Assistant](https://www.home-assistant.io/)
</div>

<p align="center">
Ask OpenAI, Anthropic Claude, DeepSeek and Google Gemini models questions from your automations and scripts. The integration keeps per-instance conversation history, returns full-length responses through response variables, supports structured JSON output, and exposes token, latency and error metrics as sensor attributes.
</p>

---

> [!IMPORTANT]
> Community driven: for more details on the integration,   
> check out the discussion on the **[Home Assistant Community forum](https://community.home-assistant.io/t/ha-text-ai-transforming-home-automation-through-multi-llm-integration/799741)**
>
>  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=smkrv&repository=ha-text-ai&category=Integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" width="210" height="auto"></a>
>  
> [Screenshots](assets/images/screenshots/screenshot.jpg)

## Features

- **Multi-provider support**: OpenAI, Anthropic Claude, DeepSeek, Google Gemini, plus any OpenAI-compatible endpoint
- **Conversation context**: the model sees previous messages; depth is configurable per request (1-20)
- **Response variables**: `ask_question` returns the full response directly to the calling automation, bypassing the 255-character state limit
- **Structured output**: JSON responses matching a schema you provide
- **Per-request overrides**: model, temperature, max_tokens, system prompt, thinking mode
- **Usage metrics**: token counters, latency and success/error statistics as sensor attributes
- **File-based history**: per-instance JSON storage with automatic rotation at 1 MB

#### Translations

| Code | Language | Status |
|------|----------|--------|
| de | Deutsch | Full |
| en | English | Primary |
| es | Español | Full |
| hi | हिन्दी | Full |
| it | Italiano | Full |
| ru | Русский | Full |
| sr | Српски | Full |
| zh | 中文 | Full |

## Prerequisites

- Home Assistant 2024.12.0 or later
- An API key from one of:
  - OpenAI ([Get key](https://platform.openai.com/account/api-keys))
  - Anthropic ([Get key](https://console.anthropic.com/))
  - DeepSeek ([Get key](https://platform.deepseek.com/api_keys))
  - OpenRouter ([Get key](https://openrouter.ai/keys))
  - Google Gemini ([Get key](https://ai.google.dev/gemini-api/docs/api-key)) thanks to ([@Azzedde](https://github.com/Azzedde))
  - Any OpenAI-compatible API provider

## Configuration Options

### Core Configuration Settings
- **API Provider**: OpenAI / Anthropic / DeepSeek / Gemini
- **API Key**: provider-specific authentication
- **Model**: any model your provider offers
- **Temperature**: sampling temperature (0.0-2.0)
- **Max Tokens**: response length cap, passed to the LLM API
- **Request Interval**: minimum delay between API calls (seconds)
- **History Size**: number of conversations to retain
- **Custom API Endpoint**: for OpenRouter, proxies and self-hosted servers
- **Disable Thinking**: turn off model reasoning where the provider supports it
- **Allow Local Network**: permit endpoints on private addresses (needed for local servers like Ollama)

### Recommended Models

#### OpenAI Models
- **GPT-5.6 Sol** - flagship tier for the hardest tasks
- **GPT-5.6 Terra** - mid-tier for high-volume tasks
- **GPT-5.6 Luna** - fastest and cheapest, enough for most home automation queries

#### Anthropic Claude Models
- **Claude Fable 5** - the most capable model for complex tasks
- **Claude Sonnet 5** - balance between quality and cost
- **Claude Haiku 4.5** - the fastest and cheapest option in the lineup

#### DeepSeek Models
- **deepseek-v4-flash** - fast general-purpose model (default)
- **deepseek-v4-pro** - stronger at reasoning and coding

> The legacy model names `deepseek-chat` and `deepseek-reasoner` stop working on 2026-07-24. If your instance still uses one of them, switch the model in the integration options.

#### Google Gemini Models
- **gemini-3.5-flash** - default; Google's strongest currently available model
- **gemini-3.1-pro** - previous flagship, still supported

> Google shut down `gemini-2.0-flash` on 2026-06-01 and retires the 2.5 family on 2026-10-16. If your instance uses one of those, switch the model in the integration options.

<details>
<summary>Potentially Compatible Providers</summary>

Other providers with OpenAI-compatible APIs may work through the custom endpoint option:
- Groq
- Together AI
- Perplexity AI
- Mistral AI
- Local AI servers (like Ollama - enable **Allow Local Network** in the options)
- Custom OpenAI-compatible endpoints

Compatibility is not guaranteed. A provider needs an OpenAI-like REST API with JSON request/response format, standard bearer authentication and similar parameter handling. Check the provider's documentation and make sure your API key has sufficient quota.

</details>

## Installation

### HACS Installation (Recommended)
>[!TIP]
>HA Text AI is available in the default HACS repository. You can install it directly through HACS or click the button below to open it there.

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=smkrv&repository=ha-text-ai&category=Integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" width="170" height="auto"></a>
1. Open HACS in Home Assistant
2. Search for "HA Text AI"
3. Click "Download"
4. Restart Home Assistant

**Alternative Method (Custom Repository):**
If the integration is not found in the default repository:
1. Click "..." in top right corner of HACS
2. Select "Custom repositories"
3. Add repository URL: `https://github.com/smkrv/ha-text-ai`
4. Choose "Integration" as category
5. Click "Download"

### Manual Installation
1. Download `ha_text_ai.zip` from the latest release
2. Extract the archive and copy the `ha_text_ai` folder into your `custom_components` directory
3. Restart Home Assistant
4. Add configuration via UI (Settings > Devices & Services > Add Integration)

## Configuration

### Via UI (Recommended)
1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "HA Text AI"
4. Follow the configuration steps

> **Note:** This integration is configured exclusively through the UI (config entries). YAML configuration is not supported.

## Quick Start

After configuration you get one entity per instance, named `sensor.ha_text_ai_<name>`. It is a status sensor: it shows the last response and usage metrics, but you don't type questions into it. Questions go through the `ha_text_ai.ask_question` action, called from Developer Tools, automations, or scripts.

### First question, no YAML

1. Open Developer Tools > Actions (called "Services" in older HA versions).
2. Search for "HA Text AI: Ask Question".
3. Pick your instance, type a question, press "Perform action".
4. The response appears below the form.

### In an automation

1. Go to Settings > Automations & scenes > Create automation.
2. Add a trigger: a button press, a time, a state change.
3. Add action > search "HA Text AI: Ask Question" > fill in the question and pick your instance.
4. To use the reply in a follow-up step, the action needs `response_variable: ai_response`. If the visual editor doesn't show a field for it, open the three-dot menu on that action, choose "Edit in YAML", and add the line at the end.
5. In the next action, `{{ ai_response.response_text }}` holds the full answer, for example as a notification message.

Complete working automations: [Automation Examples](#automation-examples-with-response-variables).

### On a dashboard

The sensor keeps the last question and answer as attributes, so a Markdown card can show them:

```yaml
type: markdown
content: >-
  **Q:** {{ state_attr('sensor.ha_text_ai_my_assistant', 'question') }}

  **A:** {{ state_attr('sensor.ha_text_ai_my_assistant', 'response') }}
```

The attributes fill in after the first question. They are capped at 2048 characters, so long answers come back complete only via `response_variable`.

## Available Services

### Response Variables

`ask_question` returns its result directly to the calling automation via `response_variable`. The full response text comes back regardless of length (no 255-character truncation), it is available immediately without polling sensor state, and each service call gets its own result, so parallel automations don't overwrite each other.

### ask_question
```yaml
service: ha_text_ai.ask_question
data:
  question: "What's the optimal temperature for sleeping?"
  instance: sensor.ha_text_ai_claude
  model: "claude-sonnet-5"  # optional, overrides the configured model
  temperature: 0.5  # optional
  max_tokens: 500  # optional
  context_messages: 10  # optional, previous messages to include (1-20, default 5)
  system_prompt: "You are a sleep optimization expert"  # optional
  disable_thinking: true  # optional, disable model reasoning for this request
response_variable: ai_response
```

For structured JSON output, add `structured_output` with a schema:
```yaml
service: ha_text_ai.ask_question
data:
  question: "Suggest three energy-saving actions for tonight"
  instance: sensor.ha_text_ai_gpt
  structured_output: true
  json_schema: >-
    {"type": "object", "properties": {"actions": {"type": "array", "items": {"type": "string"}}}}
response_variable: ai_response
```

#### Response Data Structure
```yaml
# The service returns structured data:
response_text: "The optimal sleeping temperature is 65-68°F (18-20°C)..."
tokens_used: 150
prompt_tokens: 50
completion_tokens: 100
model_used: "claude-sonnet-5"
instance: "sensor.ha_text_ai_claude"
question: "What's the optimal temperature for sleeping?"
timestamp: "2026-07-09T16:57:00.000Z"
success: true
# error and error_type are present only when success is false
```

### set_system_prompt
```yaml
service: ha_text_ai.set_system_prompt
data:
  instance: sensor.ha_text_ai_gpt
  prompt: |
    You are a home automation expert focused on:
    1. Energy efficiency
    2. Comfort optimization
    3. Security considerations
    Provide practical, actionable advice.
```

### clear_history
```yaml
service: ha_text_ai.clear_history
data:
  instance: sensor.ha_text_ai_gpt
```

### get_history
```yaml
service: ha_text_ai.get_history
data:
  limit: 5  # optional, number of conversations to return (values above 200 are clamped); omit to get the full stored history
  filter_model: "gpt-4o"  # optional, filter by specific AI model
  start_date: "2026-02-01"  # optional, filter conversations from this date
  include_metadata: false  # optional, include tokens, response time, etc.
  sort_order: "newest"  # optional, sort order: "newest" or "oldest"
  instance: sensor.ha_text_ai_gpt
response_variable: history_result  # entries are in history_result.history
```

## Automation Examples with Response Variables

### Example 1: Smart Home Advice with Direct Response
```yaml
automation:
  - alias: "Get AI Home Advice"
    trigger:
      - platform: state
        entity_id: input_button.ask_ai_advice
    action:
      - service: ha_text_ai.ask_question
        data:
          question: "What's the best way to optimize energy usage in my home?"
          instance: sensor.ha_text_ai_gpt
        response_variable: ai_advice
      - service: notify.mobile_app
        data:
          title: "Smart Home Tip"
          message: |
            {{ ai_advice.response_text }}
            
            Tokens used: {{ ai_advice.tokens_used }}
            Model: {{ ai_advice.model_used }}
```

### Example 2: Weather-Based AI Recommendations
```yaml
automation:
  - alias: "Weather-Based AI Suggestions"
    trigger:
      - platform: numeric_state
        entity_id: sensor.outdoor_temperature
        below: 0
    action:
      - service: ha_text_ai.ask_question
        data:
          question: |
            The outdoor temperature is {{ states('sensor.outdoor_temperature') }}°C. 
            What should I do to prepare my home for freezing weather?
          system_prompt: "You are a home maintenance expert. Provide practical, actionable advice."
          instance: sensor.ha_text_ai_gpt
        response_variable: winter_advice
      - if:
          - condition: template
            value_template: "{{ winter_advice.success }}"
        then:
          - service: persistent_notification.create
            data:
              title: "Winter Preparation Advice"
              message: |
                {{ winter_advice.response_text }}
                
                Generated at: {{ winter_advice.timestamp }}
        else:
          - service: persistent_notification.create
            data:
              title: "AI Service Error"
              message: "Failed to get winter advice: {{ winter_advice.error }}"
```

### Example 3: Multi-Step AI Workflow
```yaml
automation:
  - alias: "Multi-Step AI Analysis"
    trigger:
      - platform: state
        entity_id: input_button.analyze_home_status
    action:
      # Step 1: Get current status analysis
      - service: ha_text_ai.ask_question
        data:
          question: |
            Current home status:
            - Temperature: {{ states('sensor.indoor_temperature') }}°C
            - Humidity: {{ states('sensor.indoor_humidity') }}%
            - Energy usage: {{ states('sensor.power_consumption') }}W
            
            Analyze this data and provide insights.
          instance: sensor.ha_text_ai_gpt
        response_variable: status_analysis
      
      # Step 2: Get recommendations based on analysis
      - service: ha_text_ai.ask_question
        data:
          question: |
            Based on this analysis: "{{ status_analysis.response_text[:500] }}"
            
            Provide 3 specific actionable recommendations for improvement.
          context_messages: 2  # Include previous conversation
          instance: sensor.ha_text_ai_gpt
        response_variable: recommendations
      
      # Step 3: Send the combined report
      - service: notify.telegram
        data:
          title: "Home Analysis Report"
          message: |
            **Analysis:**
            {{ status_analysis.response_text }}
            
            **Recommendations:**
            {{ recommendations.response_text }}
            
            **Report Details:**
            - Total tokens used: {{ status_analysis.tokens_used + recommendations.tokens_used }}
            - Analysis model: {{ status_analysis.model_used }}
            - Generated: {{ recommendations.timestamp }}
```

### Migration from Sensors to Response Variables

#### Old Method:
```yaml
# Old way: delay-based polling, response truncated by the 255-character state limit
automation:
  - alias: "Old AI Response Method"
    action:
      - service: ha_text_ai.ask_question
        data:
          question: "Long question here..."
          instance: sensor.ha_text_ai_gpt
      - delay: "00:00:05"  # Wait for sensor update
      - service: notify.mobile
        data:
          message: "{{ state_attr('sensor.ha_text_ai_gpt', 'response')[:255] }}..."  # Truncated
```

#### New Method:
```yaml
# New way: full response, available immediately
automation:
  - alias: "New AI Response Method"
    action:
      - service: ha_text_ai.ask_question
        data:
          question: "Long question here..."
          instance: sensor.ha_text_ai_gpt
        response_variable: ai_response
      - service: notify.mobile
        data:
          message: "{{ ai_response.response_text }}"  # Full response, no truncation
```

### HA Text AI Sensor Naming Convention

#### Naming Rules
- Only lowercase letters (a-z), numbers (0-9) and underscore (_)
- The part after the `sensor.ha_text_ai_` prefix is limited to 50 characters
- No spaces; keep it descriptive but short

#### Sensor Name Structure
```yaml
# Always starts with 'sensor.ha_text_ai_'
# You define only the part after the prefix
sensor.ha_text_ai_YOUR_UNIQUE_SUFFIX

# Examples:
sensor.ha_text_ai_gpt      # GPT-based sensor
sensor.ha_text_ai_claude   # Claude-based sensor
sensor.ha_text_ai_abc      # Custom suffix
```

#### Response Retrieval
```yaml
# Use your specific sensor name
{{ state_attr('sensor.ha_text_ai_gpt', 'response') }}
```

#### Practical Usage
```yaml
automation:
  - alias: "AI Response with Custom Sensor"
    action:
      - service: ha_text_ai.ask_question
        data:
          question: "Home automation advice"
          instance: sensor.ha_text_ai_gpt
      - service: notify.mobile
        data:
          message: >
            AI Tip:
            {{ state_attr('sensor.ha_text_ai_gpt', 'response') }}
```

### HA Text AI Sensor Attributes

- **Model and provider**: current model, API provider, model used for the last response
- **System status**: processing, rate-limit and endpoint state
- **Performance metrics**: request success/failure counters and latency statistics
- **Token usage**: total, prompt and completion token counters as reported by the provider's API
- **Last interaction**: most recent question, response and timestamp
- **System health**: error counter, maintenance flag, uptime and start time

Attributes may be 0 or empty until the first request completes. The sensor writes a new state only when a request starts or finishes, history is cleared or the system prompt changes, so it adds nothing to the recorder database between requests.

<details>
<summary>Detailed Sensor Attributes</summary>

#### Model and Provider Information
```yaml
# Model currently configured for this instance
{{ state_attr('sensor.ha_text_ai_gpt', 'model') }}         # gpt-4o-mini

# Service provider (determines API endpoint and authentication)
{{ state_attr('sensor.ha_text_ai_gpt', 'api_provider') }}  # openai

# Model that produced the last response (may differ after a per-request override)
{{ state_attr('sensor.ha_text_ai_gpt', 'last_model') }}    # gpt-4o-mini
```

#### System Status
```yaml
# Indicates if a request is currently being processed
{{ state_attr('sensor.ha_text_ai_gpt', 'is_processing') }}    # false

# Shows if the API has hit its request rate limit
{{ state_attr('sensor.ha_text_ai_gpt', 'is_rate_limited') }}  # false

# Status of the API endpoint being used
{{ state_attr('sensor.ha_text_ai_gpt', 'endpoint_status') }}  # ready
```

#### Performance Metrics
```yaml
# Number of successfully completed API requests
{{ state_attr('sensor.ha_text_ai_gpt', 'successful_requests') }}  # 42

# Number of API requests that encountered errors
{{ state_attr('sensor.ha_text_ai_gpt', 'failed_requests') }}      # 0

# Average / max / min response time, in seconds
{{ state_attr('sensor.ha_text_ai_gpt', 'average_latency') }}      # 1.85
{{ state_attr('sensor.ha_text_ai_gpt', 'max_latency') }}          # 4.2
{{ state_attr('sensor.ha_text_ai_gpt', 'min_latency') }}          # 0.9
```

#### Conversation and Token Usage
```yaml
# Number of entries in the current history file
{{ state_attr('sensor.ha_text_ai_gpt', 'history_size') }}         # 12

# Token counters as reported by the provider's API
{{ state_attr('sensor.ha_text_ai_gpt', 'total_tokens') }}         # 4520
{{ state_attr('sensor.ha_text_ai_gpt', 'prompt_tokens') }}        # 3100
{{ state_attr('sensor.ha_text_ai_gpt', 'completion_tokens') }}    # 1420

# Last 3 conversation entries, each truncated to 256 characters
# (full history is available via the get_history service)
{{ state_attr('sensor.ha_text_ai_gpt', 'conversation_history') }} # [...]
```

#### Last Interaction Details
```yaml
# Most recent response, truncated to 2048 characters in the attribute
# (the response_variable path returns the full text)
{{ state_attr('sensor.ha_text_ai_gpt', 'response') }}        # Last AI response

# The most recently processed question
{{ state_attr('sensor.ha_text_ai_gpt', 'question') }}        # Last asked question

# When the last interaction occurred
{{ state_attr('sensor.ha_text_ai_gpt', 'last_timestamp') }}  # Timestamp
```

#### System Health
```yaml
# Cumulative count of errors across all requests
{{ state_attr('sensor.ha_text_ai_gpt', 'total_errors') }}    # 0

# Error message of the last failed request (null after a success)
{{ state_attr('sensor.ha_text_ai_gpt', 'last_error') }}      # null

# Maintenance flag
{{ state_attr('sensor.ha_text_ai_gpt', 'is_maintenance') }}  # false

# Seconds since the instance was set up, as of the last state write. Reads 0
# after a restart or an options change until the first request and does not
# tick between requests; homeassistant.update_entity refreshes it on demand
# (one recorder row per call). For a live figure use started_at.
{{ state_attr('sensor.ha_text_ai_gpt', 'uptime') }}          # 547.58

# UTC time the instance was set up (resets on HA restart or entry reload)
{{ state_attr('sensor.ha_text_ai_gpt', 'started_at') }}      # 2026-08-28T20:15:03.876332+00:00

# Live uptime in seconds
{{ (now() - as_datetime(state_attr('sensor.ha_text_ai_gpt', 'started_at'))).total_seconds() }}
```

### History Storage
Conversation history stored in `.storage/ha_text_ai_history/` directory:
- Each instance has its own history file (JSON)
- Files are automatically rotated when size limit is reached
- Archived history files are timestamped
- Default maximum file size: 1MB

</details>

## FAQ

**Q: Which AI providers are supported?**
A: OpenAI, Anthropic, DeepSeek and Google Gemini are built-in providers. OpenRouter and other OpenAI-compatible services work through the OpenAI provider with a custom endpoint.

**Q: How can I reduce API costs?**
A: Use a cheap fast model (GPT-5.6 Luna, Claude Haiku 4.5, deepseek-v4-flash, gemini-3.5-flash) for routine queries, lower `context_messages`, and cap `max_tokens`.

**Q: Are there limitations on the number of requests?**
A: Depends on your API provider's plan. Monitor usage via the sensor attributes and throttle calls with the `request_interval` option.

**Q: Can I use custom models?**
A: Yes, you can configure custom endpoints and use any compatible model by specifying it in the configuration.

**Q: How do I switch between different AI providers?**
A: Each integration instance is bound to one provider. Add a separate instance per provider and pick the instance in your service calls; within an instance you can override the model per request.

**Q: What are the token limits for different models?**
A: Context window sizes vary by provider and model - check your provider's documentation. The `max_tokens` option caps only the response length, not the context window.

**Q: How do I monitor token usage?**
A: Use the sensor attributes `total_tokens`, `prompt_tokens` and `completion_tokens`. You can also create automations to alert you when usage exceeds a threshold.

**Q: Is my data secure?**
A: Conversation history and API keys are stored locally in your Home Assistant instance. Questions and context are sent to the provider you configure over HTTPS; nothing is shared with third parties beyond that provider.

**Q: How do context messages work?**
A: Context messages let the AI reference previous conversation history. By default 5 previous messages are included; you can set 1 to 20 per request to balance conversation depth against token usage.

**Q: Where is conversation history stored?**  
A: History is stored in files under the `.storage/ha_text_ai_history/` directory, with automatic rotation and size management.

**Q: Can I access old conversation history?**  
A: Yes, archived history files are stored with timestamps and can be accessed manually if needed.

**Q: How much history is kept?**  
A: 50 conversations by default, configurable up to 100 in the UI. Files are automatically rotated when they reach 1MB.

## Contributing

Contributions welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

1. Fork the repository
2. Create feature branch (`git checkout -b feature/Enhancement`)
3. Commit changes (`git commit -m 'Add Enhancement'`)
4. Push branch (`git push origin feature/Enhancement`)
5. Open Pull Request

## Legal Disclaimer and Limitation of Liability  

### Software Disclaimer  

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,   
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A   
PARTICULAR PURPOSE AND NONINFRINGEMENT.  

IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,   
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,   
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER   
DEALINGS IN THE SOFTWARE.  

## License

Author: SMKRV
[MIT License](https://opensource.org/licenses/MIT) - see [LICENSE](LICENSE) for details.

## Support the Project

The best support is:
- Sharing feedback
- Contributing ideas
- Recommending to friends
- Reporting issues
- Star the repository

If you want to say thanks financially, you can send a small token of appreciation in USDT:

**USDT Wallet (TRC10/TRC20):**
`TXC9zYHYPfWUGi4Sv4R1ctTBGScXXQk5HZ`

---

<div align="center"><img src="https://github.com/smkrv/ha-text-ai/blob/2aaf3405759eb2d97624834594e24ace896131df/assets/images/icons/footer_icon.png" alt="HA Text AI" style="width: 128px; height: auto;"/></div>  
<div align="center">

Made for the Home Assistant Community

[Report Bug](https://github.com/smkrv/ha-text-ai/issues) · [Request Feature](https://github.com/smkrv/ha-text-ai/issues)

</div>
