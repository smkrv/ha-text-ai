# 🤖 HA Text AI for Home Assistant

<div align="center">  

![GitHub release](https://img.shields.io/github/release/smkrv/ha-text-ai.svg?style=flat-square) ![GitHub last commit](https://img.shields.io/github/last-commit/smkrv/ha-text-ai.svg?style=flat-square) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT) [![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration) ![/README.md](https://img.shields.io/badge/language-English-green?style=flat-square) ![/README_RU.md](https://img.shields.io/badge/language-Russian-green?style=flat-square) ![](https://img.shields.io/badge/language-Deutch-green?style=flat-square)

  <img src="https://github.com/smkrv/ha-text-ai/blob/524849f6a945ec62c2cf6a6b7ecd9a28b37bf0fa/misc/icons/logo.jpg" alt="HA Text AI" height="160"/>

### Advanced AI Integration for [Home Assistant](https://www.home-assistant.io/) with LLM multi-provider support
</div>

<p align="center">
Transform your smart home experience with powerful AI assistance powered by multiple AI providers including OpenAI GPT and Anthropic Claude models. Get intelligent responses, automate complex scenarios, and enhance your home automation with advanced natural language processing.

</p>

---

> [!IMPORTANT]
> 🚧 ALPHA VERSION 🚧  
> Expect: potential bugs, frequent changes, incomplete features.  
> 🤝 Community Driven  
>
>  <a href="https://community.home-assistant.io/t/ha-text-ai-transforming-home-automation-with-multi-provider-language-models/799741"><img src="https://img.shields.io/badge/Community-blue?style=for-the-badge&logo=homeassistant&logoColor=white&color=03a9f4"/></a>  
>  
> [Screenshots](misc/screenshots/screenshot.jpg)

## 🌟 Features

- 🧠 **Multi-Provider AI Integration**:
  - Support for OpenAI GPT models
  - Anthropic Claude integration
  - Custom API endpoints
  - Flexible model selection

- 💬 **Advanced Language Processing**:
  - Context-aware responses
  - Multi-turn conversations
  - Custom system instructions
  - Natural conversation flow

- 📝 **Enhanced Memory Management**:
  - Persistent conversation history
  - Context-aware responses
  - Customizable history limits
  - Model-specific filtering

- ⚡ **Performance Optimization**:
  - Efficient token usage
  - Smart rate limiting
  - Response caching
  - Request interval control

- 🎯 **Advanced Customization**:
  - Per-request model selection
  - Adjustable parameters
  - Custom system prompts
  - Temperature control

- 🔒 **Enhanced Security**:
  - Secure API key storage
  - Rate limiting protection
  - Error handling
  - Usage monitoring

- 🎨 **Improved User Experience**:
  - Intuitive configuration UI
  - Detailed sensor attributes
  - Rich service interface
  - Model selection UI

- 🔄 **Automation Integration**:
  - Event-driven responses
  - Conditional logic support
  - Template compatibility
  - Model-specific automation

## 📋 Prerequisites

- Home Assistant 2024.11 or later
- Active API key from:
  - OpenAI ([Get key](https://platform.openai.com/account/api-keys))
  - Anthropic ([Get key](https://console.anthropic.com/))
  - OpenRouter ([Get key](https://openrouter.ai/keys))
- Python 3.9 or newer
- Stable internet connection

### Configuration Options
- API Provider (OpenAI/Anthropic)
- API Key (provider-specific)
- Model Selection (flexible, provider-specific models)
- Temperature (Creativity control, 0.0-2.0)
- Max Tokens (Response length limit)
- Request Interval (API call throttling)
- Custom API Endpoint (optional)

#### ⓘ Potentially Compatible Providers  
The integration is designed to be flexible and may work with other providers offering OpenAI-compatible APIs:  
- Groq  
- Together AI  
- Perplexity AI  
- Mistral AI  
- Google AI  
- Local AI servers (like Ollama)  
- Custom OpenAI-compatible endpoints  

#### Additional Notes  
- Not all providers guarantee full compatibility  
- Performance may vary between providers  
- Check individual provider's documentation  
- Ensure your API key has sufficient credits/quota

#### Provider Compatibility Requirements  
To be compatible, a provider should support:  
- OpenAI-like REST API structure  
- JSON request/response format  
- Standard authentication method  
- Similar model parameter handling

## ⚡ Installation

### HACS Installation (Recommended)
<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=smkrv&repository=ha-text-ai&category=Integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" width="170" height="auto"></a>
1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click "..." in top right corner
4. Select "Custom repositories"
5. Add repository URL: `https://github.com/smkrv/ha-text-ai`
6. Choose "Integration" as category
7. Click "Download"
8. Restart Home Assistant

### Manual Installation
1. Download the latest release
2. Extract and copy `custom_components/ha_text_ai` to your `custom_components` directory
3. Restart Home Assistant
4. Add configuration via UI or YAML

## ⚙️ Configuration

### Via UI (Recommended)
1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "HA Text AI"
4. Follow the configuration steps

### Via YAML

### Platform Configuration (Global Settings)

```yaml
ha_text_ai:
  api_provider: openai  # Required
  api_key: !secret ai_api_key  # Required
  model: gpt-4o-mini  # Strongly recommended
  temperature: 0.7  # Optional
  max_tokens: 1000  # Optional
  request_interval: 1.0  # Optional
  api_endpoint: https://api.openai.com/v1  # Required
  system_prompt: |  # Optional
    You are a home automation expert assistant.
    Focus on practical and efficient solutions.
```

### Sensor Configuration

```yaml
sensor:
  - platform: ha_text_ai
    name: "My AI Assistant"  # Required, unique identifier
    api_provider: openai  # Optional (inherits from platform)
    model: "gpt-4o-mini"  # Optional
    temperature: 0.7  # Optional
    max_tokens: 1000  # Optional
```

### 📋 Configuration Parameters

#### Platform Configuration

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `api_provider` | String | ✅ | - | AI service provider (openai, anthropic) |
| `api_key` | String | ✅ | - | Authentication key for AI service |
| `model` | String | ⚠️ | Provider default | Strongly recommended: Specific AI model to use. If not specified, the provider's default model will be used |
| `temperature` | Float | ❌ | 0.7 | Response creativity level (0.0-2.0) |
| `max_tokens` | Integer | ❌ | 1000 | Maximum response length |
| `request_interval` | Float | ❌ | 1.0 | Delay between API requests |
| `api_endpoint` | URL | ⚠️ | Provider default | Custom API endpoint |
| `system_prompt` | String | ❌ | - | Default context for AI interactions |

#### Sensor Configuration

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `platform` | String | ✅ | - | Must be `ha_text_ai` |
| `name` | String | ✅ | - | Unique sensor identifier |
| `api_provider` | String | ❌ | Platform setting | Override global provider |
| `model` | String | ⚠️ | Platform setting | Recommended: Override global model. If not specified, uses platform or provider default |
| `temperature` | Float | ❌ | Platform setting | Override global temperature |
| `max_tokens` | Integer | ❌ | Platform setting | Override global max tokens |

## 🛠️ Available Services

### ask_question
```yaml
service: ha_text_ai.ask_question
data:
  question: "What's the optimal temperature for sleeping?"
  model: "claude-3-sonnet"  # optional
  temperature: 0.5  # optional
  max_tokens: 500  # optional
  context_messages: 10  #optional, number of previous messages to include in context, default: 5
  system_prompt: "You are a sleep optimization expert"  # optional
```

### set_system_prompt
```yaml
service: ha_text_ai.set_system_prompt
data:
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
```

### get_history
```yaml
service: ha_text_ai.get_history
data:
  limit: 5  # optional
  filter_model: "gpt-4o"  # optional
```

### 🏷️ HA Text AI Sensor Naming Convention

#### Character Restrictions  
- Only lowercase letters (a-z)  
- Numbers (0-9)  
- Underscore (_)  
- Maximum length: 50 characters (including `ha_text_ai_`)

#### Sensor Name Structure
```yaml
# Always starts with 'sensor.ha_text_ai_'
# You define only the part after the underscore
sensor.ha_text_ai_YOUR_UNIQUE_SUFFIX

# Examples:
sensor.ha_text_ai_gpt      # GPT-based sensor
sensor.ha_text_ai_claude   # Claude-based sensor
sensor.ha_text_ai_gpt   # Custom suffix
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
      - service: notify.mobile
        data:
          message: >
            AI Tip:
            {{ state_attr('sensor.ha_text_ai_gpt', 'response') }}
```

### 💡 Naming Rules
- Prefix is always `sensor.ha_text_ai_`
- Add your unique identifier after the underscore
- Use lowercase
- No spaces allowed
- Keep it descriptive but concise

### 🔍 HA Text AI Sensor Attributes

#### Model and Provider Information
```yaml
# Name of the AI model currently in use (e.g., latest version of GPT)  
{{ state_attr('sensor.ha_text_ai_gpt', 'Model') }}           # gpt-4o  

# Service provider for the AI model (determines API endpoint and authentication)  
{{ state_attr('sensor.ha_text_ai_gpt', 'Api provider') }}    # openai  

# Previous or alternative model configuration  
{{ state_attr('sensor.ha_text_ai_gpt', 'Last model') }}      # gpt-4o
```

#### System Status
```yaml
# Current operational readiness of the AI service API  
{{ state_attr('sensor.ha_text_ai_gpt', 'Api status') }}      # ready  

# Indicates if a request is currently being processed  
{{ state_attr('sensor.ha_text_ai_gpt', 'Is processing') }}   # false  

# Shows if the API has hit its request rate limit  
{{ state_attr('sensor.ha_text_ai_gpt', 'Is rate limited') }} # false  

# Status of the specific API endpoint being used  
{{ state_attr('sensor.ha_text_ai_gpt', 'Endpoint status') }} # ready
```

#### Performance Metrics
```yaml
# Total number of successfully completed API requests  
{{ state_attr('sensor.ha_text_ai_gpt', 'Successful requests') }}   # 0  

# Number of API requests that encountered errors  
{{ state_attr('sensor.ha_text_ai_gpt', 'Failed requests') }}       # 0  

# Mean time taken to receive a response from the AI service  
{{ state_attr('sensor.ha_text_ai_gpt', 'Average latency') }}       # 0  

# Maximum time taken for a single request-response cycle  
{{ state_attr('sensor.ha_text_ai_gpt', 'Max latency') }}           # 0
```

#### Conversation and Token Usage
```yaml
# Number of previous interactions stored in conversation context  
{{ state_attr('sensor.ha_text_ai_gpt', 'History size') }}          # 0  

# Total number of tokens used across all interactions  
{{ state_attr('sensor.ha_text_ai_gpt', 'Total tokens') }}          # 0  

# Tokens used in the input prompts  
{{ state_attr('sensor.ha_text_ai_gpt', 'Prompt tokens') }}         # 0  

# Tokens used in the AI's generated responses  
{{ state_attr('sensor.ha_text_ai_gpt', 'Completion tokens') }}     # 0
```

#### Last Interaction Details
```yaml
# Most recent complete response generated by the AI service  
{{ state_attr('sensor.ha_text_ai_gpt', 'Response') }}        # Last AI response  

# The most recently processed user query or prompt  
{{ state_attr('sensor.ha_text_ai_gpt', 'Question') }}        # Last asked question  

# Precise moment when the last interaction occurred (useful for tracking and logging)  
{{ state_attr('sensor.ha_text_ai_gpt', 'Last timestamp') }}  # Timestamp
```

#### System Health
```yaml
# Cumulative count of all errors encountered during AI service interactions  
{{ state_attr('sensor.ha_text_ai_gpt', 'Total errors') }}    # 0  

# Indicates if the AI service is currently undergoing scheduled or emergency maintenance  
{{ state_attr('sensor.ha_text_ai_gpt', 'Is maintenance') }}  # false  

# Total continuous operational time of the AI service (in hours or days)  
{{ state_attr('sensor.ha_text_ai_gpt', 'Uptime') }}          # 547,58
```

### 💡 Pro Tips
- Always check attribute existence
- Use these attributes for monitoring and automation
- Some values might be 0 or empty initially


## 📘 FAQ

**Q: Which AI providers are supported?**
A: Currently OpenAI (GPT models) and Anthropic (Claude models) are supported, with more providers planned.

**Q: How can I reduce API costs?**
A: Use GPT-3.5-Turbo or Claude-3-Sonnet for most queries, implement caching, and optimize token usage.

**Q: Are there limitations on the number of requests?**
A: Depends on your API provider's plan. We recommend monitoring usage and implementing request throttling via `request_interval` configuration.

**Q: Can I use custom models?**
A: Yes, you can configure custom endpoints and use any compatible model by specifying it in the configuration.

**Q: How do I switch between different AI providers?**
A: Simply change the model parameter in your configuration or service calls to use the desired provider's model.

**Q: How can I reduce API costs?**
A: Use GPT-3.5-Turbo for most queries, implement caching, and optimize token usage.

**Q: Is my data secure?**
A: Yes, your data is secure. The system operates entirely on your local machine, keeping your data under your control. API keys are stored securely and all external communications use encrypted connections.

**Q: How do context messages work?**
A: Context messages allow the AI to remember and reference previous conversation history. By default, 5 previous messages are included, but you can customize this from 1 to 20 messages to control the conversation depth and token usage.

## 🤝 Contributing

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

## 📝 License

Author: SMKRV
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) - see [LICENSE](LICENSE) for details. 

## 💡 Support the Project

The best support is:
- Sharing feedback
- Contributing ideas
- Recommending to friends
- Reporting issues
- Star the repository

If you want to say thanks financially, you can send a small token of appreciation in USDT:

**USDT Wallet (TRC10/TRC20):**
`TXC9zYHYPfWUGi4Sv4R1ctTBGScXXQk5HZ`

*Open-source is built by community passion!* 🚀

---

<div align="center">

Made with ❤️ and Claude 3.5 Sonnet for the Home Assistant Community

[Report Bug](https://github.com/smkrv/ha-text-ai/issues) · [Request Feature](https://github.com/smkrv/ha-text-ai/issues)

</div>
