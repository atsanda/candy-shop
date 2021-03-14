from django.contrib import admin

from .models import Region, Courier, WorkingHours, Order, DeliveryHours

admin.site.register(Region)
admin.site.register(Courier)
admin.site.register(WorkingHours)
admin.site.register(Order)
admin.site.register(DeliveryHours)
