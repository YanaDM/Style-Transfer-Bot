from model import StyleTransferModel
from telegram_token import token
import numpy as np
from PIL import Image
from io import BytesIO
from multiprocessing import Queue, Process
from time import sleep
from telegram.ext import Updater, MessageHandler, Filters, ConversationHandler, CommandHandler, RegexHandler
from telegram import ReplyKeyboardMarkup
import logging
import threading
import os
import sys
from threading import Thread

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logger = logging.getLogger(__name__)

MENU, CHOOSE_STYLE, WAIT_PHOTO, ABOUT = range(4)


menu_keyboard = [['Fast Style Transfer']]
menu_markup = ReplyKeyboardMarkup(menu_keyboard, one_time_keyboard=True)


style_choice_keyboard = [['candy', 'mosaic'],
                         ['rain_princess', 'udnie']]
style_choice_markup = ReplyKeyboardMarkup(style_choice_keyboard, one_time_keyboard=True)


model = StyleTransferModel()
job_queue = Queue()


def worker(bot, queue):
    while True:
        message, style_chosen = queue.get()
        # Получаем сообщение с картинкой из очереди и обрабатываем ее
        chat_id = message.chat_id
        logger.info("Got image from {}".format(chat_id))

        # получаем информацию о картинке
        image_info = message.photo[-1]
        image_file = bot.get_file(image_info)

        content_image_stream = BytesIO()
        image_file.download(out=content_image_stream)

        model_name = style_chosen + '.pth'

        output = model.transfer_style(content_image_stream, model_name)
        sleep(10)

        # теперь отправим назад фото
        output_stream = BytesIO()
        output.save(output_stream, format='PNG')
        output_stream.seek(0)
        bot.send_photo(chat_id, photo=output_stream, timeout=1000)
        bot.send_message(chat_id=chat_id, text="Нажми /restart, чтобы перезапустить бота.")
        logger.info("Sent Photo to user")


def start(bot, update):
    update.message.reply_text("Привет! Я бот, который может обрабатывать картинки в одном из доступных мне стилей. Нажми на Fast Style Transfer\
    и следуй дальнейшим инструкциям, чтобы обработать картинку или нажми /about, чтобы подробнее узнать о доступных стилях.",
                              reply_markup=menu_markup)

    return MENU


def menu_fallback(bot, update, user_data):
    # TODO Clear all inner states
    update.message.reply_text("You exited to menu",
                              reply_markup=menu_markup)

    return MENU


def fast_transfer_choice(bot, update):
    update.message.reply_text("You chose fast style transfer, now choose style",
                              reply_markup=style_choice_markup)

    return CHOOSE_STYLE


def received_style_choice(bot, update, user_data):
    user_data['style_choice'] = update.message.text
    update.message.reply_text("Now send photo")

    return WAIT_PHOTO


def received_photo_fast_transfer(bot, update, user_data):
    style_chosen = user_data['style_choice']
    update.message.reply_text("Ваше фото помещено в очередь, скоро оно придет", )
    job_queue.put((update.message, style_chosen))

    return MENU

def about(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="В данный момент изображение можно обработать в одном из четырех стилей.\
    \nДалее описаны доступные варианты и ресурсы, где можно о них узнать подробнее:\
    \ncandy - стиль модерн (https://clck.ru/FGrrF)\
    \nmosaic - витражи в стиле Тиффани (https://clck.ru/FGrrb)\
    \nrain_princess - импрессионизм (https://clck.ru/FGrro)\
    \nudnie - кубизм (https://clck.ru/FGrrw)\
    \nТеперь нажимай Fast Style Transfer.\
    \nДля того чтобы показать меню, если оно скрыто, отправь сообщение с текстом - menu.")

def main():
    updater = Updater(token=token)

    dp = updater.dispatcher

    def stop_and_restart():
        """Gracefully stop the Updater and replace the current process with a new one"""
        updater.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def restart(bot, update):
        update.message.reply_text('Bot is restarting... Now press /start')
        Thread(target=stop_and_restart).start()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            MENU: [RegexHandler('^Fast Style Transfer$',
                                fast_transfer_choice)],
            CHOOSE_STYLE: [MessageHandler(Filters.text,
                                          received_style_choice, pass_user_data=True)],
            WAIT_PHOTO: [MessageHandler(Filters.photo,
                                        received_photo_fast_transfer, pass_user_data=True)]
        },
        fallbacks=[RegexHandler('^menu$', menu_fallback, pass_user_data=True)]
    )

    dp.add_handler(conv_handler)

    dp.add_handler(CommandHandler('about', about))

    dp.add_handler(CommandHandler('restart', restart))

    worker_args = (updater.bot, job_queue)
    worker_process = Process(target=worker, args=worker_args)
    worker_process.start()

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
