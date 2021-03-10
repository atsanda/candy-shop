from rest_framework import serializers
from .models import Courier, Region, WorkingHours
from .validators import RegexValidator


class WorkingHoursField(serializers.StringRelatedField):
    def to_internal_value(self, data):
        return data


class RegionsField(serializers.PrimaryKeyRelatedField):
    # This is needed to stub queryset and avoid assertion inside __init__
    queryset = object()

    def to_internal_value(self, data):
        if self.pk_field is not None:
            data = self.pk_field.to_internal_value(data)
        return data


class CourierSerializer(serializers.ModelSerializer):
    working_hours = WorkingHoursField(
        many=True, validators=[RegexValidator(WorkingHours.regex)])
    regions = RegionsField(many=True)
    courier_id = serializers.IntegerField()

    class Meta:
        model = Courier
        fields = ['courier_id', 'curier_type', 'regions', 'working_hours']

    def create(self, validated_data):
        regions = validated_data.pop('regions')
        regions = [Region.objects.get_or_create(pk=r)[0] for r in regions]
        working_hours = validated_data.pop('working_hours')

        courier = Courier(**validated_data)
        courier.save()
        courier.regions.add(*regions)

        for h in working_hours:
            working_hours = WorkingHours.from_string(h)
            working_hours.courier = courier
            working_hours.save()

        return courier
