import re
import urllib.parse

from django.core.management.base import BaseCommand
from mainapp.models import Message


def get_bulk(size, offset=0):
    max_pk = Message.objects.order_by('-tg_id').first().tg_id
    print(max_pk)
    lower = offset + 1
    upper = offset + size
    while lower < max_pk:
        result = Message.objects.filter(tg_id__gte=lower, tg_id__lte=upper).all()
        print(lower, upper)
        lower += size
        upper += size
        yield result


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # messages = Message.objects.order_by('pk').all()
        # ltag_count = rtag_count = link_count = 0
        for messages in get_bulk(1000, offset=2495976):
            # with transaction.atomic():
            updated = []
            for message in messages:
                if message.content.find('></a>') >= 0:
                    message.content = message.content.replace('></a>', '>🌐</a>')
                # if (message.content.find('a href="https://t.me/') >= 0) and not (message.content.find('">@') >= 0):
                #     message.content = re.sub(r'<a href="https://t\.me/([\w\W\d_]+)>(.*)</a>',
                #                              r'<a href="https://t.me/\1)">\2</a>', message.content)
                    updated.append(message)
                # if message.content.find('[') >= 0:
                #     message.content = re.sub(r'\[.*?\]\(https://t\.me/anime_lepra/(\d+)\)',
                #                              r'<a href="/goto/\1">message#\1</a>', message.content)
                #     for match in re.finditer(r'(\[(.*?)\]\((.*?)\))', message.content):
                #         res = match.groups()
                #         message.content = message.content.replace(
                #             res[0],
                #             f'<a href="{res[2]}">🌐'
                #             f'{res[1] if res[1] else urllib.parse.urlparse(res[2]).hostname}'
                #             f'</a>')
                #     updated.append(message)
                if message.content.find('\n') >= 0:
                    message.content = re.sub(r'\n', r'<br>', message.content)
                    updated.append(message)
                # if re.match(r'.*\[\]\((.*?)\).*', message.content):
                #     message.content = re.sub(r'\[\]\((.*?)\)', r'[\1](\1)', message.content)
                #     print('W', end='')
                # if re.match(r'.*<(?!(/|)(strong|em|i|s|code|pre|br(|/))>).*', message.content):
                #     print(re.sub(r'<(?!(/|)(strong|em|i|s|code|pre|br(|/))>)', r'&lt;', message.content))
                #     ltag_count += 1
                    # print('T', end='')
                # if re.match(r'.*(?<!<(/|)(strong|em|i|s|code|pre|br(|/))>).*', message.content):
                #     print(re.sub(r'<(?!(/|)(strong|em|i|s|code|pre|br(|/))>)', r'&lt;', message.content))
                #     ltag_count += 1
                    # print('T', end='')
                    # message.save()
            Message.objects.bulk_update(updated, ['content'])
        # print(ltag_count)
