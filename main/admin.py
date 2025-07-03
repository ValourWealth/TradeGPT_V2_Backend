# from django.contrib import admin
# from . models import ChatMessage, ChatSession
# # Register your models here.

# admin.site.register(ChatSession)
# admin.site.register(ChatMessage)

from django.contrib import admin
from .models import ChatSession, ChatMessage

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'username', 'created_at')
    search_fields = ('username',)

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'timestamp')
    list_filter = ('role',)
    search_fields = ('content',)
