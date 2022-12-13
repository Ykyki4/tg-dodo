import logging
from textwrap import dedent

from environs import Env
from geopy import distance
import redis
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, Filters, Updater

from api import get_access_token, get_products, get_product_by_id, download_photo, add_product_to_cart, get_cart, \
    delete_from_cart, create_customer, get_all_entries, add_client_entry
from bot_helpers import get_menu, fetch_coordinates, show_cart_to_courier


_database = None
logger = logging.getLogger('BotLogger')


def start(update, context):
    products_raw = get_products(context.bot_data['shop_access_token'])
    context.bot_data['current_chunk'] = 0

    markup, chunks_number = get_menu(products_raw)

    context.bot_data['chunks_number'] = chunks_number

    update.message.reply_text(text='Что хотите закзать?', reply_markup=markup)
    return 'HANDLE_MENU'


def show_menu(update, context):
    products_raw = get_products(context.bot_data['shop_access_token'])

    markup, _ = get_menu(products_raw, context.bot_data['current_chunk'])

    context.bot.send_message(
        chat_id=update.effective_user.id,
        text='Что хотите закзать?',
        reply_markup=markup)
    context.bot.delete_message(
        chat_id=update.effective_user.id,
        message_id=update.callback_query.message.message_id,
    )

    return 'HANDLE_MENU'


def handle_menu(update, context):
    query = update.callback_query

    if query.data == 'cart':
        return show_cart(update, context)
    elif query.data == '➡️':
        if context.bot_data['current_chunk']+1 != context.bot_data['chunks_number']:
            context.bot_data['current_chunk'] += 1
            return show_menu(update, context)
    elif query.data == '⬅️':
        if context.bot_data['current_chunk'] != 0:
            context.bot_data['current_chunk'] -= 1
            return show_menu(update, context)
    else:
        context.user_data['product_id'] = query.data

        product = get_product_by_id(context.bot_data['shop_access_token'], query.data)

        product_img_id = product['relationships']['main_image']['data']['id']
        filename = download_photo(context.bot_data['shop_access_token'], product_img_id)

        with open(f'{filename}', 'rb') as image:
            product_text = dedent(f'''
                            {product['name']}
                            Стоимость: {product['price'][0]['amount']}
                            
                            {product['description']}
                            ''')

            keyboard = [[InlineKeyboardButton('Положить пиццу в корзину', callback_data='product_to_cart')],
                        [InlineKeyboardButton('Корзина🛒', callback_data='cart')],
                        [InlineKeyboardButton('Назад🔙', callback_data='menu')]
                        ]

            markup = InlineKeyboardMarkup(keyboard)

            context.bot.send_photo(chat_id=query.message.chat_id,
                                   photo=image,
                                   caption=product_text,
                                   reply_markup=markup,)
            context.bot.delete_message(chat_id=query.message.chat_id,
                                       message_id=query.message.message_id)

            return 'HANDLE_DESCRIPTION'


def handle_description(update, context):
    query = update.callback_query

    if query.data == 'menu':
        return show_menu(update, context)
    elif query.data == 'cart':
        return show_cart(update, context)
    elif query.data == 'product_to_cart':
        add_product_to_cart(
                    context.bot_data['shop_access_token'],
                    update.effective_user.id,
                    context.user_data['product_id']
                    )

        update.callback_query.answer(
            text=f'Продукт был добавлен в корзину',
        )

        return 'HANDLE_DESCRIPTION'


def show_cart(update, context):
    query = update.callback_query

    cart_response, items_response = get_cart(context.bot_data['shop_access_token'], update.effective_user.id)

    cart_text = ''
    keyboard = []
    for item in items_response:
        cart_text += (
            dedent(f'''
            {item["name"]}
            {item["description"]}
            {item["quantity"]} пицц в корзине за {item["meta"]["display_price"]["with_tax"]["value"]["formatted"]}
            '''))

        keyboard.append(
            [InlineKeyboardButton(f'Убрать {item["name"]} из корзины',
                                  callback_data=item["id"])]
        )

    cart_text += f'К оплате: {cart_response["meta"]["display_price"]["with_tax"]["formatted"]}'

    keyboard.append([InlineKeyboardButton('Оплатить💳', callback_data='pay')])
    keyboard.append([InlineKeyboardButton('Назад🔙', callback_data='menu')])

    markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(chat_id=update.effective_user.id,
                             text=cart_text,
                             reply_markup=markup)
    context.bot.delete_message(chat_id=query.message.chat_id,
                               message_id=query.message.message_id)

    return 'HANDLE_CART'


def handle_cart(update, context):
    query = update.callback_query
    if query.data == 'menu':
        return show_menu(update, context)
    elif query.data == 'pay':
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Пожалуйста, пришлите ваш адрес текстом или геолокацию.')
        context.bot.delete_message(chat_id=query.message.chat_id,
                                   message_id=query.message.message_id)
        return 'WAITING_GEO'
    else:
        delete_from_cart(context.bot_data['shop_access_token'], update.effective_user.id, query.data)
        update.callback_query.answer(
            text='Продукт был убран из корзины',
        )
        return show_cart(update, context)


