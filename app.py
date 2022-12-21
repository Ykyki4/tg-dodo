import os
import sys
import json
from datetime import datetime

from environs import Env
import requests
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler

from api import get_access_token, get_products, download_photo


env = Env()
env.read_env()

app = Flask(__name__)

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


@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):  # someone sent us a message
                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text
                    send_message(sender_id, message_text)
    return "ok", 200


def send_message(recipient_id, message_text):
    products = get_products(SHOP_ACCESS_TOKEN)

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

    for product in products[:5]:
        menu_elements.append(
                            {
                            "title": f"{product['name']} ({product['price'][0]['amount']} р.)",
                            "image_url": download_photo(SHOP_ACCESS_TOKEN, product['relationships']['main_image']['data']['id']),
                            "subtitle": product['description'],
                            "buttons": [
                                {
                                "type":"postback",
                                "title":"Добавить в корзину",
                                "payload": product['id'],
                                }
                            ] 
                    }
                )

    request_content = json.dumps({
        "recipient": {
            "id": recipient_id
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
