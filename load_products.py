import json
from pathlib import PurePath

from environs import Env
import requests

from api import get_access_token


def get_menu():
    path = PurePath('data', 'menu.json')
    with open(path, 'r', encoding='utf8') as file:
        menu_raw = file.read()
    menu = json.loads(menu_raw)
    return menu


def add_image(access_token, image_url):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    files = {
        'file_location': (None, image_url),
    }

    response = requests.post('https://api.moltin.com/v2/files', headers=headers, files=files)
    response.raise_for_status()

    return response.json()


def add_image_to_product(access_token, product_id, image_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    main_image_data = {
        'data': {
            'type': 'main_image',
            'id': image_id,
        },
    }

    response = requests.post(
        f'https://api.moltin.com/v2/products/{product_id}/relationships/main-image',
        headers=headers,
        json=main_image_data,
    )
    response.raise_for_status()

    return response.json()


def load_products(access_token, menu):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    for menu_item in menu:
        product_data = {
            'data': {
                'type': 'product',
                'sku': str(menu_item['id']),
                'slug': f"pizza-{menu_item['id']}",
                'name': menu_item['name'],
                'description': menu_item['description'],
                'manage_stock': False,
                'price': [
                    {
                        'amount': menu_item['price'],
                        'currency': 'RUB',
                        'includes_tax': False
                    }
                ],
                'status': 'live',
                'commodity_type': 'physical',
            },
        }

        add_image_response = add_image(access_token, menu_item['product_image']['url'])

        add_product_response = requests.post(f"https://api.moltin.com/v2/products", headers=headers, json=product_data)
        add_product_response.raise_for_status()

        add_image_to_product(access_token, add_product_response.json()['data']['id'], add_image_response.json()['data']['id'])


if __name__ == '__main__':
    env = Env()
    env.read_env()

    shop_client_id = env('SHOP_CLIENT_ID')
    shop_client_secret = env('SHOP_CLIENT_SECRET')

    shop_access_token, _ = get_access_token(shop_client_id, shop_client_secret)

    menu = get_menu()

    load_products(shop_access_token, menu)
