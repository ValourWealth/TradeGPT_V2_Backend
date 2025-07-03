from django.shortcuts import render
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework import status
from .models import ChatSession, ChatMessage
from .utils import get_user_from_token
from django.utils.timezone import now
import uuid
from django.utils import timezone


class TradeGPTUserView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.GET.get("token")
        if not token:
            return Response({"error": "Token is missing"}, status=400)

        try:
            decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            return Response({
                "user_id": decoded.get("user_id"),
                "username": decoded.get("username"),
                "first_name": decoded.get("first_name"),
                "last_name": decoded.get("last_name"),
                "email": decoded.get("email"),
                "subscription_status": decoded.get("subscription_status"),
                "profile_photo": decoded.get("profile_photo"),
                "phone_number": decoded.get("phone_number"),
                "country": decoded.get("country"),
                "state": decoded.get("state"),
                "is_staff": decoded.get("is_staff"),
                "is_superuser": decoded.get("is_superuser"),
            })
        except jwt.ExpiredSignatureError:
            return Response({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)


class StartChatSessionView(APIView):
    def get(self, request):
        token = request.GET.get("token")
        user = get_user_from_token(token)

        session = ChatSession.objects.create(
            session_id=uuid.uuid4(),
            user_id=user["user_id"],
            username=user["username"],
        )
        return Response({"session_id": session.session_id})
    
    # Replace POST method with this logic:
    def post(self, request):
        token = request.GET.get("token")
        user = get_user_from_token(token)

        # ✅ Check if session for today already exists
        today = timezone.now().date()
        existing_session = ChatSession.objects.filter(
            user_id=user["user_id"],
            created_at__date=today
        ).first()

        if existing_session:
            return Response({"session_id": existing_session.session_id})
        else:
            session = ChatSession.objects.create(
                session_id=uuid.uuid4(),
                user_id=user["user_id"],
                username=user["username"],
            )
            return Response({"session_id": session.session_id})



class MessageListCreateView(APIView):
    def post(self, request, session_id):
        token = request.GET.get("token")
        user = get_user_from_token(token)

        try:
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)

        data = request.data
        ChatMessage.objects.create(
            session=session,
            role=data["role"],
            content=data["content"]
        )
        return Response({"message": "Saved"}, status=201)

    def get(self, request, session_id):
        token = request.GET.get("token")
        user = get_user_from_token(token)

        try:
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)

        messages = session.messages.order_by("timestamp")
        return Response([
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in messages
        ])



class UserChatSessionsView(APIView):
    def get(self, request):
        token = request.GET.get("token")
        user = get_user_from_token(token)

        sessions = ChatSession.objects.filter(user_id=user["user_id"]).order_by("-created_at")
        return Response([
            {"session_id": s.session_id, "created_at": s.created_at}
            for s in sessions
        ])


class DailyMessageLimitView(APIView):
    def get(self, request):
        token = request.GET.get("token")
        user = get_user_from_token(token)

        count = ChatMessage.objects.filter(
            session__user_id=user["user_id"],
            timestamp__date=now().date()
        ).count()

        max_allowed = {
            "free": 3,
            "premium": 5,
            "platinum": 10,
        }.get(user["subscription_status"], 3)

        return Response({"count": count, "max": max_allowed})

import re
import html
import logging
import time
import uuid

from django.http import StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from openai import OpenAI

from .models import ChatSession, ChatMessage
from .utils import get_user_from_token

logger = logging.getLogger(__name__)


# def clean_special_chars(text):
#     # Decode HTML entities
#     text = html.unescape(text)

#     # Remove unwanted headers/sections
#     text = re.sub(r'<h2>.*?(Response to User|Analysis|Summary|html).*?</h2>', '', text, flags=re.IGNORECASE)
#     text = re.sub(r'\b(Response\s*to\s*User|Analysis|Summary|html)\b', '', text, flags=re.IGNORECASE)

#     # Inject class="title" into all <h2> tags
#     text = re.sub(r'<h2([^>]*)>', r'<h2\1 class="title">', text)

#     # Remove backticks and code fences
#     text = text.replace("```", "")

#     # Fix glued words
#     text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
#     text = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', text)
#     text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
#     text = re.sub(r'\$(\d)', r'$ \1', text)

