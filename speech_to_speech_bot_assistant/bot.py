import openai
import asyncio
from aiogram import Bot, types, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.dispatcher.router import Router
from aiogram.types import ContentType, FSInputFile
from aiogram.filters import Command
from aiogram import F
from pydub import AudioSegment
import os
from openai import OpenAI
from openai.types.beta.threads import MessageContentText
client = OpenAI()

# Obtain Telegram API token from environment variables
# OpenAI is also an environmental variables
TELEGRAM_API_TOKEN = os.environ["TELEGRAM_API_TOKEN"]

# Initialize bot with Telegram API token and setup dispatcher and router
bot = Bot(token=TELEGRAM_API_TOKEN)
dp = Dispatcher()

storage = MemoryStorage()
router = Router()
dp.include_router(router)

# Dictionary to maintain user states
user_threads = {}

# Send a welcome message when user starts or asks for help
@router.message(Command(commands=["start", "help"]))
async def send_welcome(message: types.Message, state: FSMContext):
    await message.answer("Привет! Отправьте мне голосовое сообщение, и я переведу его в текст.")

# Handler for incoming messages
@router.message()
async def handle_message(message: types.Message, state: FSMContext):
    """
    Handles all incoming messages and routes them based on their type.
    Audio messages are acknowledged, and voice messages are processed further.
    """
    if message.audio:
        await message.answer("Аудио сообщение получено. Пожалуйста, отправьте голосовое сообшение.")
    elif message.voice:
        await handle_voice(message)

    else:
        await message.answer("Другой тип сообщения получен. Пожалуйста, отправьте голосовое сообшение.")

# Handler for voice messages
@router.message()
async def handle_voice(message: types.Message):
    """
    Processes voice messages. Converts the voice message to text,
    sends it to the OpenAI API, and then generates a response.
    The response is converted to speech and sent back to the user.
    """
    transcript, thread_id, file_name, user_folder = await handle_voice_to_text(message)
    response_message = add_message_to_thread(thread_id, transcript)
    if response_message is not None:
        print("Message successfully added to thread.")
        await message.answer("Сообщение обрабатывается. Может занять некоторое время.")
        print(response_message)
    else:
        print("Failed to add message to thread.")
    try:
        output_file_path = await run_message(thread_id, assistant_id, file_name, user_folder)
        print(output_file_path)
        if output_file_path:
            file_to_upload = FSInputFile(output_file_path)
            # Send the speech file as a voice message
            await bot.send_voice(chat_id=message.chat.id, voice=file_to_upload)
            os.remove(output_file_path)
        else:
            await message.answer("Произошла ошибка, попробуйте еще раз.")
    except Exception as e:
        print(f"Failed to handle voice message: {e}")

# Process and convert voice messages to text
async def handle_voice_to_text(message: types.Message):
    """
    Converts a voice message to text using OpenAI's Whisper model.
    It handles the downloading of the voice message file, conversion to MP3,
    and then sends it for transcription.
    """
    user_id = message.from_user.id  # Get user ID
    user_folder = f'./downloads/{user_id}'  # Define user-specific folder

    # Check if user folder exists, if not, create it
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_name = os.path.basename(file.file_path)
    destination_file_path = os.path.join(user_folder, file_name)
    await bot.download_file(file.file_path, destination = destination_file_path)
    file_name_cut = os.path.splitext(file_name)[0]
    mp3_filename = file_name_cut + '.mp3'
    audio = AudioSegment.from_file(destination_file_path)
    mp3_file_path = os.path.join(user_folder, mp3_filename)
    audio.export(mp3_file_path, format='mp3')


    audio_file = open(mp3_file_path, "rb")
    transcript = openai.OpenAI().audio.transcriptions.create(
    model="whisper-1", 
    file=audio_file, 
    response_format="text"
    )

    # create separate thread for each user
    thread_id = thread_creating(user_id)

    # removing temporary files
    os.remove(destination_file_path)
    os.remove(mp3_file_path)
    return transcript, thread_id, file_name_cut, user_folder

# Create new thread for each user
def thread_creating(user_id):
    """
    Manages threads for each user. If a user does not have an existing thread,
    a new one is created. This is used to handle conversations in OpenAI.
    """
    # Check if a thread for this user already exists, else create one
    if user_id not in user_threads:
        thread = client.beta.threads.create()  # Create a new thread
        user_threads[user_id] = thread.id  # Store thread ID

    # Use the thread ID for this user's conversation
    thread_id = user_threads[user_id]
    return thread_id

