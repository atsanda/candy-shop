from rest_framework import serializers
from .models import Courier, WorkingHours, Order
from .validators import RegexValidator, IntervalValidator
from .services import create_courier, update_courier, create_order
from django.db.models.manager import Manager
import logging


class ChoiceField(serializers.ChoiceField):
    """
    Doesn't work correctly in case of IntegerChoice
    Had to override
    Taken from
    https://stackoverflow.com/questions/28945327/django-rest-framework-with-choicefield
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
        elif (isinstance(self.initial_data, list) and
              isinstance(self.initial_data[0], dict)):
            return self.initial_data[0].keys()
        else:
            raise serializers.ValidationError("Invalid data passed")

    def validate(self, data):
        if hasattr(self, 'initial_data'):
            unknown_keys = (set(self.get_initial_data_keys()) -
                            set(self.fields.keys()))
            if unknown_keys:
                msg = "Got unknown fields: {}".format(unknown_keys)
                raise serializers.ValidationError(msg)
        return data

    def run_validation(self, initial_data, id_field):
        try:
            return super().run_validation(initial_data)
        except serializers.ValidationError as e:
            # it is not the best practice, but required by the task
            logging.error(e, exc_info=True)
            err_data = {'id': initial_data.get(id_field, None)}
            raise serializers.ValidationError(err_data)


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
        return create_courier(validated_data)

    def update(self, instance, validated_data):
        return update_courier(instance, validated_data)

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
        validators=[IntervalValidator(left=Order.MIN_WEIGHT,
                                      right=Order.MAX_WEIGHT)])
    region = SingleRegionField()

    class Meta:
        model = Order
        fields = ['order_id', 'weight', 'region', 'delivery_hours']

    def create(self, validated_data):
        return create_order(validated_data)

    def run_validation(self, initial_data):
        return super().run_validation(initial_data, 'order_id')


class AssignSerializer(serializers.Serializer):
    courier_id = serializers.PrimaryKeyRelatedField(
        queryset=Courier.objects
                        .all()
                        .prefetch_related('regions', 'working_hours'))


class CompleteOrderSerializer(serializers.Serializer):
    courier_id = serializers.PrimaryKeyRelatedField(
        queryset=Courier.objects.all())
    order_id = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())

    def validate_order_id(self, value):
        if not (value.status in [Order.OrderStatus.ASSIGNED,
                                 Order.OrderStatus.COMPLETE]):
            raise serializers.ValidationError("Order has invalid status")
        return value

    def validate(self, data):
        if (
            data['order_id'].courier is None or
            data['order_id'].courier.pk != data['courier_id'].pk
        ):
            msg = "The Order doesn't belong to the courier"
            raise serializers.ValidationError(msg)
        return data


class CourierDetailsSerializer(CourierSerializer):
    rating = serializers.FloatField()
    earnings = serializers.IntegerField()

    class Meta:
        model = Courier
        fields = ['courier_id', 'courier_type', 'regions',
                  'working_hours', 'rating', 'earnings']
