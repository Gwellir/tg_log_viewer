import os
from shutil import copy

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField, SearchVector
from django.db import models
from django.db.models import Count
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from mainapp.paginator import UserPaginator
from parsers.constants import NOT_DL, OVERSIZE, DL_FOLDER, MAIN_FOLDER
from tg_log_viewer.settings import LOG_MESSAGES_PER_PAGE
from utils.file_hash import hashify_copy


class MessageTypeChoices(models.IntegerChoices):
    TEXT = 0, _("Text")
    GIF = 1, _("Animation")
    STICKER = 2, _("Sticker")
    PHOTO = 3, _("Photo")
    IMAGE_FILE = 4, _("Image file")
    VIDEO = 5, _("Video")
    POLL = 6, _("Poll")
    LOCATION = 7, _("Location")
    ANIMATED_STICKER = 8, _("Animated sticker")
    VOICE_MESSAGE = 9, _("Voice message")
    VIDEO_MESSAGE = 10, _("Video message")
    AUDIO_FILE = 11, _("Audio file")

    OTHER_FILE = 100, _("Other file")


class MediaFile(models.Model):
    is_downloaded = models.BooleanField(verbose_name="media downloaded flag")
    media_type = models.CharField(verbose_name='media_type as in TG log format', max_length=50, null=True, db_index=True)
    mime_type = models.CharField(verbose_name='mime_type as in TG log format', max_length=50, null=True)
    thumbnail = models.CharField(verbose_name='path to a thumbnail bound to this message', max_length=255, blank=True)
    width = models.IntegerField(verbose_name="width of a media file", null=True)
    height = models.IntegerField(verbose_name="height of a media file", null=True)
    duration_seconds = models.IntegerField(verbose_name="duration of a media file", null=True)
    file_path = models.CharField(verbose_name='path to mediafile bound to this message', max_length=255, blank=True)
    sticker_emoji = models.CharField(verbose_name='Emoji for a sticker', max_length=8, null=True)
    performer = models.CharField(verbose_name="Performer tag", max_length=200, null=True)
    title = models.CharField(verbose_name="composition title", max_length=200, null=True)
    hash = models.SlugField(verbose_name="CRC32 hash", max_length=8, null=True)
    size = models.IntegerField(verbose_name="file size", null=True)

    @classmethod
    def create(cls, msg_entry):
        hash_data = None
        if msg_entry.get('media_type') in ('sticker', 'animated_sticker', 'gif'):
            hash_data = hashify_copy(os.path.join(DL_FOLDER, msg_entry['file']))
            file_path = hash_data.get_media_path()
        else:
            file_path = msg_entry['file'] if 'file' in msg_entry else msg_entry['photo']
            copy(os.path.join(DL_FOLDER, file_path),
                 os.path.join(MAIN_FOLDER, file_path))

        media_type = msg_entry.get('media_type')
        if not media_type and msg_entry.get('photo'):
            media_type = 'photo'

        media_data = dict(
            is_downloaded=msg_entry.get('file') != NOT_DL and msg_entry.get('file') != OVERSIZE,
            media_type=media_type,
            mime_type=msg_entry.get('mime_type'),
            thumbnail=msg_entry.get('thumbnail') if msg_entry.get('thumbnail') else "",
            width=msg_entry.get('width'),
            height=msg_entry.get('height'),
            duration_seconds=msg_entry.get('duration_seconds'),
            file_path=file_path,
            sticker_emoji=msg_entry.get('sticker_emoji'),
            performer=msg_entry.get('performer'),
            title=msg_entry.get('title'),
            hash=hash_data.hash if hash_data else None,
            size=hash_data.size if hash_data else None,
        )
        media = cls.objects.create(**media_data)
        return media


class Poll(models.Model):
    question = models.TextField(verbose_name="Poll question")
    closed = models.BooleanField(verbose_name="is a poll closed", default=False)
    total_voters = models.IntegerField(verbose_name="total votes for this poll")

    @classmethod
    def create(cls, poll_data: dict) -> 'Poll':
        answers = poll_data.pop("answers")
        poll = cls.objects.create(**poll_data)

        for answer in answers:
            pa: PollAnswer
            pa = PollAnswer.objects.create(poll=poll, **answer)

        return poll


class PollAnswer(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="answers")
    chosen = models.BooleanField(verbose_name="log owner vote for the option", default=False)
    text = models.CharField(verbose_name="option description", max_length=255)
    voters = models.IntegerField(verbose_name="total votes for this option")


class Location(models.Model):
    latitude = models.CharField(verbose_name="Latitude for the location", max_length=20)
    longitude = models.CharField(verbose_name="Longitude for the location", max_length=20)
    place_name = models.CharField(verbose_name="Place name (if available)", max_length=200, null=True)
    address = models.CharField(verbose_name="Location address (if available)", max_length=200, null=True)


class Message(models.Model):

    paginator = UserPaginator

    tg_id = models.PositiveIntegerField(verbose_name="Telegram log id", unique=True)
    date = models.DateTimeField(verbose_name='Message sending time')
    edited = models.DateTimeField(verbose_name='Message edit time', null=True)
    from_name = models.CharField(verbose_name='TG user first name', max_length=100)
    from_id = models.BigIntegerField(verbose_name='TG user ID', null=True)
    content = models.TextField(verbose_name='Message content', blank=True)
    media = models.ForeignKey(MediaFile, on_delete=models.SET_NULL, null=True, related_name="message")
    media_string = models.CharField(blank=True, max_length=100, verbose_name='path to mediafile bound to this message')
    msg_type = models.PositiveIntegerField(verbose_name='message type (related to media type it was carrying', choices=MessageTypeChoices.choices, default=0)
    reply_to_message_id = models.PositiveIntegerField(verbose_name='number of message which this one replies to', default=0)
    forwarded_from = models.CharField(verbose_name='forwarding source', max_length=255, blank=True)
    fwd_time = models.DateTimeField(verbose_name='fwd source sending time', null=True)
    via_bot = models.CharField(verbose_name='inline message sender name', blank=True, max_length=255)
    poll = models.ForeignKey(Poll, verbose_name="A telegram poll results", on_delete=models.SET_NULL, null=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)

    @property
    def message_page_num(self):
        return (self.pk - 1) // LOG_MESSAGES_PER_PAGE + 1

    @cached_property
    def distinct_users(self):
        users_sorted = (
            Message.objects
            .values('from_name')
            .annotate(count=Count('from_name'))
            .order_by('-count')
            .all()
        )

        return [user['from_name'] for user in users_sorted]

    def __str__(self):
        return f'#{self.tg_id} -> {self.from_name} sent this at {self.date}\n' \
               f'{self.content[:50]}\n' \
               f'contains: {self.msg_type} - {self.media}\n' \
               f'is_reply: {self.reply_to_message_id}\n' \
               f'is_fwd: {self.forwarded_from} {self.fwd_time}\n' \
               f'is_inline: {self.via_bot}\n'

    class Meta:
        ordering = ['pk']


class MessageVector(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="vector")
    vector = SearchVectorField(verbose_name="message vectors", null=True)

    class Meta:
        indexes = [
            GinIndex(SearchVector("vector", config='russian'), name="idx_gin_document"),
        ]
