from django.utils import timezone
from django.core.paginator import Paginator
from django.db import transaction
from .models import Order, Courier, Region, WorkingHours, DeliveryHours
from django.db.models import Max


@transaction.atomic
def assign_orders(courier):
    available_orders = (
        Order.objects
             .get_available_orders(courier)
             .order_by('-weight')
    )

    selected_orders = []
    # chunk size can be different
    paginator = Paginator(available_orders, per_page=5)

    weight_capacity = courier.get_weight_balance()
    if weight_capacity < 0:
        raise ValueError("Weight capacity for the courier is negative!")

    assigned_time = timezone.now()
    for page in paginator:
        page_break = False

        for order in page.object_list:
            if order.weight > weight_capacity:
                page_break = True
                break
            else:
                order.courier = courier
                order.status = Order.OrderStatus.ASSIGNED
                order.assigned_time = assigned_time
                selected_orders.append(order)
                weight_capacity -= order.weight

        if page_break:
            break
    Order.objects.bulk_update(selected_orders,
                              ['courier', 'status', 'assigned_time'])
    return selected_orders


def complete_order(courier: Courier, order: Order):
    order.status = Order.OrderStatus.COMPLETE
    order.complete_time = timezone.now()

    last_complete_time = (
        Courier.objects
        .filter(pk=courier.pk)
        .filter(orders__assigned_time=order.assigned_time)
        .aggregate(Max('orders__complete_time'))
    )['orders__complete_time__max']
    last_complete_time = last_complete_time or order.assigned_time
    order.delivery_time = order.complete_time - last_complete_time
    order.save()
    return order


def create_courier(data: dict):
    regions = data.pop('regions')
    regions = [Region.objects.get_or_create(pk=r)[0] for r in regions]
    working_hours = data.pop('working_hours')

    courier = Courier(**data)
    courier.save()
    courier.regions.add(*regions)

    WorkingHours.objects.bulk_create(
        [WorkingHours.from_string(s, courier=courier) for s in working_hours])
    return courier


@transaction.atomic
def update_courier(instance, data):
    instance.courier_type = data.get('courier_type', instance.courier_type)
    instance.save()

    if 'regions' in data:
        instance.regions.clear()
        instance.regions.add(
            *[Region.objects.get_or_create(pk=r)[0] for r in data['regions']])

    if 'working_hours' in data:
        instance.working_hours.all().delete()
        wh_instances = [
            WorkingHours.from_string(s, courier=instance)
            for s in data['working_hours']]
        WorkingHours.objects.bulk_create(wh_instances)

    instance.save()
    available_orders = list(
        instance.orders.all()
        .get_available_orders(instance,
                              required_status=Order.OrderStatus.ASSIGNED,
                              apply_weight_filter=False)
        .order_by('weight')
    )
    weight_balance = instance.get_weight_balance()
    while available_orders and weight_balance < 0:
        order = available_orders.pop(0)
        order.return_to_open()
        weight_balance += order.weight

    return instance


def create_order(data):
    delivery_hours = data.pop('delivery_hours')
    region = Region.objects.get_or_create(pk=data.pop('region'))[0]
    order = Order(region=region, **data)
    order.save()
    DeliveryHours.objects.bulk_create(
        [DeliveryHours.from_string(s, order=order) for s in delivery_hours])
    return order
