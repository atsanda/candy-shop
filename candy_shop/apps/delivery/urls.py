from django.urls import path, include
from rest_framework import routers
from .views import CourierViewSet, OrderViewSet, AssignView, CompleteOrderView


router = routers.DefaultRouter(trailing_slash=False)
router.register(r'couriers', CourierViewSet)
router.register(r'orders', OrderViewSet)


urlpatterns = [
    path('orders/assign', AssignView.as_view()),
    path('orders/complete', CompleteOrderView.as_view()),
    path('', include(router.urls)),
]
