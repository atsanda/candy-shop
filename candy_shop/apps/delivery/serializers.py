from rest_framework import serializers
from .models import Courier, Region, WorkingHours, DeliveryHours, Order
from .validators import RegexValidator, IntervalValidator
from django.db.models.manager import Manager
import logging


class ChoiceField(serializers.ChoiceField):
    """
    Doesn't work correctly in case of IntegerChoice
    Had to override
    Taken from https://stackoverflow.com/questions/28945327/django-rest-framework-with-choicefield
    """
    def to_representation(self, obj):
        if obj == '' and self.allow_blank:
            return obj
        return self._choices[obj]

    def to_internal_value(self, data):
        # To support inserts with the value
        if data == '' and self.allow_blank:
            return ''

        for key, val in self._choices.items():
            if val == data:
                return key
        self.fail('invalid_choice', input=data)


class HoursField(serializers.StringRelatedField):
    def to_internal_value(self, data):
        return data


class RegionsField(serializers.ListField):
    def __init__(self):
        super().__init__(child=serializers.IntegerField(min_value=1))

    def to_representation(self, value):
        # to options here 
        if isinstance(value, list):  # on validation error in another filed
            return value
        elif isinstance(value, Manager):  # on usual
            return [int(v.pk) for v in value.all()]
        else:
            raise serializers.ValidationError()

    def to_internal_value(self, data):
        return super().to_internal_value(data)

    def run_validation(self, initial_data):
        return super().run_validation(initial_data)


class DeliveryModelSerializer(serializers.ModelSerializer):
    def get_initial_data_keys(self):
        if isinstance(self.initial_data, dict):
            return self.initial_data.keys()
        elif isinstance(self.initial_data, list) and isinstance(self.initial_data[0], dict):
            return self.initial_data[0].keys()
        else:
            raise serializers.ValidationError("Invalid data passed")

    def validate(self, data):
        if hasattr(self, 'initial_data'):
            unknown_keys = set(self.get_initial_data_keys()) - set(self.fields.keys())
            if unknown_keys:
                raise serializers.ValidationError("Got unknown fields: {}".format(unknown_keys))
        return data

    def run_validation(self, initial_data, id_field):
        try:
            return super().run_validation(initial_data)
        except serializers.ValidationError as e:
            logging.error(e, exc_info=True)
            raise serializers.ValidationError({'id': initial_data.get(id_field, None)})


class CourierSerializer(DeliveryModelSerializer):
    working_hours = HoursField(
        many=True, validators=[RegexValidator(WorkingHours.regex)])
    regions = RegionsField()
    courier_id = serializers.IntegerField()
    courier_type = ChoiceField(Courier.CourierType.choices)

    class Meta:
        model = Courier
        fields = ['courier_id', 'courier_type', 'regions', 'working_hours']

    def create(self, validated_data):
        regions = validated_data.pop('regions')
        regions = [Region.objects.get_or_create(pk=r)[0] for r in regions]
        working_hours = validated_data.pop('working_hours')

        courier = Courier(**validated_data)
        courier.save()
        courier.regions.add(*regions)

        # !TODO revise this
        WorkingHours.objects.bulk_create_from_str(working_hours, courier)

        return courier

    def update(self, instance, validated_data):
        instance.courier_type = validated_data.get('courier_type', instance.courier_type)
        instance.save()

        if 'regions' in validated_data:
            instance.regions.clear()
            instance.regions.add(
                *[Region.objects.get_or_create(pk=r)[0] for r in validated_data['regions']])
            #!TODO regions cleanup

        if 'working_hours' in validated_data:
            instance.working_hours.all().delete()
            # !TODO revise this
            WorkingHours.objects.bulk_create_from_str(validated_data['working_hours'], instance)

        instance.save()
        available_orders = list(
            instance.orders.all()
            .get_available_orders(instance,
                                  required_status=Order.OrderStatus.ASSIGNED,
                                  apply_weight_filter=False)
            .order_by('weight')
        )
        weight_balance = instance.get_weight_balance()
        while available_orders and weight_balance < 0:
            order = available_orders.pop(0)
            order.return_to_open()
            weight_balance += order.weight

        return instance

    def run_validation(self, initial_data):
        return super().run_validation(initial_data, 'courier_id')


class SingleRegionField(serializers.IntegerField):
    def __init__(self):
        super().__init__(min_value=1)

    def to_representation(self, value):
        return int(value.pk)


class OrderSerializer(DeliveryModelSerializer):
    delivery_hours = HoursField(
        many=True, validators=[RegexValidator(WorkingHours.regex)])
    order_id = serializers.IntegerField()
    weight = serializers.DecimalField(
        max_digits=Order._meta.get_field('weight').max_digits,
        decimal_places=Order._meta.get_field('weight').decimal_places,
        validators=[IntervalValidator(left=Order.MIN_WEIGHT, right=Order.MAX_WEIGHT)])
    region = SingleRegionField()

    class Meta:
        model = Order
        fields = ['order_id', 'weight', 'region', 'delivery_hours']

    def create(self, validated_data):
        delivery_hours = validated_data.pop('delivery_hours')
        region = Region.objects.get_or_create(pk=validated_data.pop('region'))[0]
        order = Order(region=region, **validated_data)
        order.save()
        DeliveryHours.objects.bulk_create(
            [DeliveryHours.from_string(s, order=order) for s in delivery_hours]
        )
        return order

    def run_validation(self, initial_data):
        return super().run_validation(initial_data, 'order_id')


class AssignSerializer(serializers.Serializer):
    courier_id = serializers.PrimaryKeyRelatedField(
        queryset=Courier.objects.all().prefetch_related('regions', 'working_hours')
    )


class CompleteOrderSerializer(serializers.Serializer):
    courier_id = serializers.PrimaryKeyRelatedField(queryset=Courier.objects.all())
    order_id = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())

    def validate_order_id(self, value):
        if value.status != Order.OrderStatus.ASSIGNED:
            raise serializers.ValidationError("Order has invalid status")
        return value

    def validate(self, data):
        if data['order_id'].courier is None or data['order_id'].courier.pk != data['courier_id'].pk:
            raise serializers.ValidationError("The Order doesn't belong to the courier")
        return data


class CourierDetailsSerializer(CourierSerializer):
    rating = serializers.FloatField()
    earnings = serializers.IntegerField()

    class Meta:
        model = Courier
        fields = ['courier_id', 'courier_type', 'regions', 'working_hours', 'rating', 'earnings']