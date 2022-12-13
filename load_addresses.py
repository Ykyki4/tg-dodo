import json
from pathlib import PurePath

import requests
from environs import Env

from api import get_access_token


def get_addresses():
    path = PurePath('data', 'addresses.json')
    with open(path, 'r', encoding='utf8') as file:
        addresses_raw = file.read()
    addresses = json.loads(addresses_raw)

    return addresses


def create_flow(access_token, name, slug, description, enabled):
    headers = {
        'Authorization': access_token,
        'Content-Type': 'application/json',
    }

    json_data = {
        'data': {
            'type': 'flow',
            'name': name,
            'slug': slug,
            'description': description,
            'enabled': enabled,
        },
    }

    response = requests.post('https://api.moltin.com/v2/flows', headers=headers, json=json_data)
    response.raise_for_status()

    return response.json()


def create_field(access_token, name, slug, description, flow_id):
    headers = {
        'Authorization': access_token,
        'Content-Type': 'application/json',
    }
    json_data = {
        'data': {
            'type': 'field',
            'name': name,
            'slug': slug.lower(),
            'description': description,
            'field_type': 'string',
            'required': False,
            'enabled': True,
            'relationships': {
                'flow': {
                    'data': {
                        'type': 'flow',
                        'id': flow_id,
                    },
                },
            },
        },
    }

    response = requests.post('https://api.moltin.com/v2/fields', headers=headers, json=json_data)
    response.raise_for_status()

    return response.json()


def add_fields_to_pizzeria_flow(access_token, pizzeria_flow_id):
    fields = ['Address', 'Alias', 'Longitude', 'Latitude']

    for field in fields:
        create_field(access_token, field, field, field, pizzeria_flow_id)


def load_addresses_to_fields(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    for restaurant in get_addresses():
        json_data = {
            'data': {
                'type': 'entry',
                'address': restaurant['address']['full'],
                'alias': restaurant['alias'],
                'longitude': restaurant['coordinates']['lon'],
                'latitude': restaurant['coordinates']['lat'],
            },
        }
        response = requests.post(f'https://api.moltin.com/v2/flows/pizzeria/entries',
                                 headers=headers, json=json_data)
        response.raise_for_status()


if __name__ == '__main__':
    env = Env()
    env.read_env()

    shop_client_id = env('SHOP_CLIENT_ID')
    shop_client_secret = env('SHOP_CLIENT_SECRET')

    shop_access_token, _ = get_access_token(shop_client_id, shop_client_secret)

    flow_response = create_flow(shop_access_token, 'Pizzeria', 'pizzeria', 'Pizzeria addresses', True)
    add_fields_to_pizzeria_flow(shop_access_token, flow_response['data']['id'])

    load_addresses_to_fields(shop_access_token)
