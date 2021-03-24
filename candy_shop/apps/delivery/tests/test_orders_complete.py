import pytest
import json
from rest_framework import status
from candy_shop.apps.delivery.models import Order


@pytest.fixture
def simple_setup(client):
    couriers = {
        "data": [
            {
                "courier_id": 1,
                "courier_type": "foot",
                "regions": [1],
                "working_hours": ["09:00-18:00"]
            },
        ]
    }
    response = client.post(
        '/couriers',
        json.dumps(couriers),
        content_type="application/json")
    assert response.status_code == status.HTTP_201_CREATED

    orders = {
        "data": [
            {
                "order_id": 1,
                "weight": 1,
                "region": 1,
                "delivery_hours": ["09:00-18:00"]
            }
        ]
    }

    response = client.post(
        '/orders',
        json.dumps(orders),
        content_type="application/json")
    assert response.status_code == status.HTTP_201_CREATED

    assign = {
        "courier_id": 1
    }
    response = client.post(
        '/orders/assign',
        json.dumps(assign),
        content_type="application/json")

    assert response.status_code == status.HTTP_200_OK
    assert set([o['id'] for o in response.data['orders']]) == {1}


@pytest.mark.django_db
@pytest.mark.integration
def test_valid_complete(simple_setup, client):
    complete = {
        "courier_id": 1,
        "order_id": 1,
    }
    response = client.post(
        '/orders/complete',
        json.dumps(complete),
        content_type="application/json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data['order_id'] == 1


@pytest.mark.django_db
@pytest.mark.integration
def test_invalid_complete(simple_setup, client):
    complete = {
        "courier_id": 1,
        "order_id": 2,
    }
    response = client.post(
        '/orders/complete',
        json.dumps(complete),
        content_type="application/json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.integration
def test_complete_twice(simple_setup, client):
    complete = {
        "courier_id": 1,
        "order_id": 1,
    }
    response = client.post(
        '/orders/complete',
        json.dumps(complete),
        content_type="application/json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data['order_id'] == 1

    complete_time = Order.objects.get(pk=1).complete_time

    response = client.post(
        '/orders/complete',
        json.dumps(complete),
        content_type="application/json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data['order_id'] == 1

    assert Order.objects.get(pk=1).complete_time == complete_time

