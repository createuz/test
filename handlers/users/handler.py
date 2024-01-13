import re, time
from aiogram.dispatcher import FSMContext
from aiogram.types import InputMediaPhoto, InputMediaVideo, InlineKeyboardButton, InlineKeyboardMarkup, ContentType
from utlis.models import *
import keyboards
from data import *
from instagram.api import InstagramAPI

instagram_api = InstagramAPI()


@dp.message_handler(commands=['start'], chat_type=types.ChatType.PRIVATE)
async def start_handler_lang(message: types.Message):
    await message.delete()
    try:
        language = await User.get_language(message.chat.id)
        if language:
            await bot.send_message(message.chat.id, text=f"<b>{keyboards.select_dict[language]}</b>",
                                   reply_markup=keyboards.keyboard_group[language],
                                   disable_web_page_preview=True, protect_content=True)
        else:
            await bot.send_message(message.chat.id, text=keyboards.choose_button,
                                   reply_markup=keyboards.language_keyboard,
                                   protect_content=True)
            await LanguageSelection.select_language.set()
    except Exception as e:
        logger.exception("Error while processing start command: %s", e)


@dp.callback_query_handler(lambda c: c.data in keyboards.languages.keys(), state=LanguageSelection.select_language,
                           chat_type=types.ChatType.PRIVATE)
async def process_language_selection(callback_query: types.CallbackQuery, state: FSMContext):
    selected_language = callback_query.data
    chat_id = callback_query.message.chat.id
    username = callback_query.message.chat.username
    first_name = callback_query.from_user.first_name
    language = keyboards.languages[selected_language]
    created_add = datetime.now()
    try:
        await User.create_user(chat_id, username, first_name, language, created_add)
        await state.finish()
        await bot.answer_callback_query(callback_query.id)
        callback_id = callback_query.message.message_id
        await bot.edit_message_text(chat_id=chat_id, message_id=callback_id,
                                    text=f"<b>{keyboards.select_dict[language]}</b>",
                                    reply_markup=keyboards.keyboard_group[language], disable_web_page_preview=True)
    except Exception as e:
        logger.exception("Error while processing language selection: %s", e)


@dp.message_handler(commands=['lang'], chat_type=types.ChatType.PRIVATE)
async def change_language_handler(message: types.Message):
    chat_id = message.chat.id
    await message.delete()
    try:
        await bot.send_message(chat_id, text=keyboards.choose_button, reply_markup=keyboards.language_keyboard,
                               protect_content=True)
        await LanguageChange.select_language.set()
    except Exception as e:
        await bot.send_message(message.chat.id,
                               "You haven't selected a language yet. Please use the /start command to select a language.",
                               protect_content=True)


@dp.callback_query_handler(lambda c: c.data in keyboards.languages.keys(), state=LanguageChange.select_language,
                           chat_type=types.ChatType.PRIVATE)
async def process_change_language(callback_query: types.CallbackQuery, state: FSMContext):
    selected_language = callback_query.data
    chat_id = callback_query.message.chat.id
    language = keyboards.languages[selected_language]
    try:
        await User.update_language(chat_id, language)
        await state.finish()
        await bot.answer_callback_query(callback_query.id)
        callback_id = callback_query.message.message_id
        await bot.edit_message_text(chat_id=chat_id, message_id=callback_id,
                                    text=f"<b>{keyboards.select_dict[language]}</b>",
                                    reply_markup=keyboards.keyboard_group[language], disable_web_page_preview=True)
    except Exception as e:
        logger.exception("Error while changing language preference: %s", e)


@dp.message_handler(commands=['help'])
async def help_handler(message: types.Message):
    await message.delete()
    try:
        if message.chat.type != types.ChatType.PRIVATE:
            language = await Group.get_language(message.chat.id)
            await bot.send_message(message.chat.id, text=keyboards.help_dict[language], disable_web_page_preview=True,
                                   protect_content=True)
        else:
            language = await User.get_language(message.chat.id)
            await bot.send_message(message.chat.id, text=f"<b>{keyboards.help_dict[language]}</b>",
                                   disable_web_page_preview=True, protect_content=True)
    except Exception as e:
        logger.exception("Error while processing start command: %s", e)


@dp.message_handler(regexp=r'https?:\/\/(www\.)?instagram\.com\/(reel|p)\/([-_a-zA-Z0-9]{11})',
                    chat_type=types.ChatType.PRIVATE)
