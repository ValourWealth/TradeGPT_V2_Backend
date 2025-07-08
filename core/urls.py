"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from main.views import *
from main.views import DeepSeekChatView as DeepSeekChatStreamView
from main.views import DirectChatAIView

from accounts.views import SignupView, LoginView
from chat.views import *



urlpatterns = [
    path('admin/', admin.site.urls),
    
    # accounts app url:=================================================
    path('api/signup/', SignupView.as_view(), name='signup'),
    path('api/login/', LoginView.as_view(), name='login'),
    # ===================================================================
    
    
    # chat app ==========================================================
    path('api/sessions/', ChatSessionListCreateView.as_view(), name='chat-sessions'),
    path('api/sessions/<uuid:session_id>/messages/', ChatMessageListCreateView.as_view(), name='chat-messages'),
    # ===================================================================
    
    
    path("api/chat/start/", StartChatSessionView.as_view()),
    path("api/chat/sessions/<uuid:session_id>/messages/", MessageListCreateView.as_view()),
    path("api/chat/user-sessions/", UserChatSessionsView.as_view()),
    path("api/chat/message-limit/", DailyMessageLimitView.as_view()),
    
    path("api/deepseek-chat/", DeepSeekChatView.as_view()),
    path("api/deepseek-chat/stream", DeepSeekChatView.as_view()),  # ✅ NEW for streaming
    # for direct user chat 
     path("api/deepseek-chat/direct/", DirectChatAIView.as_view(), name="deepseek-direct-chat"),
    
]

# tradegptv2backend-production.up.railway.app
