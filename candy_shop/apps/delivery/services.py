from django.core.paginator import Paginator
from django.db import transaction
from .models import Order, Courier
from django.db.models import Sum, Q


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

    for page in paginator:
        page_break = False

        for order in page.object_list:
            if order.weight > weight_capacity:
                page_break = True
                break
            else:
                order.courier = courier
                order.status = Order.OrderStatus.ASSIGNED
                selected_orders.append(order)
                weight_capacity -= order.weight

        if page_break:
            break
    Order.objects.bulk_update(selected_orders, ['courier', 'status'])
    return selected_orders


def complete_order(courier: Courier, order: Order):
    order.status = Order.OrderStatus.COMPLETE
    order.courier = None
    order.save()
    return order
