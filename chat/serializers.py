from rest_framework import serializers
from .models import ChatSession

class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ['id', 'user', 'title', 'created_at']
        read_only_fields = ['id', 'created_at']
