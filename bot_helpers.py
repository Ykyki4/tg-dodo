from more_itertools import chunked

from geopy import distance
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


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


def get_distance(entry):
    pizzeria_address = (entry.longitude, entry.latitude)
    return distance.distance(order_address, pizzeria_address).km