#     # Add space after hyphen if stuck
#     text = re.sub(r'-([^\s])', r'- \1', text)

#     # Remove empty tags
#     text = re.sub(r'<(p|h2)[^>]*>\s*</\1>', '', text)

#     # Normalize whitespace
#     text = re.sub(r'\s{2,}', ' ', text)
#     text = re.sub(r'\n{3,}', '\n\n', text)

#     return text.strip()
def clean_special_chars(text):
    import html
    import re

    text = html.unescape(text)

    # Fix glued sentences
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)          # MetaPlatforms → Meta Platforms
    text = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    text = re.sub(r'\$(\d)', r'$ \1', text)

    # Inject spacing after punctuation if missing
    text = re.sub(r'(?<=[a-zA-Z0-9])\.(?=[A-Z])', '. ', text)

    # Convert plain `-` bullets into <br/> for safety
    text = text.replace("\n- ", "<br/>- ")

    # Inject class into <h2>
    text = re.sub(r'<h2([^>]*)>', r'<h2\1 class="title">', text)

    # Remove unwanted headers
    text = re.sub(r'<h2>.*?(Response to User|Analysis|Summary|html).*?</h2>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(Response\s*to\s*User|Analysis|Summary|html)\b', '', text, flags=re.IGNORECASE)

    # Remove backticks or empty tags
    text = text.replace("```", "")
    text = re.sub(r'<(p|h2)[^>]*>\s*</\1>', '', text)

    # Normalize line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'\s{2,}', ' ', text)

    return text.strip()



def normalize_query_type(raw):
    raw = raw.lower().strip()
    if "price" in raw and "chart" in raw:
        return "price_chart"
    elif "news" in raw:
        return "recent_news"
    elif "fundamental" in raw or "technical" in raw:
        return "fundamental_analysis"
    else:
        return "default"


