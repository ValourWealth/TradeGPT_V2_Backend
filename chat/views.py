from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ChatSession
from .serializers import ChatSessionSerializer

class CreateChatSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        title = request.data.get("title")
        if not title:
            return Response({"error": "Title is required"}, status=400)

        session = ChatSession.objects.create(user=request.user, title=title)
        serializer = ChatSessionSerializer(session)
        return Response(serializer.data)
