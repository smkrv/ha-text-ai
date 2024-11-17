# HA text AI

This is a Home Assistant custom integration that allows you to interact with OpenAI's API and compatible endpoints to generate AI responses.

## Features

- Configure all settings through the Home Assistant UI
- Support for OpenAI API and compatible endpoints
- Configurable parameters (temperature, max tokens, etc.)
- Request queue system to prevent API rate limiting
- Long response storage
- Multiple parallel questions support
- Real-time updates

## Installation

### HACS Installation
1. Go to HACS in your Home Assistant installation
2. Click on "Integrations"
3. Click the "+" button
4. Search for "HA text AI"
5. Click "Install"
6. Restart Home Assistant

### Manual Installation
1. Copy the `custom_components/ha_text_ai` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Configuration -> Integrations
2. Click "+" to add a new integration
3. Search for "HA text AI"
4. Enter your OpenAI API key and configure other settings

## Usage

### Service Calls
You can use the `ha_text_ai.ask_question` service to ask questions:

```yaml
service: ha_text_ai.ask_question
data:
  question: "What is the weather like today?"
```

### Automation Example
```yaml
automation:
  - alias: "Daily Weather Question"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      - service: ha_text_ai.ask_question
        data:
          question: "What's the weather forecast for today?"
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `api_key` | Your OpenAI API key | Required |
| `model` | The AI model to use | gpt-3.5-turbo |
| `temperature` | Response randomness (0-1) | 0.7 |
| `max_tokens` | Maximum response length | 1000 |
| `api_endpoint` | Custom API endpoint | https://api.openai.com/v1 |
| `request_interval` | Minimum time between requests | 1.0 |

## Support

For bugs and feature requests, please create an issue on GitHub.

## License

This project is licensed under the MIT License.
```