@method_decorator(csrf_exempt, name='dispatch')
class DeepSeekChatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            symbol = data.get("symbol", "N/A")
            name = data.get("name", "N/A")
            query_type = normalize_query_type(data.get("queryType", "default"))
            price = data.get("price", "N/A")
            open_ = data.get("open", "N/A")
            high = data.get("high", "N/A")
            low = data.get("low", "N/A")
            previous_close = data.get("previousClose", "N/A")
            volume = data.get("volume", "N/A")
            trend = data.get("trend", "N/A")
            news_list = data.get("news", [])

            MAX_TOKENS = min(max(int(data.get("tokenLimit", 1500)), 1), 8192)

            news_lines = ""
            for item in news_list[:5]:
                headline = item.get("headline", "No headline")
                time_str = item.get("time", "Unknown time")
                category = item.get("category", "General")
                news_lines += f"- {headline} at {time_str} | {category}\n"
            if not news_lines.strip():
                news_lines = "No major headlines available."

            # HTML prompt builder
            if query_type == "price_chart":
                prompt = f"""
You are TradeGPT, a financial data analyst. Respond in clean HTML format with structure and insights.

<h2>Price Movements for {name} ({symbol})</h2>
<p>
<b>Price:</b> ${price}<br/>
<b>Open:</b> ${open_}<br/>
<b>High:</b> ${high}<br/>
<b>Low:</b> ${low}<br/>
<b>Previous Close:</b> ${previous_close}<br/>
<b>Volume:</b> {volume}<br/>
<b>Trend:</b> {trend}
</p>

<h2>Key Observations</h2>
<ul>
  <li>Discuss volatility patterns</li>
  <li>Identify the trend direction</li>
  <li>Highlight any notable price swings or breakout points</li>
</ul>
"""
            elif query_type == "recent_news":
                prompt = f"""
You are TradeGPT, a financial news summarizer. Present recent headlines for {name} ({symbol}) in structured HTML format.

<h2>Recent News for {name} ({symbol})</h2>
<p>Below are the top headlines:</p>
<ul>
{''.join(f"<li>{item.get('headline', 'No headline')} - <i>{item.get('time', 'Unknown time')}</i> | {item.get('category', 'General')}</li>" for item in news_list[:5]) or "<li>No major headlines available.</li>"}
</ul>

<h2>Insights</h2>
<p>Summarize common themes across these stories — sentiment, market impact, or sector movements.</p>
"""
            elif query_type == "fundamental_analysis":
                prompt = f"""
You are TradeGPT, a senior financial analyst. Provide an HTML-structured analysis of {name} ({symbol}).

<h2>Company Overview</h2>
<p>
<b>Symbol:</b> {symbol}<br/>
<b>Company:</b> {name}<br/>
<b>Price:</b> ${price}<br/>
<b>Open:</b> ${open_}<br/>
<b>High:</b> ${high}<br/>
<b>Low:</b> ${low}<br/>
<b>Previous Close:</b> ${previous_close}<br/>
<b>Volume:</b> {volume}<br/>
<b>Trend:</b> {trend}
</p>

<h2>News Headlines</h2>
<ul>
{''.join(f"<li>{item.get('headline', 'No headline')} - <i>{item.get('time', 'Unknown time')}</i> | {item.get('category', 'General')}</li>" for item in news_list[:5]) or "<li>No major headlines available.</li>"}
</ul>

<h2>Key Financial Metrics</h2>
<ul>
  <li>Valuation ratios (P/E, P/B, P/S)</li>
  <li>Profit margins and ROE</li>
  <li>Liquidity and debt levels</li>
</ul>

<h2>Risks</h2>
<p>Highlight financial, regulatory, or macroeconomic risks.</p>
"""
            else:
                prompt = f"""
You are TradeGPT, a senior technical analyst and trader. Respond in clean HTML using headings, paragraphs, and bullet points. Provide a structured breakdown of market data for {name} ({symbol}).

<h2>Stock Snapshot</h2>
<p>
<b>Symbol:</b> {symbol}<br/>
<b>Company:</b> {name}<br/>
<b>Price:</b> ${price}<br/>
<b>Open:</b> ${open_}<br/>
<b>High:</b> ${high}<br/>
<b>Low:</b> ${low}<br/>
<b>Previous Close:</b> ${previous_close}<br/>
<b>Volume:</b> {volume}<br/>
<b>Trend:</b> {trend}
</p>

<h2>News Headlines</h2>
<p>{news_lines.replace("-", "<br/>-")}</p>

<h2>Trade Ideas</h2>
<ul>
  <li><b>Entry:</b> Identify support/resistance</li>
  <li><b>Stop-Loss:</b> Below key levels</li>
  <li><b>Target:</b> Based on momentum or technical projections</li>
</ul>
"""

            # Call DeepSeek
            client = OpenAI(
                api_key="sk-fd092005f2f446d78dade7662a13c896",
                base_url="https://api.deepseek.com"
            )

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are TradeGPT, a professional market analyst."},
                    {"role": "user", "content": prompt}
                ],
                stream=True,
                max_tokens=MAX_TOKENS
            )

            def stream():
                for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield f"data: {clean_special_chars(content)}\n\n"

            return StreamingHttpResponse(stream(), content_type="text/event-stream")

        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            return Response({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class DirectChatAIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            message = request.data.get("message", "").strip()
            if not message:
                return Response({"error": "Message is required."}, status=400)

            prompt = f"""
You are TradeGPT, a professional financial analyst and assistant. Respond using clean HTML with headings and bullet points.

<h2>Response to User</h2>
<p>{message}</p>

<h2>Analysis</h2>
<ul>
  <li>Break down the query in clear financial terms</li>
  <li>Use real-world examples if relevant</li>
  <li>Highlight any actionable ideas</li>
</ul>

<h2>Summary</h2>
<p>Offer a final conclusion or advice based on the above content.</p>
"""

            client = OpenAI(
                api_key="sk-fd092005f2f446d78dade7662a13c896",
                base_url="https://api.deepseek.com"
            )

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are TradeGPT, a helpful financial assistant."},
                    {"role": "user", "content": prompt}
                ],
                stream=True,
                max_tokens=1200
            )

            def stream():
                for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield f"data: {clean_special_chars(content)}\n\n"

            return StreamingHttpResponse(stream(), content_type="text/event-stream")

        except Exception as e:
            logger.error(f"Direct chat error: {str(e)}")
            return Response({"error": str(e)}, status=500)
