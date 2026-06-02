import json
import random
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

    if settings.VK_GROUP_TOKEN and settings.VK_ADMIN_ID:
        vk_message = (
            f"Обратная связь:\n"
            f"   Имя: {name}. Email: {email}\n"
            f"   Тема: {SUBJECT_LABELS[subject]}\n"
            f"   Дата и Время: {timezone.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"СООБЩЕНИЕ: {message}"
        )
        try:
            resp = http_requests.get(
                "https://api.vk.com/method/messages.send",
                params={
                    "user_id": settings.VK_ADMIN_ID,
                    "message": vk_message,
                    "random_id": random.randint(0, 2**31),
                    "access_token": settings.VK_GROUP_TOKEN,
                    "v": settings.VK_API_VERSION,
                },
                timeout=5,
            )
            resp.raise_for_status()
            response_data = resp.json()
            if "error" in response_data:
                print(f"VK API error: {response_data['error']}")
            else:
                print(f"VK message sent successfully: {response_data}")
        except Exception as e:
            print(f"Failed to send VK message: {e}")

    return JsonResponse({"success": True, "message": "Сообщение отправлено"})
