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
