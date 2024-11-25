# 🤖 HA Text AI for Home Assistant

<div align="center">  

  ![GitHub release](https://img.shields.io/github/release/smkrv/ha-text-ai.svg?style=flat-square) ![GitHub downloads](https://img.shields.io/github/downloads/smkrv/ha-text-ai/total.svg?style=flat-square) ![GitHub stars](https://img.shields.io/github/stars/smkrv/ha-text-ai.svg?style=social) ![GitHub last commit](https://img.shields.io/github/last-commit/smkrv/ha-text-ai.svg?style=flat-square) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT) [![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)

  <img src="https://github.com/smkrv/ha-text-ai/blob/3e3ec45b195c92989434fde40ae110027f4ea124/misc/icons/icon.png" alt="HA Text AI" width="140"/>

### Advanced AI Integration for Home Assistant with multi-provider support
</div>

<p align="center">
Transform your smart home experience with powerful AI assistance powered by multiple AI providers including OpenAI GPT and Anthropic Claude models. Get intelligent responses, automate complex scenarios, and enhance your home automation with advanced natural language processing.
</p>

+-----------------------------------------------------------+
| 🚧 ALPHA VERSION 🚧 |
+-----------------------------------------------------------+
| This is an early development release |
| |
| ⚠️ Expect: |
| - Potential bugs |
| - Frequent changes |
| - Incomplete features |
| |
| 🤝 Community Driven |
+-----------------------------------------------------------+

---

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

- Home Assistant 2023.11 or later
- Active API key from:
  - OpenAI ([Get key](https://platform.openai.com/account/api-keys))
  - Anthropic ([Get key](https://console.anthropic.com/))
  - OpenRouter ([Get OpenRouter API Key](https://openrouter.ai/keys))
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

#### ⚠️ Additional Notes  
- Not all providers guarantee full compatibility  
- Performance may vary between providers  
- Check individual provider's documentation  
- Ensure your API key has sufficient credits/quota

#### ⚠️ Provider Compatibility Requirements  
To be compatible, a provider should support:  
- OpenAI-like REST API structure  
- JSON request/response format  
- Standard authentication method  
- Similar model parameter handling

## ⚡ Installation

### HACS Installation (Recommended)
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
```yaml
ha_text_ai:
  api_provider: openai  # or anthropic
  api_key: !secret ai_api_key
  model: gpt-4o-mini
  temperature: 0.7
  max_tokens: 1000
  request_interval: 1.0
  api_endpoint: https://api.openai.com/v1  # optional, for custom endpoints
  system_prompt: |
    You are a home automation expert assistant.
    Focus on practical and efficient solutions.
```

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

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

Made with ❤️ for the Home Assistant Community

[Report Bug](https://github.com/smkrv/ha-text-ai/issues) · [Request Feature](https://github.com/smkrv/ha-text-ai/issues)

</div>
