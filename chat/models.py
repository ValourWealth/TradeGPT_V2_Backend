import uuid
from django.db import models
from accounts.models import User

class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_sessions")
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255, blank=True, default="New Session")

    def __str__(self):
        return f"{self.user.email} - {self.title}"

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20)  # "user" or "assistant"
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
