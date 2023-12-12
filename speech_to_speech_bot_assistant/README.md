# OpenAI-Powered Telegram Voice Assistant Bot

This Telegram bot is designed to convert voice messages into text using OpenAI's Whisper model, respond to queries via OpenAI's GPT model, and then convert these text responses back into voice messages using text-to-speech (TTS) technology. It's an interactive way to engage with an AI assistant through a familiar messaging platform.

## Features

- **Voice to Text Conversion**: Converts user's voice messages into text using OpenAI's Whisper model.
- **Interaction with OpenAI's GPT Model**: Processes the transcribed text and generates responses using OpenAI's GPT model.
- **Text to Speech**: Converts the AI's text response back into voice messages using TTS.
- **Personalized User Interaction**: Manages separate threads for each user to maintain the context of the conversation.

## Installation

Before you start, ensure you have Python 3.8 or later installed on your system. You will also need to set up a Telegram bot and obtain an API token. 

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/gir2017/tg_bots.git
   cd tg_bots/speech_to_speech_bot_assistant

2. **Install Dependencies:**
   ```bash
    pip install -r requirements.txt

3. **Set up Environment Variables:**
- Create a .env file in the project root.
- Add your Telegram API token and OpenAI API key:
  ```
  TELEGRAM_API_TOKEN=your_telegram_token_here
  OPENAI_API_KEY=your_openai_api_key_here

4. **Run the Bot:**
   ```
   python bot.py
