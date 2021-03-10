import re
from rest_framework import serializers


class RegexValidator:
    def __init__(self, regex_expression):
        self.rgx = re.compile(regex_expression)

    def __call__(self, value):
        if not self.rgx.match(value):
            message = "This field must has invalid format"
            raise serializers.ValidationError(message)
