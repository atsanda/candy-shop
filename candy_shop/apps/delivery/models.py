from decimal import Decimal

from django.db import models
from django.db.models import QuerySet, Q, Avg, Min, Count, Case, When, F, Sum
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

    class CourierType(models.IntegerChoices):
        FOOT = 10, 'foot'
        BIKE = 15, 'bike'
        CAR = 50, 'car'

        def get_earnings_coef(self):
            return {
                'foot': 2,
                'bike': 5,
                'car': 9,
                }[self.label]

    courier_type = models.IntegerField(choices=CourierType.choices)
    regions = models.ManyToManyField(Region)

    @property
    def rating(self):
        q_res = (
            self.orders.all()
            .values('region')
            .annotate(Avg('delivery_time'))
            .aggregate(Min('delivery_time__avg'))
        )
        min_avg_delivery_time = q_res['delivery_time__avg__min']
        if min_avg_delivery_time is None:
            return None

        rating = 5 * (60*60 - min(min_avg_delivery_time.total_seconds(), 60*60)) / (60*60)
        return round(rating, 2)

    @property
    def earnings(self):
        q_res = (
            self.orders.all()
            .values('assigned_time')
            .annotate(
                cnt_assigned_orders=Count('*'),
                cnt_completed_orders=Count(
                    Case(
                        When(status=Order.OrderStatus.COMPLETE, then=F('status'))
                    ))
                )
            .filter(cnt_assigned_orders=F('cnt_completed_orders'))
            .aggregate(n_deliviries_complete=Count('assigned_time', distinct=True))
        )
        n_deliviries_complete = q_res.get('n_deliviries_complete', 0)
        C = Courier.CourierType(self.courier_type).get_earnings_coef()
        return n_deliviries_complete * 500 * C

    def get_orders_weight(self):
        return (
            self.orders.all()
            .filter(status=Order.OrderStatus.ASSIGNED)
            .aggregate(weight__sum=Sum('weight')
        )['weight__sum'])

    def get_weight_balance(self):
        current_weight = self.get_orders_weight()
        weight_capacity = self.courier_type - (current_weight or 0)
        return weight_capacity


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


class OrderQuerySet(QuerySet):
    def get_available_orders(self,
                             courier: Courier,
                             required_status: str = 'open',
                             apply_weight_filter: bool = True):
        qs = self.filter(region__in=courier.regions.all())
        qs = qs.filter(status=required_status)
        if apply_weight_filter:
            qs = qs.filter(weight__lte=courier.courier_type)
        filter_wh = None
        for wh in courier.working_hours.all():
            q = Q(
                Q(delivery_hours__starts_at__lt=wh.finishes_at) & 
                Q(delivery_hours__finishes_at__gt=wh.starts_at)
            )
            filter_wh = filter_wh | q if filter_wh is not None else q
        qs = qs.filter(filter_wh)
        qs = qs.distinct()
        return qs


class Order(models.Model):
    objects = OrderQuerySet.as_manager()

    MIN_WEIGHT = Decimal('0.01')
    MAX_WEIGHT = Decimal('50')

    class OrderStatus(models.TextChoices):
        OPEN = 'open'
        ASSIGNED = 'assigned'
        COMPLETE = 'complete'

    order_id = models.BigAutoField(primary_key=True)
    weight = models.DecimalField(max_digits=4, decimal_places=2)
    region = models.ForeignKey(Region, on_delete=models.PROTECT)
    courier = models.ForeignKey(Courier, on_delete=models.PROTECT, related_name='orders', blank=True, null=True)
    status = models.CharField(max_length=10, choices=OrderStatus.choices, default=OrderStatus.OPEN)
    open_time = models.DateTimeField(auto_now=True)
    assigned_time = models.DateTimeField(blank=True, null=True)
    complete_time = models.DateTimeField(blank=True, null=True)
    delivery_time = models.DurationField(blank=True, null=True)

    def return_to_open(self):
        self.status = self.OrderStatus.OPEN
        self.assigned_time = None
        self.courier = None
        self.save()


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
