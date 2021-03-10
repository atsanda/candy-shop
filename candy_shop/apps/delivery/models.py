from django.db import models


class Region(models.Model):
    pass


class Courier(models.Model):
    courier_id = models.BigAutoField(primary_key=True)

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
    regex = r'^(2[0-3]|[01]\d):([0-5]\d)-(2[0-3]|[01]\d):([0-5]\d)$'
    time_format = r'%H:%M'

    courier = models.ForeignKey(
        Courier,
        on_delete=models.CASCADE,
        related_name='working_hours')
    starts_at = models.TimeField()
    finishes_at = models.TimeField()

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
