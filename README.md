# 🤖 HA Text AI for Home Assistant

<div align="center">  

  ![GitHub release](https://img.shields.io/github/v/release/smkrv/ha-text-ai?style=flat-square) ![GitHub last commit](https://img.shields.io/github/last-commit/smkrv/ha-text-ai?style=flat-square) [![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg?style=flat-square)](https://creativecommons.org/licenses/by-nc-sa/4.0/) [![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
  ![Deutsch](https://img.shields.io/badge/lang-DE-blue?style=flat-square) ![English](https://img.shields.io/badge/lang-EN-blue?style=flat-square) ![Español](https://img.shields.io/badge/lang-ES-blue?style=flat-square) ![हिन्दी](https://img.shields.io/badge/lang-HI-blue?style=flat-square) ![Italiano](https://img.shields.io/badge/lang-IT-blue?style=flat-square) ![Русский](https://img.shields.io/badge/lang-RU-blue?style=flat-square) ![Српски](https://img.shields.io/badge/lang-SR-blue?style=flat-square) ![中文](https://img.shields.io/badge/lang-ZH-blue?style=flat-square)


  <img src="https://github.com/smkrv/ha-text-ai/blob/main/custom_components/ha_text_ai/icons/logo%402x.png" alt="HA Text AI" style="width: 50%; max-width: 256px; max-height: 128px; aspect-ratio: 2/1; object-fit: contain;"/>

### Advanced AI Integration for [Home Assistant](https://www.home-assistant.io/) with LLM multi-provider support
</div>

<p align="center">
Transform your smart home experience with powerful AI assistance powered by multiple AI providers including OpenAI GPT, Anthropic Claude, DeepSeek and Google Gemini models. Get intelligent responses, automate complex scenarios, and enhance your home automation with advanced natural language processing.

</p>

---

> [!IMPORTANT]
> 🤝 Community Driven: for more details on the integration,   
> check out the discussion on the **[Home Assistant Community forum](https://community.home-assistant.io/t/ha-text-ai-transforming-home-automation-through-multi-llm-integration/799741)**
>
>  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=smkrv&repository=ha-text-ai&category=Integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" width="210" height="auto"></a>
>  
> [Screenshots](assets/images/screenshots/screenshot.jpg)

## 🌟 Features

- 🧠 **Multi-Provider AI Integration**: Support for OpenAI GPT, Anthropic Claude, DeepSeek and Google Gemini models
- 💬 **Advanced Language Processing**: Context-aware, multi-turn conversations
- 📝 **Enhanced Memory Management**: Secure file-based history storage
- ⚡ **Performance Optimization**: Efficient token usage and smart rate limiting
- 🎯 **Advanced Customization**: Per-request model and parameter selection
- 🔒 **Enhanced Security**: Secure API key management and usage monitoring
- 🎨 **Improved User Experience**: Intuitive configuration and rich interfaces
- 🔄 **Automation Integration**: Event-driven responses and template compatibility

<details>
<summary>📦 Detailed Feature Breakdown</summary>

### 🧠 **Multi-Provider AI Integration**
- Support for OpenAI GPT models
- Anthropic Claude integration
- DeepSeek integration
- Google Gemini integration
- Custom API endpoints
- Flexible model selection

### 💬 **Advanced Language Processing**
- Context-aware responses
- Multi-turn conversations
- Custom system instructions
- Natural conversation flow

### 📝 **Enhanced Memory Management**
- File-based conversation history storage
- Automatic history rotation
- Configurable history size limits
- Secure storage in Home Assistant

### ⚡ **Performance Optimization**
- Efficient token usage
- Smart rate limiting
- Response caching
- Request interval control

### 🎯 **Advanced Customization**
- Per-request model selection
- Adjustable parameters
- Custom system prompts
- Temperature control

### 🔒 **Enhanced Security**
- Secure API key storage
- Rate limiting protection
- Error handling
- Usage monitoring

### 🎨 **Improved User Experience**
- Intuitive configuration UI
- Detailed sensor attributes
- Rich service interface
- Model selection UI

### 🔄 **Automation Integration**
- Event-driven responses
- Conditional logic support
- Template compatibility
- Model-specific automation

</details>

#### 🌐 Translations

| Code | Language | Status |
|------|----------|--------|
| 🇩🇪 de | Deutsch | Full |
| 🇬🇧 en | English | Primary |
| 🇪🇸 es | Español | Full |
| 🇮🇳 hi | हिन्दी | Full |
| 🇮🇹 it | Italiano | Full |
| 🇷🇺 ru | Русский | Full |
| 🇷🇸 sr | Српски | Full |
| 🇨🇳 zh | 中文 | Full |

## 📋 Prerequisites

- Home Assistant 2024.12.0 or later (recommended for best compatibility)
- Active API key from:
  - OpenAI ([Get key](https://platform.openai.com/account/api-keys))
  - Anthropic ([Get key](https://console.anthropic.com/))
  - DeepSeek ([Get key](https://platform.deepseek.com/api_keys))
  - OpenRouter ([Get key](https://openrouter.ai/keys))
  - Google Gemini 🆕 ([Get key](https://ai.google.dev/gemini-api/docs/api-key)) thanks to ([@Azzedde](https://github.com/Azzedde))
  - Any OpenAI-compatible API provider
- Python 3.9 or newer
- Stable internet connection

## Configuration Options

### 🔧 **Core Configuration Settings**
- 🌐 **API Provider**: OpenAI/Anthropic/DeepSeek/Gemini
- 🔑 **API Key**: Provider-specific authentication
- 🤖 **Model Selection**: Flexible, provider-specific models
- 🌡️ **Temperature**: Creativity control (0.0-2.0)
- 📏 **Max Tokens**: Response length limit (passed directly to the LLM API to control the maximum length of the response)
- ⏱️ **Request Interval**: API call throttling
- 💾 **History Size**: Number of messages to retain
- 🌍 **Custom API Endpoint**: Optional advanced configuration

### 🤖 **Recommended Models**

#### OpenAI Models
- **GPT-5** - The latest flagship model, best for complex reasoning
- **GPT-5 mini** - A cost-effective and fast model, suitable for most tasks

#### Anthropic Claude Models
- **Claude Opus 4.6** - The most capable model for handling complex tasks
- **Claude Sonnet 4.6** - Offers a balance between performance and cost
- **Claude Haiku 4.5** - The fastest and most economical option in the series

#### DeepSeek Models
- **DeepSeek-V3** - A general-purpose model for a wide range of tasks
- **DeepSeek-R1** - A specialized model focused on reasoning and coding

#### Google Gemini Models
- **Gemini 3.1 Pro** - The newest and most advanced model available
- **Gemini 3.1 Flash Lite** - Fastest and most cost-efficient model for high-volume workloads

<details>
<summary>🌐 Potentially Compatible Providers</summary>

#### Flexible Provider Ecosystem
The integration is designed to be flexible and may work with other providers offering OpenAI-compatible APIs:
- Groq
- Together AI
- Perplexity AI
- Mistral AI
- Google AI
- Local AI servers (like Ollama)
- Custom OpenAI-compatible endpoints

#### 🚨 Compatibility Notes
- Not all providers guarantee full compatibility
- Performance may vary between providers
- Check individual provider's documentation
- Ensure your API key has sufficient credits/quota

#### 🔍 Provider Compatibility Requirements
To be compatible, a provider should support:
- OpenAI-like REST API structure
- JSON request/response format
- Standard authentication method
- Similar model parameter handling

</details>

## ⚡ Installation

### HACS Installation (Recommended)
>[!TIP]
>HA Text AI is available in the default HACS repository. You can install it directly through HACS or click the button below to open it there.

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=smkrv&repository=ha-text-ai&category=Integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" width="170" height="auto"></a>
1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Search for "HA Text AI"
4. Click "Download"
5. Restart Home Assistant

**Alternative Method (Custom Repository):**
If the integration is not found in the default repository:
1. Click "..." in top right corner of HACS
2. Select "Custom repositories"
3. Add repository URL: `https://github.com/smkrv/ha-text-ai`
4. Choose "Integration" as category
5. Click "Download"

### Manual Installation
1. Download the latest release
2. Extract and copy `custom_components/ha_text_ai` to your `custom_components` directory
3. Restart Home Assistant
4. Add configuration via UI (Settings → Devices & Services → Add Integration)

## ⚙️ Configuration

### Via UI (Recommended)
1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "HA Text AI"
4. Follow the configuration steps

> **Note:** This integration is configured exclusively through the UI (config entries). YAML configuration is not supported.

## 🛠️ Available Services

### 🔄 Response Variables (New!)

**HA Text AI now supports response variables** - a powerful feature that returns AI responses directly from service calls, eliminating the need for separate text sensors and the 255-character limitation!

#### ✨ Key Benefits:
- **Unlimited response length** - No more 255-character truncation
- **Direct data access** - Get responses immediately in automations
- **Race condition prevention** - Eliminates conflicts in parallel automations
- **Simplified workflows** - No need to read from sensors

### ask_question
```yaml
service: ha_text_ai.ask_question
data:
  question: "What's the optimal temperature for sleeping?"
  model: "claude-sonnet-4-6-20260217"  # optional
  temperature: 0.5  # optional
  max_tokens: 500  # optional
  context_messages: 10  #optional, number of previous messages to include in context, default: 5
  system_prompt: "You are a sleep optimization expert"  # optional
  instance: sensor.ha_text_ai_gpt
response_variable: ai_response  # NEW! Store response data directly
```

#### 📊 Response Data Structure:
```yaml
# The service returns structured data:
response_text: "The optimal sleeping temperature is 65-68°F (18-20°C)..."
tokens_used: 150
prompt_tokens: 50
completion_tokens: 100
model_used: "claude-sonnet-4-6-20260217"
instance: "sensor.ha_text_ai_gpt"
question: "What's the optimal temperature for sleeping?"
timestamp: "2025-02-09T16:57:00.000Z"
success: true
# error: "Error message" (only present if success: false)
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
  limit: 5  # optional, number of conversations to return (1-100)
  filter_model: "gpt-4o"  # optional, filter by specific AI model
  start_date: "2025-02-01"  # optional, filter conversations from this date
  include_metadata: false  # optional, include tokens, response time, etc.
  sort_order: "newest"  # optional, sort order: "newest" or "oldest"
  instance: sensor.ha_text_ai_gpt
```

## 🚀 Advanced Automation Examples with Response Variables

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
          title: "🏠 Smart Home Tip"
          message: |
            {{ ai_advice.response_text }}
            
            📊 Tokens used: {{ ai_advice.tokens_used }}
            🤖 Model: {{ ai_advice.model_used }}
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
              title: "❄️ Winter Preparation Advice"
              message: |
                {{ winter_advice.response_text }}
                
                Generated at: {{ winter_advice.timestamp }}
        else:
          - service: persistent_notification.create
            data:
              title: "⚠️ AI Service Error"
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
      
      # Step 3: Send comprehensive report
      - service: notify.telegram
        data:
          title: "🏠 Home Analysis Report"
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

### 💡 Migration from Sensors to Response Variables

#### Old Method (Limited):
```yaml
# ❌ Old way - limited to 255 characters, race conditions
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
          message: "{{ state_attr('sensor.ha_text_ai_gpt', 'response')[:255] }}..."  # Truncated!
```

#### New Method (Unlimited):
```yaml
# ✅ New way - unlimited length, immediate access, no race conditions
automation:
  - alias: "New AI Response Method"
    action:
      - service: ha_text_ai.ask_question
        data:
          question: "Long question here..."
          instance: sensor.ha_text_ai_gpt
        response_variable: ai_response  # Direct access!
      - service: notify.mobile
        data:
          message: "{{ ai_response.response_text }}"  # Full response, no truncation!
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

### 💡 Naming Rules
- Prefix is always `sensor.ha_text_ai_`
- Add your unique identifier after the underscore
- Use lowercase
- No spaces allowed
- Keep it descriptive but concise

### 🔍 HA Text AI Sensor Attributes

- 🤖 **Model and Provider Information**: Tracking current AI model and service provider
- 🚦 **System Status**: Real-time API and processing readiness
- 📊 **Performance Metrics**: Request success rates and response times
- 💬 **Conversation Tracking**: Token usage and interaction history are estimated using a heuristic method based on word count and specific word characteristics, which may differ from actual token usage.
- 🕒 **Last Interaction Details**: Recent query and response tracking
- ❤️ **System Health**: Error monitoring and service uptime

<details>
<summary>📦 Detailed Sensor Attributes</summary>

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

# Number of entries in current history file
{{ state_attr('sensor.ha_text_ai_gpt', 'History size') }}          # 0  

# Last few conversation entries (last 5 for performance)
{{ state_attr('sensor.ha_text_ai_gpt', 'conversation_history') }}  # [...]
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

### History Storage
Conversation history stored in `.storage/ha_text_ai_history/` directory:
- Each instance has its own history file (JSON)
- Files are automatically rotated when size limit is reached
- Archived history files are timestamped
- Default maximum file size: 1MB

### 💡 Pro Tips
- Always check attribute existence
- Use these attributes for monitoring and automation
- Some values might be 0 or empty initially

</details>

## 📘 FAQ

**Q: Which AI providers are supported?**
A: OpenAI (GPT models), Anthropic (Claude models), DeepSeek, Google Gemini, and OpenRouter are officially supported, with many other OpenAI-compatible providers working as well.

**Q: How can I reduce API costs?**
A: Use gpt-5-mini or claude-haiku-4-5 for most queries, implement caching, and optimize token usage.

**Q: Are there limitations on the number of requests?**
A: Depends on your API provider's plan. We recommend monitoring usage and implementing request throttling via `request_interval` configuration.

**Q: Can I use custom models?**
A: Yes, you can configure custom endpoints and use any compatible model by specifying it in the configuration.

**Q: How do I switch between different AI providers?**
A: Simply change the model parameter in your configuration or service calls to use the desired provider's model.

**Q: What are the token limits for different models?**
A: Token limits vary by provider and model. OpenAI's GPT-5 supports up to 1M context tokens, Claude Opus 4.6 supports up to 1M tokens, Gemini 3.1 Pro supports up to 1M tokens, while smaller models typically have 128K-200K limits. Check your provider's documentation for specific limits.

**Q: How do I monitor token usage?**
A: Use the sensor attributes like `Total tokens`, `Prompt tokens`, and `Completion tokens` to track usage. You can also create automations to alert you when usage exceeds certain thresholds.

**Q: Is my data secure?**
A: Yes, your data is secure. The system operates entirely on your local machine, keeping your data under your control. API keys are stored securely and all external communications use encrypted connections.

**Q: How do context messages work?**
A: Context messages allow the AI to remember and reference previous conversation history. By default, 5 previous messages are included, but you can customize this from 1 to 20 messages to control the conversation depth and token usage.

**Q: Where is conversation history stored?**  
A: History is stored in files under the `.storage/ha_text_ai_history/` directory, with automatic rotation and size management.

**Q: Can I access old conversation history?**  
A: Yes, archived history files are stored with timestamps and can be accessed manually if needed.

**Q: How much history is kept?**  
A: By default, up to 50 conversations are stored (max 200), configurable via UI. Files are automatically rotated when they reach 1MB.

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

<div align="center"><img src="https://github.com/smkrv/ha-text-ai/blob/2aaf3405759eb2d97624834594e24ace896131df/assets/images/icons/footer_icon.png" alt="HA Text AI" style="width: 128px; height: auto;"/></div>  
<div align="center">

Made with ❤️ for the Home Assistant Community

[Report Bug](https://github.com/smkrv/ha-text-ai/issues) · [Request Feature](https://github.com/smkrv/ha-text-ai/issues)

</div>
 
