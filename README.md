# Candy Shop

[![codecov](https://codecov.io/gh/atsanda/candy-shop/branch/main/graph/badge.svg?token=YYQ675YF3V)](https://codecov.io/gh/atsanda/candy-shop)

This is a small REST servise written with [Django REST framework](https://www.django-rest-framework.org/) for managing couriers and orders for a candy shop. It is a part of selection process to [Yandex Backend School](https://yandex.ru/promo/academy/backend-school).

## Structure

The app implements several apis:
```
[POST] /couriers
[GET] /couriers/{courier_id}
[PATCH] /couriers/{courier_id}
[POST] /orders
[POST] /orders/assign
[POST] /orders/complete
```
There are several core files for processing each of them:
* a request is recieved inside [views](candy_shop/apps/delivery/views.py),
* then deserialized and validated inside [serializers](candy_shop/apps/delivery/serializers.py), 
* business logic is applied from [services](candy_shop/apps/delivery/services.py),
* comlex queries are added moved to [models](candy_shop/apps/delivery/models.py).

## Installation
To install the app for development
* install python>=3.7
* install dependencies from `requirements.txt`, it is better to do it inside virtual environment
```bash
$ python -m venv env
$ . env/bin/activate
$ pip install -r requirements.txt
```
* after that make sure you have [Postgres](https://www.postgresql.org/download/) installed (I used v.11)
* use default config for postgres
* create `candy_shop` db
* create `.env`
```.env
DJANGO_SETTINGS_MODULE=candy_shop.config
DJANGO_CONFIGURATION=Local
```
* run test to check your installation
```.bash
$ pytest
```

## Deployment

The app was deployed to corresponding virtual machine, which was given to all entrants. My settings for deployment were taken from [this video](https://youtu.be/FLiKTJqyyvs). The video offers to deploy through gunicorn, nginx and supervisor, which I did.

## Tests

[PyTest](https://docs.pytest.org/en/stable/) was used for testing. So far, only integration tests have been written.
