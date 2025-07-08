from rest_framework import generics, permissions
from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer

class ChatSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ChatMessageListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        session_id = self.kwargs.get("session_id")
        return ChatMessage.objects.filter(session__id=session_id, session__user=self.request.user).order_by('created_at')

    def perform_create(self, serializer):
        session_id = self.kwargs.get("session_id")
        session = ChatSession.objects.get(id=session_id, user=self.request.user)
        serializer.save(session=session)
