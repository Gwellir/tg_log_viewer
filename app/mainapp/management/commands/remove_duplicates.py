from django.core.management import BaseCommand

from mainapp.models import MediaFile
from tg_log_viewer.settings import MEDIA_ROOT
from utils.file_hash import hashify_rename


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        animations = MediaFile.objects.filter(media_type="animation")
        for animation in animations:
            print(animation, animation.message.get())
            file = MEDIA_ROOT / animation.file_path
            file_data = hashify_rename(file)

            animation.file_path = file_data.get_media_path()
            animation.hash = file_data.hash
            animation.size = file_data.size
            animation.save()

