from rest_framework import serializers
from .models import Courier, Region, WorkingHours, DeliveryHours, Order
from .validators import RegexValidator, IntervalValidator
from django.db.models.manager import Manager
import logging


class HoursField(serializers.StringRelatedField):
    def to_internal_value(self, data):
        return data


class RegionsField(serializers.ListField):
    def __init__(self):
        super().__init__(child=serializers.IntegerField())

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

        #!TODO orders logic

        return instance

    def run_validation(self, initial_data):
        return super().run_validation(initial_data, 'courier_id')


class OrderSerializer(DeliveryModelSerializer):
    delivery_hours = HoursField(
        many=True, validators=[RegexValidator(WorkingHours.regex)])
    order_id = serializers.IntegerField()
    weight = serializers.DecimalField(
        max_digits=Order._meta.get_field('weight').max_digits,
        decimal_places=Order._meta.get_field('weight').decimal_places,
        validators=[IntervalValidator(left=Order.MIN_WEIGHT, right=Order.MAX_WEIGHT)])

    class Meta:
        model = Order
        fields = ['order_id', 'weight', 'region', 'delivery_hours']

    def create(self, validated_data):
        delivery_hours = validated_data.pop('delivery_hours')
        order = Order(**validated_data)
        order.save()
        DeliveryHours.objects.bulk_create(
            [DeliveryHours.from_string(s, order=order) for s in delivery_hours]
        )
        return order

    def run_validation(self, initial_data):
        return super().run_validation(initial_data, 'order_id')