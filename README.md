# 🤖 HA text AI Integration for Home Assistant

![GitHub release](https://img.shields.io/github/release/smkrv/ha_text_ai.svg)
![GitHub stars](https://img.shields.io/github/stars/smkrv/ha_text_ai.svg?style=social)
![GitHub forks](https://img.shields.io/github/forks/smkrv/ha_text_ai.svg?style=social)
![GitHub issues](https://img.shields.io/github/issues/smkrv/ha_text_ai.svg)

This is a custom integration for Home Assistant that allows you to interact with OpenAI's text generation models. It provides a sensor entity to track the status of the integration and services to ask questions, view response history, and clear the history. 📊🔍

---

## Features

- **Sensor Entity**: Track the readiness of the HA text AI integration.
- **Ask Question Service**: Submit questions to the AI and receive responses.
- **Clear History Service**: Erase the stored history of questions and responses.
- **Get History Service**: Retrieve the history of recent interactions.
- **Set System Prompt Service**: Configure a system prompt for all future AI questions.

---

## Installation via HACS

1. **Install HACS** (if you haven't already): Follow the [HACS installation guide](https://hacs.xyz/docs/installation/prerequisites/) if you need to install HACS first.
2. **Add HA text AI Integration to HACS**:
    - Open Home Assistant.
    - Navigate to **HACS**.
    - Click on **Integrations**.
    - Click the **Explore & Add Repositories** button (➕).
    - Enter the repository URL: `https://github.com/smkrv/ha_text_ai`
    - Click **Add repository**.
3. **Install**:
    - In the list of available integrations, find **HA text AI**.
    - Click on **Install**.

---

## Manual Installation

1. **Download the repository**:
    - Clone the repository to your Home Assistant’s `config/custom_components` directory.
    ```bash
    git clone https://github.com/smkrv/ha_text_ai.git config/custom_components/ha_text_ai
    ```

2. **Restart Home Assistant**:
    - Go to **Configuration** -> **Server Controls** in Home Assistant and restart your Home Assistant instance.

3. **Configuration**:
    - Navigate to **Configuration** -> **Integrations** in Home Assistant.
    - Click **Add Integration** (➕).
    - Search for **HA text AI** and click **Configure**.
    - Enter your OpenAI API key and other optional settings as prompted.

---

## Configuration Options

- **API Key**: Your OpenAI API key
- **Model**: The OpenAI model to use (default: `gpt-3.5-turbo`)
- **Temperature**: Controls the randomness of the output. Lower values make the output more deterministic (default: `0.7`)
- **Max Tokens**: Maximum length of the response (default: `1000`)
- **API Endpoint**: Custom endpoint URL for the OpenAI API (default: `https://api.openai.com/v1`)
- **Request Interval**: Time interval for polling the API (in seconds, default: `1.0`)

---

## Services

### 1. Ask Question
**Service:** `ha_text_ai.ask_question`
- **Description**: Ask a question to the integrated AI and receive a response.
- **Parameters**:
    - `question`: The question or prompt to send to the AI (required)
    - `model`: Override the default model for this question (optional)
    - `temperature`: Adjust randomness in the response (0.0-1.0, optional)
    - `max_tokens`: Limit the length of the response (optional)

### 2. Clear History
**Service:** `ha_text_ai.clear_history`
- **Description**: Clear the stored history of questions and responses.

### 3. Get History
**Service:** `ha_text_ai.get_history`
- **Description**: Retrieve the history of recent interactions.
- **Parameters**:
    - `limit`: Maximum number of history items to return (default: `10`)

### 4. Set System Prompt
**Service:** `ha_text_ai.set_system_prompt`
- **Description**: Set a system prompt to guide the AI's behavior in future interactions.
- **Parameters**:
    - `prompt`: The system prompt to set (required)

---

## Advanced Usage

- **Sensor State**: The sensor entity `sensor.ha_text_ai` will show `Ready` if the integration is configured and operational, otherwise it will show `Not Ready`.
- **Attributes**: When the sensor state is `Ready`, it provides attributes:
    - `question`: The last question asked.
    - `response`: The response to the last question.
    - `last_updated`: Timestamp of the last successful update from the API.

---

## Logs & Debugging

- To view logs and debug issues, check the Home Assistant logs under **Configuration** -> **Logs**.

---

## Contributing

Feel free to contribute to this project! Open an issue or submit a pull request with any questions, improvements, or bug fixes.

- **Issues**: [github.com/smkrv/ha_text_ai/issues](https://github.com/smkrv/ha_text_ai/issues)
- **Pull Requests**: [github.com/smkrv/ha_text_ai/pulls](https://github.com/smkrv/ha_text_ai/pulls)

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

🚀 Ready to use your AI-powered assistant in Home Assistant? Just set up and start asking questions through the integrated services!
