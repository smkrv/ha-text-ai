# 🤖 HA Text AI for Home Assistant

<div align="center">

![GitHub release](https://img.shields.io/github/release/smkrv/ha-text-ai.svg?style=flat-square)
![GitHub downloads](https://img.shields.io/github/downloads/smkrv/ha-text-ai/total.svg?style=flat-square)
![GitHub stars](https://img.shields.io/github/stars/smkrv/ha-text-ai.svg?style=social)
![GitHub last commit](https://img.shields.io/github/last-commit/smkrv/ha-text-ai.svg?style=flat-square)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

</div>

<p align="center">
Transform your smart home experience with powerful AI assistance powered by OpenAI's GPT models
</p>

---

## 🌟 Features

- 🧠 **Advanced AI Integration**: Leverage OpenAI's powerful models (GPT-3.5, GPT-4) for smart home interactions
- 💬 **Natural Language Control**: Control your home and get information using everyday language
- 📝 **Conversation Memory**: Maintain context with conversation history tracking
- ⚡ **Real-time Responses**: Get quick, contextual responses to your queries
- 🎯 **Customizable Behavior**: Fine-tune AI responses with adjustable parameters
- 🔒 **Secure Integration**: Your API key and data are handled securely
- 🎨 **Flexible Configuration**: Easy setup with multiple configuration options
- 🔄 **Automation Ready**: Integrate AI responses into your automations

## 📋 Prerequisites

- Home Assistant installation (Core, OS, Container, or Supervised)
- OpenAI API key ([Get one here](https://platform.openai.com/account/api-keys))
- Python 3.9 or newer

## ⚡ Quick Start

### Manual Installation
1. Download the repository
2. Copy `custom_components/ha_text_ai` to your `custom_components` directory
3. Restart Home Assistant
4. Add configuration to `configuration.yaml`:
```yaml
ha_text_ai:
  api_key: !secret openai_api_key
```

## ⚙️ Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `api_key` | string | Required | Your OpenAI API key |
| `model` | string | `gpt-3.5-turbo` | AI model to use |
| `temperature` | float | `0.7` | Response creativity (0-2) |
| `max_tokens` | integer | `1000` | Maximum response length |
| `request_interval` | float | `1.0` | Minimum seconds between requests |
| `api_endpoint` | string | OpenAI default | Custom API endpoint URL |

## 🛠️ Available Services

### ask_question
Ask the AI assistant a question:
```yaml
service: ha_text_ai.ask_question
data:
  question: "What's the optimal temperature for sleeping?"
  model: "gpt-4"  # optional
  temperature: 0.5  # optional
  max_tokens: 500  # optional
```

### set_system_prompt
Configure AI behavior:
```yaml
service: ha_text_ai.set_system_prompt
data:
  prompt: "You are a home automation expert focused on energy efficiency"
```

### clear_history
Reset conversation history:
```yaml
service: ha_text_ai.clear_history
```

### get_history
Retrieve conversation history:
```yaml
service: ha_text_ai.get_history
data:
  limit: 5  # optional
```

## 🔧 Practical Examples

### Smart Temperature Management
```yaml
automation:
  trigger:
    platform: time_pattern
    hours: "/1"
  action:
    service: ha_text_ai.ask_question
    data:
      question: >
        Current temperature is {{ states('sensor.living_room_temperature') }}°C.
        Should I adjust the thermostat for optimal comfort and energy savings?
```

### Smart Lighting Assistant
```yaml
automation:
  trigger:
    platform: state
    entity_id: binary_sensor.living_room_motion
    to: 'on'
  condition:
    condition: template
    value_template: "{{ states('sensor.illuminance') | float < 10 }}"
  action:
    service: ha_text_ai.ask_question
    data:
      question: >
        Motion detected in living room with low light levels.
        What's the best lighting scene to set based on the time of day?
```

## ❗ Common Issues

### API Rate Limits
- Increase `request_interval` if hitting rate limits
- Consider upgrading your OpenAI plan
- Use caching for frequent queries

### High Token Usage
- Reduce `max_tokens` parameter
- Clear conversation history regularly
- Use focused system prompts

### Connection Issues
- Check internet connectivity
- Verify API key validity
- Ensure endpoint accessibility

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made with ❤️ for the Home Assistant Community

</div>
