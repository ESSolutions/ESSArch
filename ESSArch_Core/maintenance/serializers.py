from rest_framework import serializers

from ESSArch_Core.maintenance.models import AppraisalRule, AppraisalJob, ConversionRule, ConversionJob


class AppraisalRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalRule
        fields = (
            'id', 'name', 'frequency', 'specification',
        )


class AppraisalJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalJob
        fields = (
            'id', 'rule', 'status', 'start_date', 'end_date',
        )


class ConversionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversionRule
        fields = (
            'id', 'name', 'frequency', 'specification',
        )


class ConversionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversionJob
        fields = (
            'id', 'rule', 'status', 'start_date', 'end_date',
        )
