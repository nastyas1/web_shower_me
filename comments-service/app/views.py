import json
import time
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.db import close_old_connections
from .models import Comment
from .jwt_utils import require_auth


@csrf_exempt
@require_http_methods(["GET"])
def comments_page(request):
    """GET /comments/ — страница комментариев."""
    return render(request, 'app/comments.html')


@csrf_exempt
@require_http_methods(["GET"])
def list_comments(request):
    """GET /comments/api/ — последние 100 комментариев."""
    comments = Comment.objects.order_by("-created_at")[:100]
    return JsonResponse({"comments": [c.to_dict() for c in comments]})


@csrf_exempt
@require_auth
@require_http_methods(["POST"])
def create_comment(request):
    """POST /comments/ — создать комментарий. Тело: {text}."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Некорректный JSON"}, status=400)

    text = (data.get("text") or "").strip()
    if not text:
        return JsonResponse({"error": "Текст не может быть пустым"}, status=400)
    if len(text) > 1000:
        return JsonResponse({"error": "Максимум 1000 символов"}, status=400)

    payload = request.user_payload
    comment = Comment.objects.create(
        user_id=payload["user_id"],
        author=payload.get("first_name") or payload["username"],
        text=text,
    )
    return JsonResponse({"comment": comment.to_dict()}, status=201)


@csrf_exempt
@require_http_methods(["GET"])
def stream(request):
    """GET /comments/stream/ — SSE поток новых комментариев."""
    try:
        last_id = int(request.GET.get("last_id", 0))
    except (TypeError, ValueError):
        last_id = 0

    def event_stream(start_id):
        current_id = start_id
        if current_id == 0:
            for c in Comment.objects.order_by("id")[:100]:
                yield f"data: {json.dumps(c.to_dict())}\n\n"
                current_id = max(current_id, c.id)
            close_old_connections()

        deadline = time.time() + 300
        while time.time() < deadline:
            new_qs = Comment.objects.filter(id__gt=current_id).order_by("id")
            close_old_connections()
            for c in new_qs:
                yield f"data: {json.dumps(c.to_dict())}\n\n"
                current_id = c.id
            yield ": ping\n\n"
            time.sleep(1.5)

    response = StreamingHttpResponse(event_stream(last_id), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
