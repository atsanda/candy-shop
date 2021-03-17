from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from .models import Courier, Order
from rest_framework.generics import GenericAPIView
from .serializers import CourierSerializer, OrderSerializer, AssignSerializer, CompleteOrderSerializer
from .services import assign_orders, complete_order


class DeliveryCreateMixin(mixins.CreateModelMixin):
    entity_name = 'object'
    entity_id_field = 'id'

    def create(self, request, *args, **kwargs):
        is_many = 'data' in request.data
        serializer = self.get_serializer(
            data=request.data['data'] if is_many else request.data,
            many=is_many,
        )
        if not serializer.is_valid(raise_exception=False):
            errors = [e for e in serializer.errors if e]
            error_message = {'validation_error': {self.entity_name: errors}}
            return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        response_data = {self.entity_name: [{'id': d[self.entity_id_field]} for d in serializer.data]}
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)


class CourierViewSet(DeliveryCreateMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin,
                     mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    queryset = Courier.objects.all()
    serializer_class = CourierSerializer
    entity_name = 'couriers'
    entity_id_field = 'courier_id'


class OrderViewSet(DeliveryCreateMixin,
                   mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    entity_name = 'orders'
    entity_id_field = 'order_id'


class AssignView(GenericAPIView):
    serializer_class = AssignSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assigned_orders = assign_orders(serializer.validated_data['courier_id'])
        response_data = {'orders': [{'id': o.pk} for o in assigned_orders]}
        return Response(response_data, status=status.HTTP_200_OK)


class CompleteOrderView(GenericAPIView):
    serializer_class = CompleteOrderSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = complete_order(
            serializer.validated_data['courier_id'],
            serializer.validated_data['order_id'])
        response_data = {'order_id': order.pk}
        return Response(response_data, status=status.HTTP_200_OK)
