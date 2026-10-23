from django.db import transaction
from rest_framework import serializers

from .models import Choice, Exam, Question


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text", "is_correct"]


class ChoiceResourceSerializer(ChoiceSerializer):
    """Standalone choice resource; question remains a primary-key relationship."""
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())

    class Meta(ChoiceSerializer.Meta):
        fields = ["id", "question", "text", "is_correct"]

    def validate(self, attrs):
        instance = self.instance
        question = attrs.get("question", instance.question if instance else None)
        if instance and question.pk != instance.question_id:
            raise serializers.ValidationError({"question": "No se puede mover una opción a otra pregunta."})

        siblings = question.choices.exclude(pk=instance.pk) if instance else question.choices.all()
        correct = attrs.get("is_correct", instance.is_correct if instance else False)
        flags = list(siblings.values_list("is_correct", flat=True)) + [correct]
        if len(flags) < 2:
            raise serializers.ValidationError({"detail": "Una pregunta necesita al menos dos opciones."})
        if sum(flags) != 1:
            raise serializers.ValidationError({"detail": "Debe haber exactamente una opción correcta."})
        return attrs

    @staticmethod
    def validate_deletion(instance):
        remaining = instance.question.choices.exclude(pk=instance.pk)
        if remaining.count() < 2:
            raise serializers.ValidationError({"detail": "Una pregunta necesita al menos dos opciones."})
        if remaining.filter(is_correct=True).count() != 1:
            raise serializers.ValidationError({"detail": "Debe haber exactamente una opción correcta."})


class ExamSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Exam
        fields = ["id", "title", "created_at", "question_count"]
        read_only_fields = ["created_at"]


class QuestionSerializer(serializers.ModelSerializer):
    # Choices travel nested inside the question; the exam travels as an identifier.
    choices = ChoiceSerializer(many=True)

    class Meta:
        model = Question
        fields = ["id", "exam", "text", "choices", "created_at"]
        read_only_fields = ["created_at"]

    def validate_choices(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("Una pregunta necesita al menos dos opciones.")
        if sum(1 for choice in value if choice.get("is_correct")) != 1:
            raise serializers.ValidationError("Debe haber exactamente una opción correcta.")
        return value

    def create(self, validated_data):
        choices = validated_data.pop("choices")
        with transaction.atomic():
            question = Question.objects.create(**validated_data)
            Choice.objects.bulk_create(Choice(question=question, **choice) for choice in choices)
        return question

    def update(self, instance, validated_data):
        choices = validated_data.pop("choices", None)
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if choices is not None:  # sent choices replace the old ones
                instance.choices.all().delete()
                Choice.objects.bulk_create(Choice(question=instance, **choice) for choice in choices)
        return instance
