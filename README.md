# tg-dodo
 
# fish-shop
 
Чатбот в мессенджере телеграм для продажи пицц с помощью сервиса [Elastic Path](https://elasticpath.com)

[@DoDoPizza](https://t.me/dvmn_verbs_game_support_bot)

Пример работы:

![](https://github.com/Ykyki4/tg-dodo/blob/main/media/pizza-bot-example.gif)

## Установка:

Для начала, скачайте репозиторий в .zip или клонируйте его, изолируйте проект с помощью venv и установите зависимости командой:

```
pip install -r requirements.txt
```

Далее, создайте файл .env и установите следующие переменные окружения в формате ПЕРЕМЕННАЯ=значение:

* TG_BOT_TOKEN - Бот в телеграмме для викторин. Зарегистрировать нового бота можно [тут](https://telegram.me/BotFather).
* SHOP_CLIENT_ID - Айди вашего магазина на [Elastic Path](https://elasticpath.com).
* SHOP_CLIENT_SECRET - Секретный токен вашего магазина на [Elastic Path](https://elasticpath.com).
* YANDEX_API_KEY - Токен вашего аккаунта разработчика на [Yandex Api](https://developer.tech.yandex.ru/services/)
* PAYMENT_PROVIDER_TOKEN - Токен вашего провайдера для оплаты в телеграмме. Вам понадобится этот [бот](https://telegram.me/BotFather), /mybots, выберите бота, Payments.
* DB_HOST
* DB_PASSWORD
* DB_PORT

Для получения данных о вашей базе данных, зайдите на [сайт](https://redis.com/), и создайте там новую базу данных.

Для того чтобы приготовить ваш магазин к работе с ботом, запустите два этих скрипта командой:

Загрузить модель юзеров и рестораны:
```
python load_flows.py 
```

Загрузить продукты:
```
python load_products.py
```

После завершения работы этих скриптов, можно запускать бота командой:

```
python tg_bot.py
```
