import json
import requests as http_requests
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.utils import timezone
from .models import FeedbackMessage

SUBJECT_LABELS = {
    "booking":    "Бронирование",
    "technical":  "Техническая проблема",
    "suggestion": "Предложение",
    "other":      "Другое",
}


@csrf_exempt
@require_http_methods(["GET"])
def feedback_page(request):
    """GET /feedback/ — страница обратной связи."""
    return render(request, 'app/feedback.html')


@csrf_exempt
@require_http_methods(["POST"])
def submit_feedback(request):
    """POST /feedback/ — отправка обратной связи. Авторизация не требуется."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Некорректный JSON"}, status=400)

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    if not all([name, email, subject, message]):
        return JsonResponse({"error": "Заполните все поля"}, status=400)
    if subject not in SUBJECT_LABELS:
        return JsonResponse({"error": "Неверная тема"}, status=400)

    FeedbackMessage.objects.create(name=name, email=email, subject=subject, message=message)

    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        text = (
            f"💬 <b>Обратная связь</b>\n"
            f"👤 {name}\n📧 {email}\n"
            f"📌 {SUBJECT_LABELS[subject]}\n"
            f"💭 {message}\n"
            f"🕐 {timezone.now().strftime('%d.%m.%Y %H:%M')}"
        )
        try:
            resp = http_requests.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
                timeout=5,
            )
            resp.raise_for_status()
            print(f"Telegram message sent successfully: {resp.json()}")
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")

    return JsonResponse({"success": True, "message": "Сообщение отправлено"})
