import requests
from aiogram import Bot, Dispatcher, types
import asyncio
from aiogram.filters import CommandStart#, Text
import json
import os

TELEGRAM_API_TOKEN = os.environ["TELEGRAM_API_TOKEN"]
NUBELA_API_KEY = os.environ["NUBELA_API_KEY"]
COHERE_API_KEY = os.environ["COHERE_API_KEY"]

# Initialize bot with token from config
bot = Bot(token=TELEGRAM_API_TOKEN)
dp = Dispatcher()

# Custom exceptions for specific errors
class PersonalURLError(Exception):
    """Exception raised for errors in the input URL (personal LinkedIn URL instead of company URL)."""
    pass

class OtherLinkedinError(Exception):
    """General exception for LinkedIn related errors."""
    pass

class OfferGenerationError(Exception):
    """Exception raised for errors during offer generation."""
    pass

# Handler for /start command
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    """
    Handler for /start command. Sends a welcome message and instructions.
    """
    await message.answer("Привет! Отправьте мне ссылку на LinkedIn профиль компании, и я создам предложение для потенциального клиента.")

# # Обработчик команды /help
# @dp.message(Text(commands=['help']))
# async def send_help(message: types.Message):
#     await message.answer("Отправьте мне ссылку на LinkedIn, и я подготовлю предложение.")


# Function for parsing LinkedIn
def parse_linkedin(url):
    """
    Parses the LinkedIn profile data from a given URL.

    :param url: LinkedIn company profile URL
    :return: Parsed JSON data of the company profile
    :raises PersonalURLError: If the URL is of a personal LinkedIn profile
    :raises OtherLinkedinError: For other LinkedIn related errors
    """
    response = requests.get(f'https://nubela.co/proxycurl/api/linkedin/company?url={url}&resolve_numeric_id=false&use_cache=if-present',
                            headers={'Authorization': f'Bearer {NUBELA_API_KEY}'})
    if response.status_code == 200:
        return response.json()
    
    if response.status_code == 400 and 'description' in response.json():
        description = response.json()['description']

    if 'LinkedIn Person URLs' in description:
        raise PersonalURLError
    else:
        raise OtherLinkedinError(description)

def prompt_creation(profile_data):
    """
    Creates a custom prompt for the offer generation based on the company profile data.

    :param profile_data: Dictionary containing profile data of the company
    :return: Generated prompt as a string
    """
    company_name = profile_data['name']
    if company_name:
        final_prompt = f'Create a proposal for the {company_name} company from HappyAI to introduce AI into its business.'
    else:
        return "Данные LinkedIn не содержат название компании."
    
    industry = profile_data['industry']
    specialities = profile_data['specialities']
    description = profile_data['description']
    company_size = profile_data['company_size']
    
    if industry and specialities:
        final_prompt += f' Take into account the company industry ({industry}) and some of specialities: {", ".join(specialities)}.'
    elif industry:
        final_prompt += f' Take into account the company industry ({industry}).'
    elif specialities:
        final_prompt += f' Take into account some of company specialities: {", ".join(specialities)}.' 

    if description:
        if len(description) > 1350:
            description = trim_description(description)
        final_prompt += f' Also you can use a description of company: {description}.'
    if company_size:
        final_prompt += f' Take into account company size ({company_size[0]}).'
    
    final_prompt += f' Introduce yourself like a Head of Business Department of HappyAI company. Try to fit into 350 tokens. Use company name {company_name} for greetings.'
    return final_prompt

def trim_description(description, max_length=1350):
    """
    Trims the company description to a specified length by cutting off sentences.

    :param description: The original company description
    :param max_length: Maximum length of the trimmed description
    :return: Trimmed company description
    """
    # Splitting the description into sentences
    sentences = description.split('.')
    trimmed_description = ""
    total_length = 0

    # Adding sentences until the maximum length is reached
    for sentence in sentences:
        # Considering the length of the sentence including a dot and a space
        sentence_length = len(sentence) + 1

        # Checking if the total length exceeds the maximum allowed
        if total_length + sentence_length > max_length:
            break

        # Adding the sentence to the result
        trimmed_description += sentence + '.'
        total_length += sentence_length

    return trimmed_description

async def create_offer(message: types.Message, profile_data):
    """
    Generates an offer based on the company profile data.

    :param message: The original message object from aiogram
    :param profile_data: Dictionary containing profile data of the company
    :return: Generated offer as a string
    :raises OfferGenerationError: If the offer generation fails
    """
    text = prompt_creation(profile_data)
    url = "https://api.cohere.ai/v1/generate"

    payload = json.dumps({
    "truncate": "END",
    "return_likelihoods": "NONE",
    "max_tokens": 1000,
    "prompt": text})
    headers = {
    'accept': 'application/json',
    'authorization': f'Bearer {COHERE_API_KEY}',
    'content-type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    if response.status_code == 200:
        return response.json()['generations'][0]['text'].replace("[Your Name]", "")
    else:
        raise OfferGenerationError

@dp.message()
async def generate_offer(message: types.Message):
    """
    Main handler for generating an offer. It takes a message with a LinkedIn URL, processes it,
    and sends back the generated offer or an error message.

    :param message: The message object from aiogram
    """
    await message.answer("Обработка вашего запроса может занять несколько секунд...")
    linkedin_url = message.text
    try:
        profile_data = parse_linkedin(linkedin_url)
        offer = await create_offer(message, profile_data)
    except PersonalURLError:
        await message.answer('Бот принимает только LinkedIn страницы компаний, а не персональные страницы.')
    except OtherLinkedinError as e:
        await message.answer('Произошла ошибка, попробуйте заново: ' + e.args[0])
    except OfferGenerationError:
        await message.answer("Не удалось сгенерировать предложение. Попробуйте заново.")

    await message.answer(offer)


# Main function to start the bot
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
