import pytest
import json
from rest_framework import status
from candy_shop.apps.delivery.models import Courier


@pytest.fixture
def setup_with_partially_complete_delivery(client):
    couriers = {
        "data": [
            {
                "courier_id": 1,
                "courier_type": "car",
                "regions": [1],
                "working_hours": ["09:00-18:00"]
            },
            {
                "courier_id": 2,
                "courier_type": "car",
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
            },
            {
                "order_id": 2,
                "weight": 15,
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
    assert set([o['id'] for o in response.data['orders']]) == {1, 2}

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
def test_reassign_after_changing_courier_type(
    setup_with_partially_complete_delivery,
    client
):
    assign = {
        'courier_id': 2,
    }
    response = client.post(
        '/orders/assign',
        json.dumps(assign),
        content_type="application/json")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['orders']) == 0

    patch = {
        "courier_id": 1,
        "courier_type": 'foot',
    }
    response = client.patch(
        '/couriers/1',
        json.dumps(patch),
        content_type="application/json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data['courier_type'] == 'foot'
    assert Courier.objects.get(pk=1).orders.count() == 1

    response = client.post(
        '/orders/assign',
        json.dumps(assign),
        content_type="application/json")
    assert response.status_code == status.HTTP_200_OK
    assert set([o['id'] for o in response.data['orders']]) == {2}
