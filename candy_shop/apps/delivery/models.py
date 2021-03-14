from decimal import Decimal

from django.db import models
from django.db.models import QuerySet
from typing import List


class Region(models.Model):
    pass


class Hours(models.Model):
    regex = r'^(2[0-3]|[01]\d):([0-5]\d)-(2[0-3]|[01]\d):([0-5]\d)$'
    time_format = r'%H:%M'

    starts_at = models.TimeField()
    finishes_at = models.TimeField()

    class Meta:
        abstract = True

    @classmethod
    def from_string(cls, string):
        """
        string: a string with format `HH:MM-HH:MM`,
                it is assumed that string is validated
        """
        starts_at, finishes_at = string.split('-')
        return cls(starts_at=starts_at, finishes_at=finishes_at)

    def __str__(self):
        return f"{self.starts_at:%H:%M}-{self.finishes_at:%H:%M}"


class Courier(models.Model):
    courier_id = models.BigAutoField(primary_key=True)

    class CourierType(models.TextChoices):
        FOOT = "foot"
        BIKE = "bike"
        CAR = "car"

    courier_type = models.CharField(
      max_length=5,
      choices=CourierType.choices
    )

    regions = models.ManyToManyField(Region)


class WorkingHoursQuerySet(QuerySet):
    def bulk_create_from_str(self, working_hours_strs: List[str], courier: Courier):
        self.bulk_create(
            [WorkingHours.from_string(s, courier=courier) for s in working_hours_strs]
        )


class WorkingHours(models.Model):
    """
    !TODO nest from Hours
    """
    objects = WorkingHoursQuerySet.as_manager()

    regex = r'^(2[0-3]|[01]\d):([0-5]\d)-(2[0-3]|[01]\d):([0-5]\d)$'
    time_format = r'%H:%M'

    courier = models.ForeignKey(
        Courier,
        on_delete=models.CASCADE,
        related_name='working_hours')
    starts_at = models.TimeField()
    finishes_at = models.TimeField()

    @classmethod
    def from_string(cls, string, courier=None):
        """
        string: a string with format `HH:MM-HH:MM`,
                it is assumed that string is validated
        """
        starts_at, finishes_at = string.split('-')
        return cls(courier=courier, starts_at=starts_at, finishes_at=finishes_at)

    def __str__(self):
        return f"{self.starts_at:%H:%M}-{self.finishes_at:%H:%M}"


class Order(models.Model):
    MIN_WEIGHT = Decimal('0.01')
    MAX_WEIGHT = Decimal('50')

    order_id = models.BigAutoField(primary_key=True)
    weight = models.DecimalField(max_digits=4, decimal_places=2)
    region = models.ForeignKey(Region, on_delete=models.PROTECT)


class DeliveryHours(Hours):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='delivery_hours')

    @classmethod
    def from_string(cls, string, order=None):
        instance = super().from_string(string)
        instance.order = order
        return instance