async def send_instagram_media(message: types.Message):
    global waiting_msg, delete_msg
    link = message.text
    language = await User.get_language(message.chat.id)
    await message.delete()
    # match = re.search(r'https://www.instagram.com/(?:p|reel)/([-_a-zA-Z0-9]{11})', link)
    # vid = match.group(1) if match else None
    try:
        cached_data = instagram_api.cache.get(link, {})
        if cached_data.get('timestamp', 0) >= time.time() - 2629746:
            media = cached_data.get('result')
            return await bot.send_media_group(chat_id=message.chat.id, media=media)
        waiting_msg = await bot.send_message(chat_id=message.chat.id,
                                             text=f"<b>📥 {keyboards.keyboard_waiting[language]}</b>",
                                             protect_content=True)
        # urls = await instagram_api.instagram_downloader(vid=vid)
        urls = await instagram_api.instagram_downloader_stories(link=link)
        if urls is None or not urls:
            await waiting_msg.delete()
            return await bot.send_message(message.chat.id, text=keyboards.down_err[language].format(link),
                                          disable_web_page_preview=True, protect_content=True)
        media = [InputMediaPhoto(url) if 'jpg' in url else InputMediaVideo(url) for url in urls]
        media[-1].caption = f"<b>📥 {main_caption}{keyboards.keyboard_saver[language]}</b>"
        await bot.send_media_group(chat_id=message.chat.id, media=media)
        await waiting_msg.delete()
        instagram_api.cache[link] = {'result': media, 'timestamp': time.time()}
    except Exception as e:
        await waiting_msg.delete()
        logger.exception("Error while sending Instagram photo: %s", e)
        return await bot.send_message(message.chat.id, text=keyboards.down_err[language].format(link),
                                      disable_web_page_preview=True, protect_content=True)


@dp.message_handler(regexp=r'https?:\/\/(www\.)?instagram\.com\/(stories)', chat_type=types.ChatType.PRIVATE)
async def send_instagram_media(message: types.Message):
    link = message.text
    # match = re.search(r'https?://(?:www\.)?instagram\.com/(?:stories/)?([a-zA-Z0-9_.]+)/?', link)
    # username = match.group(1) if match else None
    await message.delete()
    language = await User.get_language(message.chat.id)
    waiting_msg = await bot.send_message(chat_id=message.chat.id,
                                         text=f"<b>📥 {keyboards.keyboard_waiting[language]}</b>", protect_content=True)
    try:
        urls = await instagram_api.instagram_downloader_stories(link=link)
        if urls is None or not urls:
            await waiting_msg.delete()
            return await bot.send_message(message.chat.id, text=keyboards.down_err[language].format(link),
                                          disable_web_page_preview=True, protect_content=True)
        media_groups = [urls[i:i + 10] for i in range(0, len(urls), 10)]
        for group in media_groups:
            media = [InputMediaPhoto(url) if 'jpg' in url else InputMediaVideo(url) for url in group]
            media[-1].caption = f"📥 <b>{main_caption}{keyboards.keyboard_saver[language]}</b>"
            await bot.send_media_group(chat_id=message.chat.id, media=media)
        await waiting_msg.delete()
    except Exception as e:
        logger.exception("Error while sending Instagram photo: %s", )
        await waiting_msg.delete()
        return await bot.send_message(message.chat.id, text=keyboards.down_err[language].format(link),
                                      disable_web_page_preview=True, protect_content=True)


@dp.message_handler(lambda message: message.text.startswith('@'))
async def insta_user_handler(message: types.Message):
    await message.delete()
    language = await User.get_language(message.chat.id)
    try:
        image, user = await instagram_api.instagram_user_data(language=language, link=message.text)
        if not image or not user:
            return await bot.send_message(message.chat.id, '🛑 Instagram foydalanuvchisi mavjuda emas!')
        delete_kb = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton(text='🔻', callback_data=f"bekor_qilish"))
        await bot.send_photo(message.chat.id, photo=image, caption=user, reply_markup=delete_kb)
    except Exception as e:
        logger.exception("Error while processing start command: %s", e)


@dp.message_handler(commands=['username'])
async def insta_user_handler(message: types.Message):
    await message.delete()
    try:
        await bot.send_message(message.chat.id,
                               text=f"<b>Instagram user haqida kuproq malumot olishni istasangiz foydalanuvchi @username'ni yuboring.</b>")
    except Exception as e:
        logger.exception("Error while processing start command: %s", e)
