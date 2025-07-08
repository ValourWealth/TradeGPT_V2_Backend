from rest_framework import serializers
from .models import ChatSession, ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'session', 'sender', 'content', 'created_at']
        read_only_fields = ['id', 'created_at', 'session']

    def validate(self, data):
        if 'sender' not in data or 'content' not in data:
            raise serializers.ValidationError("Both 'sender' and 'content' are required.")
        return data


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = ['id', 'user', 'title', 'created_at', 'messages']
        read_only_fields = ['user', 'created_at']
