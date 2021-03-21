from django.utils import timezone
from django.core.paginator import Paginator
from django.db import transaction
from .models import Order, Courier
from django.db.models import Sum, Q, Max


@transaction.atomic
def assign_orders(courier):
    available_orders = Order.objects.get_available_orders(courier)

    selected_orders = []
    paginator = Paginator(available_orders, per_page=5)  # chunk size can be different

    #!TODO Move to queryset manager
    current_weight = (
        Courier.objects
        .filter(pk=courier.pk)
        .filter(orders__status=Order.OrderStatus.ASSIGNED)
        .aggregate(
            Sum('orders__weight')
        )['orders__weight__sum'])
    weight_capacity = courier.courier_type - (current_weight or 0)
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
    Order.objects.bulk_update(selected_orders, ['courier', 'status', 'assigned_time'])
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
    print(last_complete_time)
    order.delivery_time = order.complete_time - last_complete_time
    order.save()
    return order