# Add message to OpenAI thread
def add_message_to_thread(thread_id, transcript):
    """
    Adds a transcribed message to the OpenAI thread for processing.
    This is part of the conversation handling with OpenAI.
    """
    try:
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=transcript
        )
        return message
    except Exception as e:
        print(f"Failed to add message to thread: {e}")
        return None

# Run and manage message threads    
async def run_message(thread_id, assistant_id, file_name, user_folder):
    """
    Check the OpenAI run status.
    After getting a response, it converts the response text to speech.
    """
    try:
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        print('Message has been run')
        run_id = run.id
        await message_status(run_id, thread_id)
        response_ai = get_response(thread_id)
        output_file_path = text_to_speech(response_ai, file_name, user_folder)
        return output_file_path
    except Exception as e:
        print(f"Failed to run message: {e}")

# Check message status
async def message_status(run_id, thread_id):
    """
    Monitors the status of the processing message in the OpenAI thread.
    Checks the status periodically until a final status is reached.
    """
    # check openai response status
    total_time = 0
    final_run_status = ['completed', 'expired', 'cancelled', 'failed']
    # First 20 seconds, check every 2 seconds
    while total_time < 20:
        await asyncio.sleep(2)
        run = client.beta.threads.runs.retrieve(
        thread_id=thread_id,
        run_id=run_id
        )
        print(f"Checking status: {run.status}")
        total_time += 2
        if run.status in final_run_status:
            break

    # Next 30 seconds, check every 5 seconds
    while total_time < 50 and run.status not in final_run_status:
        await asyncio.sleep(5)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        print(f"Checking status: {run.status}")
        total_time += 5
        if run.status in final_run_status:
            break

    # Remaining time (up to 260 seconds), check every 15 seconds
    while total_time < 260 and run.status not in final_run_status:
        await asyncio.sleep(15)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        print(f"Checking status: {run.status}")
        total_time += 15
        if run.status in final_run_status:
            break

# Retrieve responses from OpenAI thread    
def get_response(thread_id):
    """
    Retrieves responses from the OpenAI thread. It gathers all messages
    and compiles the text responses.
    """
    messages = client.beta.threads.messages.list(
    thread_id=thread_id
    )

    response_messages = []
    message = messages.data[0]
    for content in message.content:
        if isinstance(content, MessageContentText):
            response_messages.append(content.text.value)

    response_text = "\n".join(response_messages)
    return response_text

# Convert response text to speech and save as OGG file    
def text_to_speech(response_text, file_name, user_folder):
    """
    Converts the response text from OpenAI to speech using TTS.
    The speech is saved as an OGG file which is then sent back to the user.
    """
    # Path for the intermediate MP3 file
    mp3_file_path = os.path.join(user_folder, f'{file_name}.mp3')

    # Path for the final OGG file
    ogg_file_path = os.path.join(user_folder, f'{file_name}.ogg')

    # Create TTS MP3 file
    response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input=response_text
    )
    response.stream_to_file(mp3_file_path)

    # Convert MP3 to OGG
    audio = AudioSegment.from_mp3(mp3_file_path)
    audio.export(ogg_file_path, format='ogg')

    # Optionally, remove the intermediate MP3 file
    os.remove(mp3_file_path)

    return ogg_file_path

# Create assistant
def create_assistant():
    """
    Creates an instance of the OpenAI assistant. This assistant is used to
    process and respond to user messages.
    """
    try:
        my_assistant = client.beta.assistants.create(
        instructions="You should answer like a bro",
        name="bro_speaking_bot",
        tools=[{"type": "code_interpreter"}],
        model="gpt-4",
        )
        assistant_id = my_assistant.id
        print(my_assistant)
        print(my_assistant.id)
        return assistant_id
    except Exception as e:
        print(f"Failed to create assistant: {e}")
        return None

# Main function to start the bot
async def main():
    # Check if './downloads' folder exists, if not, create it
    if not os.path.exists('./downloads'):
        os.makedirs('./downloads')

    global assistant_id
    assistant_id = create_assistant()
    if assistant_id is None:
        print("Assistant creation failed. Exiting.")
        return
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