def waiting_geo(update, context):
    if update.message.location:
        context.user_data['geoposition'] = (update.message.location.longitude, update.message.location.latitude)
    else:
        context.user_data['geoposition'] = fetch_coordinates(context.bot_data['yandex_api_token'], update.message.text)

    entries = get_all_entries(context.bot_data['shop_access_token'])

    closest_pizzeria = min(entries, key=lambda entry:
                            distance.distance((entry['longitude'], entry['latitude']),
                            context.user_data['geoposition']).km)

    closest_pizzeria_distance = distance.distance((closest_pizzeria['longitude'], closest_pizzeria['latitude']),
                                                  context.user_data['geoposition']).km

    context.user_data['closest_pizzeria'] = closest_pizzeria

    deliver_pickup_keyboard = [[InlineKeyboardButton('Доставка', callback_data='deliver')],
                               [InlineKeyboardButton('Самовывоз', callback_data='pickup')]]

    deliver_pickup_markup = InlineKeyboardMarkup(deliver_pickup_keyboard)

    pickup_keyboard = [[InlineKeyboardButton('Доставка', callback_data='deliver')]]

    pickup_markup = InlineKeyboardMarkup(pickup_keyboard)

    if closest_pizzeria_distance <= 0.5:
        update.message.reply_text(
            text=dedent(f'''
            Ближайшая пиццерия всего в {int(closest_pizzeria_distance * 1000)} м. от Вас.
            Можете забрать сами, или мы доставим бесплато'''),
            reply_markup=deliver_pickup_markup
        )
    elif closest_pizzeria_distance <= 5:
        update.message.reply_text(
            text=dedent(f'''
            Ближайшая пиццерия в {closest_pizzeria_distance:.1f} км. от Вас.
            Можете забрать сами, или мы доставим за дополнительную плату в 100 р.'''),
            reply_markup=deliver_pickup_markup
        )
    elif closest_pizzeria_distance <= 20:
        update.message.reply_text(
            text=dedent(f'''
            Ближайшая пиццерия в {closest_pizzeria_distance:.1f} км. от Вас.
            Можете забрать сами, или мы доставим за дополнительную плату в 300 р.'''),
            reply_markup=deliver_pickup_markup
        )
    else:
        update.message.reply_text(
            text=dedent(f'''
            Ближайшая пиццерия в {closest_pizzeria_distance:.1f} км. от Вас.
            Так далеко мы не доставляем, можете забрать её сами.'''),
            reply_markup=pickup_markup
        )

    return 'DELIVER_CHOICE'


def handle_deliver_choice(update, context):
    query = update.callback_query
    closest_pizzeria = context.user_data["closest_pizzeria"]
    if query.data == 'pickup':
        context.bot.send_message(chat_id=update.effective_user.id,
                                 text=f'Вот адрес пиццерии: {closest_pizzeria["address"]}. Ждём вас.')
        context.bot.delete_message(chat_id=query.message.chat_id,
                                   message_id=query.message.message_id)
    elif query.data == 'deliver':
        lon, lat = context.user_data['geoposition']
        add_client_entry(context.bot_data['shop_access_token'], update.effective_user.id, lon, lat)

        show_cart_to_courier(update, context)
        context.bot.send_location(chat_id=closest_pizzeria['courierid'], longitude=lon, latitude=lat)

        context.bot.send_message(chat_id=update.effective_user.id,
                                 text=f'Курьер прибудет в течении часа, ожидайте ваш заказ.')
        context.bot.delete_message(chat_id=query.message.chat_id,
                                   message_id=query.message.message_id)


def handle_users_reply(update, context):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode('utf-8')

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_GEO': waiting_geo,
        'DELIVER_CHOICE': handle_deliver_choice,
    }
    state_handler = states_functions[user_state]

    next_state = state_handler(update, context)
    db.set(chat_id, next_state)


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', context.error)


def get_database_connection():
    global _database
    if _database is None:
        database_password = env('DATABASE_PASSWORD')
        database_host = env('DATABASE_HOST')
        database_port = env('DATABASE_PORT')
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


def regenerate_shop_access_token(context):
    shop_access_token = get_access_token(context.bot_data['shop_client_id'], context.bot_data['shop_client_secret'])
    context.bot_data['shop_access_token'] = shop_access_token


if __name__ == '__main__':
    env = Env()
    env.read_env()

    tg_token = env('TG_TOKEN')
    shop_client_id = env('SHOP_CLIENT_ID')
    shop_client_secret = env('SHOP_CLIENT_SECRET')

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    updater = Updater(tg_token)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.location, waiting_geo))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    dispatcher.add_error_handler(error)

    shop_access_token, token_expires = get_access_token(shop_client_id, shop_client_secret)

    dispatcher.bot_data['shop_client_id'] = shop_client_id
    dispatcher.bot_data['shop_client_secret'] = shop_client_secret

    dispatcher.bot_data['shop_access_token'] = shop_access_token
    updater.job_queue.run_repeating(regenerate_shop_access_token, interval=token_expires)

    dispatcher.bot_data['yandex_api_token'] = env('YANDEX_API_KEY')

    updater.start_polling()
