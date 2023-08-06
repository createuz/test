from keyboards import *
from states import *
from downloader import *
from databasedb.models import *
from loader import *
from aiogram import types


@dp.message_handler(commands=['start'], chat_type=types.ChatType.PRIVATE)
async def start_handler_lang(message: types.Message):
    try:
        language = await User.get_language(message.chat.id)
        if language:
            await bot.send_message(message.from_id, text=f"<b>{select_dict[language]}</b>",
                                   reply_markup=keyboard_group[language],
                                   disable_web_page_preview=True)
        else:
            await bot.send_message(message.chat.id, text=choose_button, reply_markup=language_keyboard)
            await LanguageSelection.select_language.set()
    except Exception as e:
        logger.exception("Error while processing start command: %s", e)


@dp.callback_query_handler(lambda c: c.data in languages.keys(), state=LanguageSelection.select_language,
                           chat_type=types.ChatType.PRIVATE)
async def process_language_selection(callback_query: types.CallbackQuery, state: FSMContext):
    selected_language = callback_query.data
    chat_id = callback_query.message.chat.id
    username = callback_query.message.chat.username
    first_name = callback_query.from_user.first_name
    language = languages[selected_language]
    try:
        await User.create_user(chat_id, username, first_name, language)
        await state.finish()
        await bot.answer_callback_query(callback_query.id)
        callback_id = callback_query.message.message_id
        await bot.edit_message_text(chat_id=chat_id, message_id=callback_id, text=f"<b>{select_dict[language]}</b>",
                                    reply_markup=keyboard_group[language], disable_web_page_preview=True)
    except Exception as e:
        logger.exception("Error while processing language selection: %s", e)


@dp.message_handler(commands=['lang'], chat_type=types.ChatType.PRIVATE)
async def change_language_handler(message: types.Message):
    chat_id = message.chat.id
    try:
        await bot.send_message(chat_id, text=choose_button, reply_markup=language_keyboard)
        await LanguageChange.select_language.set()
    except Exception as e:
        await bot.send_message(message.chat.id,
                               "You haven't selected a language yet. Please use the /start command to select a language.")


@dp.callback_query_handler(lambda c: c.data in languages.keys(), state=LanguageChange.select_language,
                           chat_type=types.ChatType.PRIVATE)
async def process_change_language(callback_query: types.CallbackQuery, state: FSMContext):
    selected_language = callback_query.data
    chat_id = callback_query.message.chat.id
    language = languages[selected_language]
    try:
        await User.update_language(chat_id, language)
        await state.finish()
        await bot.answer_callback_query(callback_query.id)
        callback_id = callback_query.message.message_id
        await bot.edit_message_text(chat_id=chat_id, message_id=callback_id, text=f"<b>{select_dict[language]}</b>",
                                    reply_markup=keyboard_group[language], disable_web_page_preview=True)
    except Exception as e:
        logger.exception("Error while changing language preference: %s", e)


@dp.message_handler(commands=['help'])
async def help_handler(message: types.Message):
    try:
        if message.chat.type != types.ChatType.PRIVATE:
            language = await Group.get_language(message.chat.id)
            await bot.send_message(message.chat.id, text=help_dict[language], disable_web_page_preview=True)
        else:
            language = await User.get_language(message.chat.id)
            await bot.send_message(message.chat.id, text=f"<b>{help_dict[language]}</b>",
                                   disable_web_page_preview=True)
    except Exception as e:
        logger.exception("Error while processing start command: %s", e)


@dp.message_handler(regexp=r'https?:\/\/(www\.)?instagram\.com\/(reel|p|tv)\/([-_a-zA-Z0-9]{11})',
                    chat_type=types.ChatType.PRIVATE)
async def send_instagram_media(message: types.Message):
    link = message.text
    try:
        language = await User.get_language(message.chat.id)
        insta_data = await InstagramMediaDB.get_video_url(message.text)
        if insta_data:
            media = [InputMediaPhoto(url) if 'jpg' in url else InputMediaVideo(url) for url in insta_data]
            media[-1].caption = f"📥 <b>{main_caption}{keyboard_saver[language]}</b>"
            await bot.send_media_group(chat_id=message.chat.id, media=media)
            await message.delete()
        else:
            await message.delete()
            waiting_msg = await bot.send_message(chat_id=message.chat.id,
                                                 text=f"<b>📥 {keyboard_waiting[language]}</b>")
            async with aiohttp.ClientSession() as session:
                urls = await instagram_downloader_photo_video(link, session=session)
                media = [InputMediaPhoto(url) if 'jpg' in url else InputMediaVideo(url) for url in
                         urls]
                media[-1].caption = f"<b>📥 {main_caption}{keyboard_saver[language]}</b>"
                await bot.send_media_group(chat_id=message.chat.id, media=media)
            await waiting_msg.delete()
            await InstagramMediaDB.create_media_list(message.text, urls)
    except Exception as e:
        logger.exception("Error while sending Instagram photo: %s", e)


# @dp.message_handler(state=InstaUserData.waiting_user_data, content_types=ContentType.TEXT)
# async def callback_inline(message: types.Message, state: FSMContext):
#     try:
#         language = await User.get_language(message.chat.id)
#         async with aiohttp.ClientSession() as session:
#             profile_photo, user_data = await insta_user_data(language, message.text.replace('@', ''), session)
#             if profile_photo:
#                 stories_keyboard = InlineKeyboardMarkup(row_width=2)
#                 stories_btn = InlineKeyboardButton(text="Stories yuklash", callback_data="stories_yuklash")
#                 stories_keyboard.add(stories_btn)
#                 await bot.send_photo(message.chat.id, photo=profile_photo, caption=user_data)
#             else:
#                 stories_keyboard = InlineKeyboardMarkup(row_width=2)
#                 stories_btn = InlineKeyboardButton(text="Stories yuklash", callback_data="stories_yuklash")
#                 stories_keyboard.add(stories_btn)
#                 await bot.send_message(message.chat.id, text=user_data)
#             await state.finish()
#     except Exception as e:
#         await bot.delete_message(message.chat.id, message_id=message.message_id)
#         logger.exception("Error while sending Instagram photo: %s", e)


@dp.message_handler(regexp=r'https?:\/\/(www\.)?instagram\.com\/(stories)', chat_type=types.ChatType.PRIVATE)
async def send_instagram_media(message: types.Message):
    link = message.text
    await message.delete()
    try:
        language = await User.get_language(message.chat.id)
        waiting_msg = await bot.send_message(chat_id=message.chat.id,
                                             text=f"<b>📥 {keyboard_waiting[language]}</b>")
        async with aiohttp.ClientSession() as session:
            urls = await instagram_downloader_photo_video(link, session=session)
            media_groups = [urls[i:i + 10] for i in range(0, len(urls), 10)]
            for group in media_groups:
                media = [InputMediaPhoto(url) if 'jpg' in url else InputMediaVideo(url) for url in group]
                media[-1].caption = f"📥 <b>{main_caption}{keyboard_saver[language]}</b>"
                await bot.send_media_group(chat_id=message.chat.id, media=media)
        await waiting_msg.delete()
    except Exception as e:
        await bot.delete_message(message.chat.id, message_id=message.message_id)
        logger.exception("Error while sending Instagram photo: %s", e)
