import json

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from .models import Task


def register(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("board")
    return render(request, "registration/register.html", {"form": form})


@login_required
def board(request):
    return render(request, "tasks/board.html")


def serialize(t):
    return {
        "id": t.id,
        "title": t.title,
        "status": t.status,
        "priority": t.priority,
        "due_date": t.due_date.isoformat() if t.due_date else None,
    }


def read_json(request):
    try:
        return json.loads(request.body or "{}")
    except ValueError:
        return None


def apply_fields(task, data):
    """Validate and apply editable fields. Returns an error string or None."""
    if "title" in data:
        title = str(data["title"]).strip()
        if not title or len(title) > 140:
            return "Title must be 1-140 characters."
        task.title = title
    if "priority" in data:
        if data["priority"] not in Task.Priority.values:
            return "Invalid priority."
        task.priority = data["priority"]
    if "due_date" in data:
        task.due_date = parse_date(data["due_date"]) if data["due_date"] else None
    return None

@login_required
@require_http_methods(["GET", "POST"])
def task_list(request):
    if request.method == "GET":
        return JsonResponse({"tasks": [serialize(t) for t in request.user.tasks.all()]})
    data = read_json(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    task = Task(owner=request.user)
    error = apply_fields(task, data)
    if error or not task.title:
        return JsonResponse({"error": error or "Title is required."}, status=400)
    task.save()
    return JsonResponse(serialize(task), status=201)