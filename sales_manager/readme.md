# LinkedIn Proposal Bot for Telegram

### Description

This Telegram bot is designed to generate business proposals based on LinkedIn company profiles. Users simply provide a LinkedIn company profile URL, and the bot utilizes AI to create a tailored business proposal.

### Features

- LinkedIn URL Processing: Parses LinkedIn company profile URLs to gather necessary company information.
- AI-Generated Proposals: Uses advanced AI techniques to generate business proposals based on company data.
- Error Handling: Custom exceptions for handling specific errors like personal LinkedIn URL inputs or other LinkedIn related errors.
  
### Installation

#### Follow these steps to set up the bot locally:

1. Clone the Repository:
- git clone https://github.com/gir2017/tg_bots.git
- cd ./tg_bots/sales_manager/

2. Install Dependencies:
pip install -r requirements.txt

3. Set Up Environment Variables:
Create a .env file and define the following variables:
- TELEGRAM_API_TOKEN=your_telegram_bot_token
- NUBELA_API_KEY=your_nubela_api_key
- COHERE_API_KEY=your_cohere_api_key

4. Start the Bot:
- python3 bot.py

### Usage
After launching the bot, users can interact with it on Telegram by sending a /start command and following the instructions to input a LinkedIn company profile URL.
