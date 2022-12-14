from more_itertools import chunked

from textwrap import dedent
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from api import get_cart


def get_menu(products, chunk=0):
    products_in_chunk = 8
    keyboard = [[InlineKeyboardButton(product['name'], callback_data=product['id'])]
                for product in list(chunked(products, products_in_chunk))[int(chunk)]]

    keyboard.append([InlineKeyboardButton('⬅️', callback_data='⬅️'),
                     InlineKeyboardButton('➡️', callback_data='➡️')])
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='cart')])

    return InlineKeyboardMarkup(keyboard), len(list(chunked(products, products_in_chunk)))


def fetch_coordinates(apikey, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat


def show_cart_to_courier(update, context):

    cart_response, items_response = get_cart(context.bot_data['shop_access_token'], update.effective_user.id)

    cart_text = ''
    for item in items_response:
        cart_text += (
            dedent(f'''
                {item["name"]}
                {item["description"]}
                {item["quantity"]} пицц в корзине за {item["meta"]["display_price"]["with_tax"]["value"]["formatted"]}
                '''))

    cart_text += f'К оплате: {context.user_data["cart_price"]}р.'

    context.bot.send_message(chat_id=context.user_data["closest_pizzeria"]['courierid'],
                             text=cart_text,)
