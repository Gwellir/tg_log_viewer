import orjson as json
import os
from json import JSONDecodeError

from django.core.management.base import BaseCommand
from mainapp.models import Message
from parsers.log_parsers import JsonParser1
from parsers.constants import DL_FOLDER


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        json_file = os.path.join(DL_FOLDER, "result.json")
        try:
            with open(json_file, 'r', encoding='utf-8') as new_data:
                data = json.loads(new_data.read())
                entries = data['messages']
        except (IOError, JSONDecodeError):
            exit(1)
        last_message = Message.objects.order_by('-tg_id').first()
        last_id = last_message.tg_id
        if last_id:
            i = 0
            while entries[i]['id'] <= last_id:
                i += 1
            while i < len(entries):
                # todo add join messages support
                if entries[i]['type'] == 'message':
                    try:
                        msg = JsonParser1(entries[i]).get_message()
                        msg.save()
                        if 'file' in entries[i]:
                            print(msg)
                            # exit(1)
                    except KeyError as err:
                        print(f'Failure at #{entries[i]["id"]}')
                        print(err)
                        exit(1)
                i += 1
