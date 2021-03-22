import pytest
import json
from rest_framework import status
from candy_shop.apps.delivery.models import Courier, Region
from copy import deepcopy


CORRECT_POST_DATA = {
    "data": [
        {
            "courier_id": 1,
            "courier_type": "foot",
            "regions": [1, 12, 22],
            "working_hours": ["11:35-14:05", "09:00-11:00"]
        },
        {
            "courier_id": 2,
            "courier_type": "bike",
            "regions": [22],
            "working_hours": ["09:00-18:00"]
        },
        {
            "courier_id": 23,
            "courier_type": "car",
            "regions": [12, 22, 23, 33],
            "working_hours": []
        },
    ]
}


@pytest.mark.django_db
@pytest.mark.integration
def test_successful_post(client):
    response = client.post(
        '/couriers',
        json.dumps(CORRECT_POST_DATA),
        content_type="application/json")

    assert response.status_code == status.HTTP_201_CREATED
    assert len(response.data["couriers"]) == 3
    ids = [item['courier_id'] for item in CORRECT_POST_DATA['data']]
    for c in response.data["couriers"]:
        assert c['id'] in ids
    assert Courier.objects.count() == 3
    assert Region.objects.count() == 5

    for c in CORRECT_POST_DATA['data']:
        courier = (
            Courier.objects
            .filter(pk=c['courier_id'])
            .prefetch_related('working_hours', 'regions', 'orders')[0]
        )
        courier_type = Courier.CourierType(courier.courier_type).label
        assert courier_type == c['courier_type']
        assert set([r.pk for r in courier.regions.all()]) == set(c['regions'])
        assert courier.orders.count() == 0
        working_hours = [str(wh) for wh in courier.working_hours.all()]
        assert set(working_hours) == set(c['working_hours'])


@pytest.fixture
def post_and_assert_fn():
    def post_and_assert(client, incorrect_data):
        response = client.post(
            '/couriers',
            json.dumps(incorrect_data),
            content_type="application/json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'validation_error' in response.data
        assert 'couriers' in response.data['validation_error']
        data = response.data['validation_error']['couriers']
        assert len(data) == 1
        assert str(data[0]['id']) == '1'
    return post_and_assert


@pytest.mark.django_db
@pytest.mark.integration
def test_invalid_region(client, post_and_assert_fn):
    incorrect_data = deepcopy(CORRECT_POST_DATA)
    incorrect_data['data'][0]['regions'] = [-1]
    post_and_assert_fn(client, incorrect_data)


@pytest.mark.django_db
@pytest.mark.integration
def test_invalid_courier_type(client, post_and_assert_fn):
    incorrect_data = deepcopy(CORRECT_POST_DATA)
    incorrect_data['data'][0]['courier_type'] = 'carpet-plane'
    post_and_assert_fn(client, incorrect_data)


@pytest.mark.django_db
@pytest.mark.integration
def test_invalid_working_hours(client, post_and_assert_fn):
    incorrect_data = deepcopy(CORRECT_POST_DATA)
    incorrect_data['data'][0]['working_hours'] = '03.09.09 10:00-15:00'
    post_and_assert_fn(client, incorrect_data)
