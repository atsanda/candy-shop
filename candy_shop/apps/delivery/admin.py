from django.contrib import admin

from .models import Region, Courier, WorkingHours

admin.site.register(Region)
admin.site.register(Courier)
admin.site.register(WorkingHours)
