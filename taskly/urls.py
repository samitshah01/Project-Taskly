"""taskly URL Configuration

"""
from django.contrib import admin
from django.urls import path
from django.urls import path, include
from django.http import JsonResponse
from django.views.static import serve
from django.conf import settings

def devtools_dummy(request):
    return JsonResponse({}, status=204)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('project_taskly.urls')),
    path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    path('.well-known/appspecific/com.chrome.devtools.json', devtools_dummy),
]
