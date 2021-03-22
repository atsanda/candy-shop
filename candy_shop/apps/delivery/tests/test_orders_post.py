import pytest
import json
from rest_framework import status
from candy_shop.apps.delivery.models import Order, Region
from copy import deepcopy
from decimal import Decimal


CORRECT_POST_DATA = {
    "data": [
        {
            "order_id": 1,
            "weight": 0.23,
            "region": 12,
            "delivery_hours": ["09:00-18:00"]
        },
        {
            "order_id": 2,
            "weight": 15,
            "region": 1,
            "delivery_hours": ["09:00-18:00"]
        },
        {
            "order_id": 3,
            "weight": 0.01,
            "region": 22,
            "delivery_hours": ["09:00-12:00", "16:00-21:30"]
        },
    ]
}


@pytest.mark.django_db
@pytest.mark.integration
def test_successful_post(client):
    response = client.post(
        '/orders',
        json.dumps(CORRECT_POST_DATA),
        content_type="application/json")

    assert response.status_code == status.HTTP_201_CREATED
    assert len(response.data["orders"]) == 3
    ids = [item['order_id'] for item in CORRECT_POST_DATA['data']]
    for o in response.data["orders"]:
        assert o['id'] in ids
    assert Order.objects.count() == 3
    assert Region.objects.count() == 3

    for o in CORRECT_POST_DATA['data']:
        order = (
            Order.objects
            .filter(pk=o['order_id'])
            .prefetch_related('delivery_hours')[0]
        )
        assert order.status == Order.OrderStatus.OPEN
        assert order.courier is None
        assert order.region.pk == o['region']
        assert order.weight == Decimal(str(o['weight']))
        delivery_hours = [str(dh) for dh in order.delivery_hours.all()]
        assert set(delivery_hours) == set(o['delivery_hours'])


@pytest.fixture
def post_and_assert_fn():
    def post_and_assert(client, incorrect_data):
        response = client.post(
            '/orders',
            json.dumps(incorrect_data),
            content_type="application/json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'validation_error' in response.data
        assert 'orders' in response.data['validation_error']
        assert len(response.data['validation_error']['orders']) == 1
        assert str(response.data['validation_error']['orders'][0]['id']) == '1'
    return post_and_assert


@pytest.mark.django_db
@pytest.mark.integration
def test_invalid_region(client, post_and_assert_fn):
    incorrect_data = deepcopy(CORRECT_POST_DATA)
    incorrect_data['data'][0]['region'] = [-1]
    post_and_assert_fn(client, incorrect_data)


@pytest.mark.django_db
@pytest.mark.integration
def test_invalid_weight(client, post_and_assert_fn):
    incorrect_data = deepcopy(CORRECT_POST_DATA)
    incorrect_data['data'][0]['weight'] = 51.0
    post_and_assert_fn(client, incorrect_data)
    incorrect_data['data'][0]['weight'] = 0.001
    post_and_assert_fn(client, incorrect_data)


@pytest.mark.django_db
@pytest.mark.integration
def test_invalid_delivery_hours(client, post_and_assert_fn):
    incorrect_data = deepcopy(CORRECT_POST_DATA)
    incorrect_data['data'][0]['delivery_hours'] = '03.09.09 10:00-15:00'
    post_and_assert_fn(client, incorrect_data)
