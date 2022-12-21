import os
import sys
import json
from datetime import datetime

from environs import Env
import requests
import redis
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler

from api import get_access_token, get_products, get_photo_url, get_products_by_category_id, get_categories


env = Env()
env.read_env()

app = Flask(__name__)

DATABASE = None

SHOP_ACCESS_TOKEN, access_token_expires = get_access_token(env("SHOP_CLIENT_ID"), env("SHOP_CLIENT_SECRET"))

scheduler = BackgroundScheduler()

def regenerate_token():
    shop_access_token, _ = get_access_token(env("SHOP_CLIENT_ID"), env("SHOP_CLIENT_SECRET"))
    os.environ['SHOP_ACCESS_TOKEN'] = shop_access_token

scheduler.add_job(func=regenerate_token, trigger="interval", seconds=access_token_expires)
scheduler.start()


@app.route('/', methods=['GET'])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == env("VERIFY_TOKEN"):
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


def get_menu(requested_category_id):
    products = get_products_by_category_id(SHOP_ACCESS_TOKEN, requested_category_id)

    params = {"access_token": env("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}

    menu_elements = [
                        {
                        "title": "Меню.",
                        "image_url": "https://img.freepik.com/premium-vector/pizza-logo-design_9845-319.jpg?w=2000",
                        "subtitle": "Что хотите заказать?",
                        "buttons": [
                            {
                            "type":"postback",
                            "title":"Корзина",
                            "payload":"cart",
                            },
                            {
                            "type":"postback",
                            "title":"Акции",
                            "payload":"sales",
                            },
                            {
                            "type":"postback",
                            "title":"Оформить заказ",
                            "payload":"checkout",
                            },
                        ],
                    },
                ]

    for product in products:
        menu_elements.append(
                            {
                            "title": f"{product['name']} ({product['price'][0]['amount']} р.)",
                            "image_url": get_photo_url(SHOP_ACCESS_TOKEN, product["relationships"]["main_image"]["data"]["id"]),
                            "subtitle": product["description"],
                            "buttons": [
                                {
                                "type": "postback",
                                "title": "Добавить в корзину",
                                "payload": product["id"],
                                }
                            ] 
                    }
                )

    categories = get_categories(SHOP_ACCESS_TOKEN)

    menu_elements.append(
                        {
                        "title": "Не нашли пиццу по вкусу?",
                        "image_url": "https://primepizza.ru/uploads/position/large_0c07c6fd5c4dcadddaf4a2f1a2c218760b20c396.jpg",
                        "subtitle": "У нас есть много разных пицц, выберите категорию.",
                        "buttons": [
                            {
                            "type": "postback",
                            "title": category["name"],
                            "payload": category["id"],
                            } for category in categories if category["id"] != requested_category_id
                        ]
                    }
                )
    return menu_elements


def handle_start(sender_id, message_text):
    params = {"access_token": env("PAGE_ACCESS_TOKEN")}
    headers = {"Content-Type": "application/json"}

    menu_elements = get_menu(env('FRONT_PAGE_CATEGORY_ID'))

    request_content = json.dumps({
        "recipient": {
            "id": sender_id
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type":"generic",
                    "elements": menu_elements
            }
        }
    }
})

    response = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=request_content)
    print(response.json())
    response.raise_for_status()

    return ""


def handle_users_reply(sender_id, message_text):
    DATABASE = get_database_connection()
    states_functions = {
        "START": handle_start,
    }
    recorded_state = DATABASE.get(f"facebookid_{sender_id}")
    if not recorded_state or recorded_state.decode("utf-8") not in states_functions.keys():
        user_state = "START"
    else:
        user_state = recorded_state.decode("utf-8")
    if message_text == "/start":
        user_state = "START"
    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, message_text)
    DATABASE.set(sender_id, next_state)


@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):  
                    sender_id = messaging_event["sender"]["id"]        
                    recipient_id = messaging_event["recipient"]["id"]  
                    message_text = messaging_event["message"]["text"]  
                    handle_users_reply(sender_id, message_text)
    return "ok", 200


def get_database_connection():
    global DATABASE
    if DATABASE is None:
        database_password = env('DATABASE_PASSWORD')
        database_host = env('DATABASE_HOST')
        database_port = env('DATABASE_PORT')
        DATABASE = redis.Redis(host=database_host, port=database_port, password=database_password)
    return DATABASE


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
