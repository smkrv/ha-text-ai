# HA Text AI Integration

A Home Assistant integration that provides a bridge to OpenAI-compatible API services with automatic Text Helper management.

## Features

- Easy integration with OpenAI-compatible APIs
- Automatic Text Helper creation for responses
- Support for custom API endpoints
- Built-in rate limiting and queue management
- Blueprint for easy automation setup
- Supports responses up to 65,536 characters

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/ha_text_ai` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings -> Devices & Services
2. Click "Add Integration"
3. Search for "HA Text AI"
4. Enter your configuration:
   - API Key: Your OpenAI API key
   - API Base URL (optional): Custom endpoint for OpenAI-compatible APIs
   - Request Interval: Minimum time between requests (in seconds)

## Usage

### Service Call

You can call the integration using the service `ha_text_ai.text_ai_call`:

```yaml
service: ha_text_ai.text_ai_call
data:
  prompt: "Tell me a joke about home automation"
  response_id: "automation_joke"  # Optional, defaults to "default"
  model: "gpt-3.5-turbo"  # Optional
  temperature: 0.7  # Optional
  max_tokens: 150  # Optional
  top_p: 1.0  # Optional
  frequency_penalty: 0.0  # Optional
  presence_penalty: 0.0  # Optional
```

### Using the Blueprint

1. Go to Settings -> Automations & Scenes
2. Click the "Add Blueprint" button
3. Import this URL: `[Your Repository URL]/blueprints/automation/ha_text_ai_request.yaml`
4. Create a new automation using the blueprint
5. Configure the trigger and prompt template

### Accessing Responses

Responses are automatically stored in Text Helpers with the format `input_text.text_ai_response_[response_id]`

Example template to access a response:
```yaml
{{ states('input_text.text_ai_response_automation_joke') }}
```

## Blueprint Configuration Example

```yaml
trigger_entity: sensor.temperature
prompt_template: "Tell me a joke about {{ states('sensor.temperature') }} degree weather"
response_id: weather_joke
model: gpt-3.5-turbo
temperature: 0.7
max_tokens: 150
```

## Advanced Usage

### Custom API Endpoints

To use with Azure OpenAI or other compatible services, set the API Base URL during configuration:

- Azure OpenAI: `https://your-resource-name.openai.azure.com`
- Other Compatible APIs: Your API endpoint URL

### Rate Limiting

The integration includes built-in rate limiting:
- Requests are queued and processed according to the configured interval
- Default interval is 2 seconds
- Can be adjusted in the integration options

## Troubleshooting

Common issues and solutions:

1. **Response not appearing:**
   - Check if the Text Helper was created (`input_text.text_ai_response_[your_id]`)
   - Verify your API key permissions

2. **API errors:**
   - Check your API key
   - Verify the API endpoint URL
   - Ensure you have sufficient API credits

3. **Rate limiting:**
   - Adjust the request interval in the integration options
   - Check for multiple automations making simultaneous requests

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you have any questions or need help, please:
1. Open an [issue] https://github.com/smkrv/ha-text-ai/issues
