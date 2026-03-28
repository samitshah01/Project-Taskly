from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django.conf import settings
from django.utils import timezone


class UserTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz_name = request.session.get("user_timezone", settings.TIME_ZONE)

        try:
            timezone.activate(ZoneInfo(tz_name))
        except ZoneInfoNotFoundError:
            timezone.activate(ZoneInfo("UTC"))

        response = self.get_response(request)
        timezone.deactivate()
        return response