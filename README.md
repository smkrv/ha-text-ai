# 🤖 HA Text AI for Home Assistant

<div align="center">

![GitHub release](https://img.shields.io/github/release/smkrv/ha-text-ai.svg?style=flat-square)
![GitHub downloads](https://img.shields.io/github/downloads/smkrv/ha-text-ai/total.svg?style=flat-square)
![GitHub stars](https://img.shields.io/github/stars/smkrv/ha-text-ai.svg?style=social)
![GitHub last commit](https://img.shields.io/github/last-commit/smkrv/ha-text-ai.svg?style=flat-square)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=flat-square)](https://github.com/hacs/integration)
[![Community Forum](https://img.shields.io/badge/Community-Forum-blue.svg?style=flat-square)](https://community.home-assistant.io/t/ha-text-ai-integration)

</div>

<p align="center">
Transform your smart home experience with powerful AI assistance powered by OpenAI's GPT models. Get intelligent responses, automate complex scenarios, and enhance your home automation with natural language processing.
</p>

---

## 🌟 Features

- 🧠 **Advanced AI Integration**:
  - Support for latest GPT models
  - Context-aware responses
  - Multi-turn conversations
- 💬 **Natural Language Control**:
  - Control devices using everyday language
  - Get detailed explanations and recommendations
  - Natural conversation flow
- 📝 **Smart Memory Management**:
  - Persistent conversation history
  - Context-aware responses
  - Customizable history limits
- ⚡ **Performance Optimized**:
  - Efficient token usage
  - Rate limit handling
  - Response caching
- 🎯 **Advanced Customization**:
  - Adjustable response parameters
  - Custom system prompts
  - Model selection per request
- 🔒 **Enhanced Security**:
  - Secure API key storage
  - Rate limiting protection
  - Error handling
- 🎨 **User Experience**:
  - Intuitive configuration UI
  - Detailed sensor attributes
  - Rich service interface
- 🔄 **Automation Integration**:
  - Event-driven responses
  - Conditional logic support
  - Template compatibility

## 📋 Prerequisites

- Home Assistant 2023.8.0 or newer
- OpenAI API key ([Get one here](https://platform.openai.com/account/api-keys))
- Python 3.9 or newer
- Stable internet connection

## ⚡ Installation

### HACS Installation (Recommended)
1. Open HACS in Home Assistant
2. Click the "+" button
3. Search for "HA Text AI"
4. Click "Install"
5. Restart Home Assistant

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
  api_key: !secret openai_api_key
  model: gpt-3.5-turbo
  temperature: 0.7
  max_tokens: 1000
  request_interval: 1.0
  api_endpoint: https://api.openai.com/v1  # optional
```

## 🛠️ Available Services

### ask_question
```yaml
service: ha_text_ai.ask_question
data:
  question: "What's the optimal temperature for sleeping?"
  model: "gpt-4o"  # optional
  temperature: 0.5  # optional
  max_tokens: 500  # optional
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
```

## 🔧 Advanced Examples

### Smart Energy Management
```yaml
automation:
  alias: "AI Energy Optimization"
  trigger:
    platform: time_pattern
    hours: "/2"
  action:
    - service: ha_text_ai.ask_question
      data:
        question: >
          Current power usage: {{ states('sensor.total_power') }}W
          Temperature: {{ states('sensor.indoor_temperature') }}°C
          Time: {{ now().strftime('%H:%M') }}
          Occupancy: {{ states('binary_sensor.occupancy') }}

          Analyze current energy usage and suggest optimizations
          considering comfort and efficiency.
        temperature: 0.3
        max_tokens: 200
    - service: notify.mobile_app
      data:
        message: "{{ states.sensor.ha_text_ai.attributes.response }}"
```

### Contextual Lighting Control
```yaml
automation:
  alias: "AI Lighting Assistant"
  trigger:
    platform: state
    entity_id: binary_sensor.motion
  variables:
    context: >
      Time: {{ now().strftime('%H:%M') }}
      Light Level: {{ states('sensor.illuminance') }}
      Room: {{ trigger.to_state.attributes.room }}
      Activity: {{ states('input_select.current_activity') }}
      Weather: {{ states('weather.home') }}
  action:
    - service: ha_text_ai.ask_question
      data:
        question: >
          Based on this context:
          {{ context }}

          Suggest optimal lighting settings for current conditions.
        model: gpt-3.5-turbo
        temperature: 0.4
    - service: scene.turn_on
      data:
        entity_id: >
          {{ states.sensor.ha_text_ai.attributes.response | regex_findall('scene\.[a-z_]+') | first }}
```

## 📊 Performance Optimization

### Token Usage
- Use focused system prompts
- Implement response caching
- Clear history periodically
- Monitor token usage

### Response Time
- Adjust request_interval
- Use faster models for simple queries
- Implement timeout handling
- Cache frequent responses

### Memory Management
- Set appropriate history limits
- Clear unused contexts
- Monitor memory usage
- Use efficient data structures

## ❗ Troubleshooting

### API Issues
- Verify API key validity
- Check rate limits
- Monitor usage quotas
- Test endpoint accessibility

### Performance Issues
- Reduce max_tokens
- Increase request_interval
- Clear conversation history
- Check network connectivity

### Integration Issues
- Verify HA version compatibility
- Check component dependencies
- Review log files
- Update configuration

## 📘 FAQ

**Q: How can I reduce API costs?**
A: Use GPT-3.5-Turbo for most queries, implement caching, and optimize token usage.

**Q: Is my data secure?**
A: Yes, API keys are stored securely and data is transmitted via encrypted connections.

**Q: Can I use custom models?**
A: Yes, configure custom endpoints and models via configuration options.

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
