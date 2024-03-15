from rest_framework import serializers


from .models import model_Note


class NoteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    slug = serializers.SlugField(max_length=250)
    obj = serializers.CharField()
    predicat = serializers.CharField()
    subj = serializers.CharField()
    publish = serializers.DateTimeField()
    created = serializers.DateTimeField()
    updated = serializers.DateTimeField()
    status = serializers.CharField()
    author_id = serializers.IntegerField()

    def create(self, validated_data):
        return model_Note.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.slug = validated_data.get('slug', instance.slug)
        instance.obj = validated_data.get('obj', instance.body)
        instance.predicat = validated_data.get('predicat', instance.body)
        instance.subj = validated_data.get('subj', instance.body)
        instance.created = validated_data.get('created', instance.created)
        instance.updated = validated_data.get('updated', instance.updated)
        instance.status = validated_data.get('status', instance.status)
        instance.author_id = validated_data.get('author_id', instance.author_id)
        instance.save()
        return instance
