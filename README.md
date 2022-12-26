# tg-dodo
 
# fish-shop
 
Чатбот в мессенджере телеграм и фэйсбук для продажи пицц с помощью сервиса [Elastic Path](https://elasticpath.com)

Телеграм:

[@DoDoPizza](https://t.me/dvmn_verbs_game_support_bot)

Фэйсбук:

[DoDo-Pizza](https://www.facebook.com/messages/t/103610002611169/)

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

Если хотите запустить бота в фэйсбуке, вам также нужно определить данные переменные:

* PAGE_ACCESS_TOKEN - маркер доступа от вашей страницы.
* VERIFY_TOKEN - ключ верификации вебхука, должен быть такой же, какой вы указали при регистрации вебхука.
* FRONT_PAGE_CATEGORY_ID - айди категории которая должна высвечиваться первой. Можно получить и установить в [Elastic Path](https://elasticpath.com).

Также, вам нужно следовать данному [гайду](https://dvmn.org/encyclopedia/api-docs/how-to-get-facebook-api/)

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
