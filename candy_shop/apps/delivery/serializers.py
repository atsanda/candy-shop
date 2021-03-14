from rest_framework import serializers
from .models import Courier, Region, WorkingHours
from .validators import RegexValidator
from django.db.models.manager import Manager
import logging


class WorkingHoursField(serializers.StringRelatedField):
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


class CourierSerializer(serializers.ModelSerializer):
    working_hours = WorkingHoursField(
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

        WorkingHours.objects.bulk_create_from_str(validated_data['working_hours'], courier)

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
            WorkingHours.objects.bulk_create_from_str(validated_data['working_hours'], instance)

        #!TODO orders logic

        return instance

    def validate(self, data):
        if hasattr(self, 'initial_data'):
            unknown_keys = set(self.initial_data.keys()) - set(self.fields.keys())
            if unknown_keys:
                raise serializers.ValidationError("Got unknown fields: {}".format(unknown_keys))
        return data


    def run_validation(self, initial_data):
        try:
            return super().run_validation(initial_data)
        except serializers.ValidationError as e:
            logging.error(e, exc_info=True)
            raise serializers.ValidationError({'id': initial_data.get('courier_id', None)})
