from django.core.management.base import BaseCommand

from django.contrib.auth.models import User

from tg_log_viewer import settings


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        super_user = User.objects.create_superuser(
            settings.SUPERUSER_USERNAME,
            settings.SUPERUSER_EMAIL,
            settings.SUPERUSER_PASSWORD,
        )
        user = User.objects.create_user(
            settings.LOG_USER_USERNAME,
            settings.LOG_USER_EMAIL,
            settings.LOG_USER_PASSWORD,
        )


