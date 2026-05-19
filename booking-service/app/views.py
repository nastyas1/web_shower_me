import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, get_object_or_404
from .models import Booking
from .jwt_utils import require_auth, get_jwt_payload

SLOT_TIMES = [
    f"{h:02d}:{m:02d}" for h in range(8, 22) for m in (0, 30)
]


@csrf_exempt
@require_http_methods(["GET"])
def booking_page(request):
    """GET /booking/ — страница бронирования."""
    return render(request, 'app/booking.html')


@csrf_exempt
@require_http_methods(["GET"])
def slots(request):
    """GET /booking/slots/?date=YYYY-MM-DD — список слотов с их статусами."""
    date = request.GET.get("date", "").strip()
    if not date:
        return JsonResponse({"error": "Укажите дату"}, status=400)

    booked_qs = Booking.objects.filter(date=date).values_list("time", "user_id")
    # Преобразуем время в строку формата HH:MM для сравнения
    booked_map = {t.strftime("%H:%M"): uid for t, uid in booked_qs}

    payload = get_jwt_payload(request)
    current_user_id = payload["user_id"] if payload else None

    result = []
    for t in SLOT_TIMES:
        uid = booked_map.get(t)
        result.append({
            "time": t,
            "status": "mine" if uid == current_user_id else ("taken" if uid else "free"),
        })

    return JsonResponse({"date": date, "slots": result})


@csrf_exempt
@require_auth
@require_http_methods(["POST"])
def create_booking(request):
    """POST /booking/create/ — создать бронь. Тело: {date, time}."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Некорректный JSON"}, status=400)

    date = (data.get("date") or "").strip()
    time_val = (data.get("time") or "").strip()
    if not date or not time_val:
        return JsonResponse({"error": "Укажите дату и время"}, status=400)

    # Преобразуем строку времени в объект time для Django
    from datetime import datetime
    try:
        time_obj = datetime.strptime(time_val, "%H:%M").time()
    except ValueError:
        return JsonResponse({"error": "Неверный формат времени"}, status=400)

    if Booking.objects.filter(date=date, time=time_obj).exists():
        return JsonResponse({"error": "Этот слот уже занят"}, status=409)

    payload = request.user_payload
    booking = Booking.objects.create(
        user_id=payload["user_id"],
        username=payload.get("first_name") or payload["username"],
        date=date,
        time=time_obj,
    )
    return JsonResponse({"booking": booking.to_dict()}, status=201)


@csrf_exempt
@require_auth
@require_http_methods(["GET"])
def my_bookings(request):
    """GET /booking/my/ — брони текущего пользователя."""
    user_id = request.user_payload["user_id"]
    bookings = Booking.objects.filter(user_id=user_id)
    return JsonResponse({"bookings": [b.to_dict() for b in bookings]})


@csrf_exempt
@require_auth
@require_http_methods(["POST"])
def cancel_booking(request, booking_id):
    """POST /booking/cancel/<id>/ — отменить бронь."""
    user_id = request.user_payload["user_id"]
    booking = get_object_or_404(Booking, id=booking_id, user_id=user_id)
    booking.delete()
    return JsonResponse({"success": True})
