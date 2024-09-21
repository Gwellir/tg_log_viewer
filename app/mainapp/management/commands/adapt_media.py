from alive_progress import alive_bar
from django.core.management import BaseCommand

from mainapp.models import Message, MediaFile


def adapt_media(message, types=None):
    if message.msg_type in (6, 7):
        return False
    if types:
        if message.msg_type not in types:
            return False

    if message.media_string and not message.content.startswith("NOT LOADED: "):
        is_downloaded = True
    else:
        is_downloaded = False

    media_type = None
    if message.msg_type == 9:
        if message.media_string.startswith("voice_message"):
            media_type = "voice_message"
        elif message.media_string.endswith(".mp3"):
            media_type = "audio_file"
            message.msg_type = 11
        else:
            message.msg_type = 100
    elif message.msg_type == 1:
        media_type = "animation"
    elif message.msg_type in (2, 8):
        media_type = "sticker"
    elif message.msg_type == 3:
        media_type = "photo"
    elif message.msg_type == 4:
        media_type = "photo_file"
    elif message.msg_type == 5:
        media_type = "video_file"

    mfile = MediaFile.objects.create(
        is_downloaded=is_downloaded,
        media_type=media_type,
        file_path=message.media_string,
    )
    message.media = mfile

    return True


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # 1 is for animation type
        qs = Message.objects.filter(msg_type__in=[1])
        with alive_bar(qs.count()) as bar:
            for i, message in enumerate(qs):
                changed = False
                changed = changed or adapt_media(message, types=[1])
                if changed:
                    message.save()
                bar()
