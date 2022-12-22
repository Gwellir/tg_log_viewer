from django.db import models
from tg_log_viewer.settings import LOG_MESSAGES_PER_PAGE


class Message(models.Model):
    tg_id = models.PositiveIntegerField(verbose_name="Telegram log id", unique=True)
    time_stamp = models.DateTimeField(verbose_name='Message sending time')
    username = models.CharField(verbose_name='TG user first name', max_length=100)
    content = models.TextField(verbose_name='Message content', blank=True)
    media = models.CharField(verbose_name='path to mediafile bound to this message', max_length=100, blank=True)
    msg_type = models.PositiveIntegerField(verbose_name='message type (related to media type it was carrying', default=0)
    reply_to = models.PositiveIntegerField(verbose_name='number of message which this one replies to', default=0)
    fwd = models.BooleanField(verbose_name='is a forwarded message or not', default=False)
    fwd_from = models.CharField(verbose_name='forwarding source', max_length=255, blank=True)
    fwd_time = models.DateTimeField(verbose_name='fwd source sending time', null=True)
    inline = models.CharField(verbose_name='inline message sender name', blank=True, max_length=255)

    @property
    def message_page_num(self):
        return (self.pk - 1) // LOG_MESSAGES_PER_PAGE + 1

    def __str__(self):
        return f'#{self.tg_id} -> {self.username} sent this at {self.time_stamp}\n' \
               f'{self.content[:50]}\n' \
               f'contains: {self.msg_type} - {self.media}\n' \
               f'is_reply: {self.reply_to}\n' \
               f'is_fwd: {self.fwd} {self.fwd_from} {self.fwd_time}\n' \
               f'is_inline: {self.inline}\n'
