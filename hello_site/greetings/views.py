from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def hello(request: HttpRequest) -> HttpResponse:
    """단순한 환영 메시지를 렌더링합니다."""
    context = {
        "title": "Hello 페이지",
        "message": "안녕하세요, Django!",
    }
    return render(request, "greetings/hello.html", context)
