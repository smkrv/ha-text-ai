# 🤖 HA text AI Integration for Home Assistant

<div align="center">

![GitHub release](https://img.shields.io/github/release/smkrv/ha-text-ai.svg)
![GitHub stars](https://img.shields.io/github/stars/smkrv/ha-text-ai.svg?style=social)
![GitHub forks](https://img.shields.io/github/forks/smkrv/ha-text-ai.svg?style=social)
![GitHub issues](https://img.shields.io/github/issues/smkrv/ha-text-ai.svg)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

<p align="center">
Powerful OpenAI integration for Home Assistant enabling natural language interaction with your smart home
</p>

---

## 📋 Table of Contents
- [Features](#-features)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Services](#-services)
- [Advanced Usage](#-advanced-usage)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

## ✨ Features

- 🔄 **Real-time AI Interaction**: Seamless communication with OpenAI's latest models
- 📝 **Conversation History**: Track and manage your AI interactions
- ⚙️ **Customizable Settings**: Fine-tune AI behavior with adjustable parameters
- 🔌 **Easy Integration**: Simple setup process through HACS or manual installation
- 🎯 **System Prompts**: Set context for more relevant AI responses

## 🚀 Installation

### HACS Installation (Recommended)
1. Ensure [HACS](https://hacs.xyz/) is installed
2. Search for "HA text AI" in HACS
3. Click Install
4. Restart Home Assistant

<details>
<summary>Manual Installation Steps</summary>

```bash
# 1. Navigate to your Home Assistant configuration directory
cd ~/.homeassistant

# 2. Create custom_components directory if it doesn't exist
mkdir -p custom_components

# 3. Clone the repository
git clone https://github.com/smkrv/ha-text-ai.git custom_components/ha-text-ai

# 4. Restart Home Assistant
```
</details>

## ⚙️ Configuration

### Basic Configuration
```yaml
ha-text-ai:
  api_key: your_openai_api_key
  model: gpt-3.5-turbo
```

### Advanced Configuration
```yaml
ha-text-ai:
  api_key: your_openai_api_key
  model: gpt-4
  temperature: 0.8
  max_tokens: 2000
  api_endpoint: https://custom-endpoint.com/v1
  request_interval: 2.0
```

## 🛠 Services

### Ask Question
```yaml
service: ha-text-ai.ask_question
data:
  question: "What's the weather like today?"
  model: "gpt-4"  # optional
  temperature: 0.7  # optional
```

### More Services
- `ha-text-ai.clear_history`: Reset conversation history
- `ha-text-ai.get_history`: Retrieve past interactions
- `ha-text-ai.set_system_prompt`: Configure AI behavior

## 🔍 Advanced Usage

### Automation Example
```yaml
automation:
  trigger:
    platform: state
    entity_id: binary_sensor.motion
    to: 'on'
  action:
    service: ha-text-ai.ask_question
    data:
      question: "What should I do when motion is detected?"
```

## 🔧 Troubleshooting

<details>
<summary>Common Issues and Solutions</summary>

### API Key Issues
- Verify API key format
- Check API key permissions
- Ensure proper configuration in secrets.yaml

### Connection Problems
- Verify internet connection
- Check API endpoint accessibility
- Review Home Assistant logs
</details>

## 👥 Contributing

We welcome contributions! Here's how you can help:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Submit a pull request

---

<div align="center">

**[Documentation](https://github.com/smkrv/ha-text-ai/wiki)** | **[Report Bug](https://github.com/smkrv/ha-text-ai/issues)** | **[Request Feature](https://github.com/smkrv/ha-text-ai/issues)**

</div>
