from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Courier
from .serializers import CourierSerializer


class CourierViewSet(viewsets.ModelViewSet):
    queryset = Courier.objects.all()
    serializer_class = CourierSerializer

    def create(self, request, *args, **kwargs):
        is_many = 'data' in request.data
        serializer = self.get_serializer(
            data=request.data['data'] if is_many else request.data,
            many=is_many,
        )
        if not serializer.is_valid(raise_exception=False):
            error_message = {'validation_error': {'couriers': serializer.errors}}
            return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        response_data = {'couriers': [{'id': d['courier_id']} for d in serializer.data]}
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
