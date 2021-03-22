import pytest
import json
from rest_framework import status
from candy_shop.apps.delivery.models import Order
from datetime import timedelta


@pytest.fixture
def setup_db(client):
    couriers = {
        "data": [
            {
                "courier_id": 1,
                "courier_type": "car",
                "regions": [1, 2, 3],
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
                "weight": 50,
                "region": 1,
                "delivery_hours": ["09:00-18:00"]
            },
            {
                "order_id": 2,
                "weight": 50,
                "region": 2,
                "delivery_hours": ["09:00-18:00"]
            },
            {
                "order_id": 3,
                "weight": 50,
                "region": 3,
                "delivery_hours": ["09:00-18:00"]
            }
        ]
    }

    response = client.post(
        '/orders',
        json.dumps(orders),
        content_type="application/json")
    assert response.status_code == status.HTTP_201_CREATED

    for order_id in [1, 2, 3]:
        assign = {
            "courier_id": 1
        }
        response = client.post(
            '/orders/assign',
            json.dumps(assign),
            content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        assert set([o['id'] for o in response.data['orders']]) == {order_id}

        complete = {
            "courier_id": 1,
            "order_id": order_id,
        }
        response = client.post(
            '/orders/complete',
            json.dumps(complete),
            content_type="application/json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data['order_id'] == order_id

        order = Order.objects.get(pk=order_id)
        order.complete_time = (
            order.assigned_time + timedelta(seconds=order_id*100))
        order.delivery_time = timedelta(seconds=order_id*100)
        order.save()


@pytest.mark.django_db
@pytest.mark.integration
def test_get_values(client, setup_db):
    response = client.get('/couriers/1')
    assert response.status_code == status.HTTP_200_OK
    data = response.data
    assert set(data.keys()) == {'courier_id', 'courier_type', 'regions',
                                'working_hours', 'rating', 'earnings'}
    assert data['earnings'] == 3 * 500 * 9
    assert data['rating'] == round((60*60 - 100)/(60*60) * 5, 2)
