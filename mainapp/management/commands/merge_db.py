import json
import os
import re
import sys
import zlib
from shutil import copy
from datetime import datetime
from json import JSONDecodeError

from django.core.management.base import BaseCommand
from mainapp.models import Message
from django.contrib.auth.models import User

NOT_DL = '(File not included. Change data exporting settings to download.)'
OVERSIZE = '(File exceeds maximum size. Change data exporting settings to download.)'
DL_FOLDER = "e:\\backup\\ChatExport_2021-11-23\\"
MAIN_FOLDER = "c:\\Users\\gwell\\Documents\\_coding_\\django\\tg_log_viewer\\static\\media\\"


def crc32(filename):
    with open(filename, 'rb') as fh:
        hash = 0
        while True:
            s = fh.read(65536)
            if not s:
                break
            hash = zlib.crc32(s, hash)
        return "%08X" % (hash & 0xFFFFFFFF)


def wrap_link(item: dict):
    link = ''
    text = ''
    if 'href' in item:
        link = item['href']
        text = item['text']
    elif item['type'] == 'link':
        link = item['text']
    else:
        text = item['text']
    return f'[{text}]({link})'


def wrap_tag(item: dict):
    tag = Parser.tags[item['type']]
    return f'<{tag}>{item["text"]}</{tag}>'


class Parser:
    timefmt = '%Y-%m-%dT%H:%M:%S %z'
    tags = {
        'bold': 'b',
        'italic': 'i',
        'pre': 'pre',
        'code': 'pre',
        'strikethrough': 'del',
        'underline': 'u',
    }
    conv = {
        'mention': wrap_link,
        'mention_name': wrap_link,
        'link': wrap_link,
        'text_link': wrap_link,
        'hashtag': wrap_link,
        'bot_command': wrap_link,
        'phone': wrap_link,
        'email': wrap_link,
        'bank_card': wrap_link,
        'cashtag': wrap_link,
        'bold': wrap_tag,
        'italic': wrap_tag,
        'pre': wrap_tag,
        'code': wrap_tag,
        'strikethrough': wrap_tag,
        'underline': wrap_tag,
    }

    def __init__(self, entry):
        if not entry['from']:
            username = 'Deleted Account'
        else:
            username = entry['from']
        self.message = Message(tg_id=entry['id'],
                               time_stamp=datetime.strptime(f"{entry['date']} +0300", Parser.timefmt).astimezone(),
                               username=username,
                               )
        self.message.content = self.concat_text(entry['text'])
        if 'forwarded_from' in entry:
            self.message.fwd = True
            self.message.fwd_from = entry['forwarded_from'] if entry['forwarded_from'] else 'Deleted Account'
            self.message.fwd_time = self.message.time_stamp
        if 'reply_to_message_id' in entry:
            self.message.reply_to = entry['reply_to_message_id']
        if 'via_bot' in entry:
            self.message.inline = entry['via_bot']
        if 'photo' in entry:
            self.message.msg_type = 3
            self.message.media = entry['photo']
            copy(os.path.join(DL_FOLDER, self.message.media),
                 os.path.join(MAIN_FOLDER, self.message.media))
        elif 'media_type' in entry and entry['media_type'] == 'animation':
            self.message.msg_type = 1
        elif 'media_type' in entry and entry['media_type'] == 'video_file':
            self.message.msg_type = 5
        elif 'sticker_emoji' in entry:
            if entry['file'].endswith('.webp'):
                self.message.msg_type = 2
            elif entry['file'].endswith('.tgs'):
                self.message.msg_type = 8
        elif 'file' in entry:
            if 'media_type' in entry and entry['media_type'] == 'sticker':
                self.message.msg_type = 3
            elif 'mime_type' in entry and entry['mime_type'].startswith('image/'):
                self.message.msg_type = 4
            else:
                self.message.msg_type = 9
        elif 'poll' in entry:
            self.message.msg_type = 6
            self.message.content = self.concat_poll(entry['poll'])
        elif 'location_information' in entry:
            self.message.msg_type = 7
            self.message.content = self.concat_location(entry['location_information'])
        if 'file' in entry and entry['file'] != NOT_DL and entry['file'] != OVERSIZE:
            self.message.media = self.hashify(entry['file'])

    def hashify(self, filename):
        hsh = crc32(os.path.join(DL_FOLDER, filename))
        folder, name = os.path.split(filename)
        new_file = os.path.join(folder, hsh + os.path.splitext(name)[1])
        print(new_file)
        copy(os.path.join(DL_FOLDER, filename), os.path.join(MAIN_FOLDER, new_file))

        return new_file.replace('\\', '/')

    def concat_text(self, text):
        content = ''
        if type(text) == list:
            for part in text:
                if type(part) == dict:
                    content += Parser.conv[part['type']](part)
                else:
                    content += part
        elif type(text) == str:
            content = text

        return content

    def concat_location(self, info):
        return f'LAT: {info["latitude"]}\nLONG: {info["longitude"]}'

    def concat_poll(self, poll):
        msg = f'{poll["question"]}\n\nTotal: {poll["total_voters"]}'
        for ans in poll['answers']:
            msg += f'\n{ans["text"]}: {ans["voters"]}'
        return msg

    @property
    def get_message(self):
        return self.message


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        json_file = os.path.join(DL_FOLDER, "result.json")
        try:
            with open(json_file, 'r', encoding='utf-8') as new_data:
                data = json.load(new_data)
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
                        msg = Parser(entries[i]).get_message
                        msg.save()
                        if 'file' in entries[i]:
                            print(msg)
                            # exit(1)
                    except KeyError as err:
                        print(f'Failure at #{entries[i]["id"]}')
                        print(err)
                        exit(1)
                i += 1
