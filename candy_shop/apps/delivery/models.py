from django.db import models


class Region(models.Model):
    pass


class Courier(models.Model):

    class CourierType(models.TextChoices):
        FOOT = "foot"
        BIKE = "bike"
        CAR = "car"

    curier_type = models.CharField(
      max_length=5,
      choices=CourierType.choices
    )

    regions = models.ManyToManyField(Region)


class WorkingHours(models.Model):
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE)
    starts_at = models.TimeField()
    finishes_at = models.TimeField()
