import re
from rest_framework import serializers


class RegexValidator:
    def __init__(self, regex_expression):
        self.rgx = re.compile(regex_expression)

    def __call__(self, value):
        if not self.rgx.match(value):
            message = "This field must has invalid format"
            raise serializers.ValidationError(message)


class IntervalValidator:
    def __init__(self, left, right, inclusive_left=True, inclusive_right=True):
        self.left = left
        self.right = right
        self.inclusive_left = inclusive_left
        self.inclusive_right = inclusive_right

    def __call__(self, value):
        if (value < self.left or
            (not self.inclusive_left and value == self.left) or
            value > self.right or
            (not self.inclusive_right and value == self.right)):
            message = f"Value {value} is out of allowed interval"
            raise serializers.ValidationError(message)
