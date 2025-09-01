# Using response_variable with HA Text AI

After updating the HA Text AI integration, it now supports using the `response_variable` parameter in Home Assistant scripts and automations.

## What Changed

- Added response schema support in the `ha_text_ai.ask_question` service
- Service is now correctly registered with `supports_response=True` flag
- You can now use `response_variable` to capture AI response in a variable

## Example Usage in Script

```yaml
action: ha_text_ai.ask_question
data:
  context_messages: 0
  temperature: 0.7
  max_tokens: 1000
  instance: sensor.ha_text_ai_gemini
  question: "What time is it?"
response_variable: ai_response
```

## Example Usage in Automation

```yaml
alias: "Get AI Response"
trigger:
  - platform: state
    entity_id: input_boolean.ask_ai
    to: "on"
action:
  - action: ha_text_ai.ask_question
    data:
      instance: sensor.ha_text_ai_gemini
      question: "What's the current weather?"
      temperature: 0.7
      max_tokens: 500
    response_variable: weather_response
  
  - action: notify.persistent_notification
    data:
      title: "AI Response"
      message: "{{ weather_response.response_text }}"
```

## Available Fields in response_variable

When you use `response_variable`, you will receive an object with the following fields:

- `response_text` (string) - The AI response text
- `tokens_used` (integer) - Total number of tokens used
- `prompt_tokens` (integer) - Number of tokens in the prompt
- `completion_tokens` (integer) - Number of tokens in the completion
- `model_used` (string) - The AI model that was used for the response
- `instance` (string) - The instance name that was used
- `question` (string) - The original question that was asked
- `timestamp` (string) - ISO timestamp when the response was generated
- `success` (boolean) - Whether the request was successful
- `error` (string) - Error message if the request failed

## Example Using Response Fields

```yaml
action:
  - action: ha_text_ai.ask_question
    data:
      instance: sensor.ha_text_ai_gemini
      question: "Tell me a joke"
    response_variable: joke_response
  
  - condition: template
    value_template: "{{ joke_response.success }}"
  
  - action: input_text.set_value
    target:
      entity_id: input_text.last_ai_response
    data:
      value: "{{ joke_response.response_text }}"
  
  - action: input_number.set_value
    target:
      entity_id: input_number.tokens_used
    data:
      value: "{{ joke_response.tokens_used }}"
```

## Error Handling

```yaml
action:
  - action: ha_text_ai.ask_question
    data:
      instance: sensor.ha_text_ai_gemini
      question: "Test question"
    response_variable: ai_result
  
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ ai_result.success }}"
        sequence:
          - action: notify.mobile_app_phone
            data:
              title: "AI Response"
              message: "{{ ai_result.response_text }}"
      - conditions:
          - condition: template
            value_template: "{{ not ai_result.success }}"
        sequence:
          - action: notify.mobile_app_phone
            data:
              title: "AI Error"
              message: "Error: {{ ai_result.error }}"
```

## Migration from Old Approach

**Old method (without response_variable):**
```yaml
# Ask question
- action: ha_text_ai.ask_question
  data:
    instance: sensor.ha_text_ai_gemini
    question: "Hello!"

# Wait and read response from sensor
- delay: 00:00:05
- action: notify.mobile_app_phone
  data:
    message: "{{ states('sensor.ha_text_ai_gemini') }}"
```

**New method (with response_variable):**
```yaml
# Ask question and get response immediately
- action: ha_text_ai.ask_question
  data:
    instance: sensor.ha_text_ai_gemini
    question: "Hello!"
  response_variable: greeting_response

- action: notify.mobile_app_phone
  data:
    message: "{{ greeting_response.response_text }}"
```

The new approach is more reliable as it doesn't require waiting and reading from the sensor.
