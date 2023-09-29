import abc
import json
import re
from collections import Counter

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from typing import Type

from parsers.constants import NOT_DL, OVERSIZE
from mainapp.models import Message, MessageTypeChoices, Poll, Location, MediaFile


def wrap_custom_emoji(item: dict):
    """Returns a custom emoji as a string, based on an item provided"""

    return item['text']


def wrap_plain(item: dict):
    """Returns plain text as a string, based on an item provided"""

    return item['text']


def wrap_mention_name(item: dict):
    """Returns a mentioned name as an html string, based on an item provided"""

    return f'<a href="https://t.me/{item.get("user_id")}">{item.get("text")}</a>'


def wrap_mention(item: dict):
    """Returns a mentioned name as an html string, based on an item provided"""

    return f'<a href="https://t.me/{item.get("text").replace("@", "")}">{item.get("text")}</a>'


def wrap_spoiler(item: dict):
    """Returns a spoiler as an html string, based on an item provided"""

    return f'<details><summary></summary>{item.get("text")}</details>'


def wrap_link(item: dict):
    """Returns an anchor tag as a string, based on an item provided"""

    link = ''
    if 'href' in item:
        link = item['href']
        text = item['text']
    elif item['type'] == 'link':
        link = text = item['text']
    else:
        text = item['text']
    return f'<a href="{link}">{text}</a>'


def wrap_tag(item: dict):
    """Returns an HTML tag as a string, based on an item provided"""

    tag = JsonParser1.tags[item['type']]
    return f'<{tag}>{item["text"]}</{tag}>'


def select_loader(directory: Path) -> 'Type[Loader]':
    """Select a required loader for provided log directory"""

    if (directory / "messages.html").exists():
        return HTMLLoader
    elif (directory / "result.json").exists():
        return JSONLoader


class Loader:

    def get_iter(self):
        pass

    def get_messages(self):
        pass


class HTMLLoader(Loader):
    """Loader for the OLD (2019-ish) telegram chat html export format"""

    media_tags = {
        "animated_wrap": MessageTypeChoices.GIF,
        "photo_wrap": MessageTypeChoices.PHOTO,
        "sticker_wrap": MessageTypeChoices.STICKER,
        "media_photo": MessageTypeChoices.IMAGE_FILE,
        "media_file": MessageTypeChoices.OTHER_FILE,
        "video_file_wrap": MessageTypeChoices.VIDEO,
        "media_video": MessageTypeChoices.VIDEO,
        "media_audio_file": MessageTypeChoices.AUDIO_FILE,
        "media_location": MessageTypeChoices.LOCATION,
        "media_venue": MessageTypeChoices.LOCATION,
        "media_voice_message": MessageTypeChoices.VOICE_MESSAGE,
        "media_poll": MessageTypeChoices.POLL,
    }

    def __init__(self, directory, start_page=None, start_message=None):
        files = self.get_file_list(Path(directory), start_page=start_page)
        self.messages = []
        # if a message doesn't have a username attached, use last found
        self.current_name: str = ""
        self.last_forwarded: str = ""
        self.names = Counter()
        for file in files:
            self.messages.extend(self.get_messages_from_file(file))
        print(self.names)
        print("DONE")

    def get_messages_from_file(self, html_doc):
        with open(html_doc, "r") as doc:
            soup = BeautifulSoup(doc, 'html.parser')
        message_divs = soup.find_all("div", class_="message")
        messages = []
        for div in message_divs:
            message = self.form_message(div)
            if message:
                messages.append(message)

        print(f"{messages[0].get('tg_id')}, {messages[0].get('date')}"
              f" -> {messages[-1].get('tg_id')}, {messages[-1].get('date')}", html_doc)

        return messages

    def form_message(self, div):
        location = poll = via_bot = forwarded_time = None
        if "service" in div["class"]:
            # todo implement service message processing
            return None
        if "joined" not in div["class"]:
            self.current_name = self.get_name(div)
            self.last_forwarded = ""
        if self.current_name.find(' via @') >= 0:
            name, via_bot = self.current_name.split(' via @')
            self.current_name = name
        else:
            name = self.current_name
        name = name.strip()
        self.names[name] += 1
        id_ = self.get_id(div)
        time = self.get_time(div)
        if forwarded := self.get_forwarded(div):
            div = forwarded
            forwarded_time = self.get_fwd_details(div)
            try:
                self.last_forwarded = self.get_name(div).replace(forwarded_time, "").strip()
            except AttributeError:
                pass
        time = self.get_time(div) if not time else time
        if not (text := self.get_text(div)):
            text = self.get_description(div)

        reply_to = self.get_reply_to(div)
        media_data = self.get_media(div)
        if "poll" in media_data:
            poll = media_data.pop("poll")
        elif "location" in media_data:
            location = media_data.pop("location")

        message = dict(
            tg_id=id_,
            from_name=name,
            via_bot=via_bot,
            date=time,
            content=text,
            forwarded_from=self.last_forwarded,
            fwd_time=forwarded_time,
            reply_to_message_id=reply_to,
            poll=poll,
            location=location,
            **media_data,
        )

        return message

    def get_media(self, div) -> dict:
        media_type = media_string = poll = None
        media_data = dict()
        if media := div.find(class_="media_wrap"):
            # locations, polls and the media which was omitted while downloading
            # were all wrapped into "media" divs in this legacy format
            # therefore sometimes you do not have a link
            media_class = media.a["class"] if media.a else media.div["class"]
            # select the tag relevant to media_type, we can use set intersection,
            # as there can be no more than one
            if media_tag_set := set(media_class) & set(self.media_tags.keys()):
                tag = media_tag_set.pop()
                media_type = self.media_tags[tag]
            if media_type:
                if anchor := media.a:
                    media_string = anchor["href"]
                    if media_type == MessageTypeChoices.LOCATION:
                        lat, lon = re.search(r"q=([\d.-]+),([\d.-]+)", media_string).groups()
                        media_data["location"] = dict(
                            latitude=lat,
                            longitude=lon,
                        )
                elif desc := media.div.find(class_="description"):
                    # todo add non-downloaded flag implementation
                    media_string = desc.text.strip()
                elif media_type == MessageTypeChoices.POLL:
                    poll = self.get_poll(div)
                    media_data["poll"] = poll
            else:
                print("NOT FOUND")

        media_data["msg_type"] = media_type
        media_data["media_string"] = media_string

        return media_data

    def get_poll(self, div):
        poll_data = dict()
        poll_data["question"] = div.find(class_="question").text.strip()
        poll_data["total_voters"] = int(div.find(class_="total").text.split()[0])
        poll_data["answers"] = []
        answers = div.find_all(class_="answer")
        for answer in answers:
            if count_div := answer.find("span"):
                count = int(count_div.text.split()[0])
                variant_div = count_div.previous_sibling
                variant = variant_div.text.strip()[2:]
            else:
                count = 0
                variant = answer.text.strip()[2:]
            poll_data["answers"].append(
                dict(
                    text=variant,
                    voters=count,
                )
            )

        return poll_data

    @staticmethod
    def get_id(div):
        return int(div["id"].replace("message", ""))

    @staticmethod
    def get_forwarded(div):
        return div.find(class_="forwarded body")

    @staticmethod
    def get_reply_to(div):
        if reply_to := div.find(class_="reply_to"):
            return reply_to.a["href"].replace("#go_to_message", "")

    def get_text(self, div):
        text = self._get_text_from_attr(div, "div", "text")
        return text if text else ""

    def get_description(self, div):
        title = self._get_text_from_attr(div, "div", "title")
        desc = self._get_text_from_attr(div, "div", "description")
        title = title if title else ""
        desc = desc if desc else ""
        return f"{title}<br>{desc}".strip()

    @staticmethod
    def get_time(div):
        if date_attr := div.find(class_="date"):
            return date_attr["title"]

    def get_name(self, div) -> str:
        return self._get_text_from_attr(div, "div", "from_name")

    def get_fwd_details(self, div) -> str:
        return self._get_text_from_attr(div, "span", "details")

    @staticmethod
    def _get_text_from_attr(div, container, attr_name):
        if attr := div.find(container, class_=attr_name):
            return attr.text.strip()

    @staticmethod
    def get_file_list(directory: Path, start_page=None):
        files = list(directory.glob("messages*.html"))
        prefix = str(directory) + "\\messages"
        files.sort(key=lambda name: int(str(name).replace(prefix, "0").replace(".html", "")))
        if not start_page:
            start_page = 0
        return [file for file in files if int(str(file).replace(prefix, "0").replace(".html", "")) >= start_page]


class JSONLoader(Loader):

    def __init__(self, directory):
        with open((directory / "result.json"), "r") as f:
            data = json.load(f)
        self.messages = data.get("messages")

    def get_iter(self):
        for message in self.messages:
            yield message

    def get_messages(self):
        return self.messages


class AbstractParser(abc.ABC):
    timefmt = '%Y-%m-%dT%H:%M:%S %z'

    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.loader = select_loader(self.directory)
        self.messages = self.loader.load(directory)
        self.existing_message_ids = set(Message.objects.values_list("tg_id"))
        self.last_existing_id = max(self.existing_message_ids)


class JsonParser1(AbstractParser):
    tags = {
        'bold': 'b',
        'italic': 'i',
        'pre': 'pre',
        'code': 'pre',
        'strikethrough': 'del',
        'underline': 'u',
    }
    conv = {
        'mention': wrap_mention,
        'mention_name': wrap_mention_name,
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
        'plain': wrap_plain,
        'pre': wrap_tag,
        'code': wrap_tag,
        'strikethrough': wrap_tag,
        'underline': wrap_tag,
        'spoiler': wrap_spoiler,
        'custom_emoji': wrap_custom_emoji,
    }

    def __init__(self, entry):
        if not entry['from']:
            username = 'Deleted Account'
        else:
            username = entry['from']
        self.message = Message(
            tg_id=entry['id'],
            date=datetime.strptime(f"{entry['date']} +0300", JsonParser1.timefmt).astimezone(),
            from_name=username,
        )
        self.message.content = self.concat_text(entry['text_entities'])
        if 'forwarded_from' in entry:
            self.message.forwarded_from = entry['forwarded_from'] if entry['forwarded_from'] else 'Deleted Account'
            self.message.fwd_time = self.message.date
        if 'reply_to_message_id' in entry:
            self.message.reply_to_message_id = entry['reply_to_message_id']
        if 'via_bot' in entry:
            self.message.via_bot = entry['via_bot']
        if 'poll' in entry:
            self.message.msg_type = 6
            self.message.poll = self.concat_poll(entry['poll'])
        if 'location_information' in entry:
            self.message.msg_type = 7
            self.message.location = self.concat_location(entry['location_information'])
        if 'file' in entry or 'photo' in entry:
            if entry.get('file') == NOT_DL or entry.get('file') == OVERSIZE:
                self.message.media_string = entry.get('file')
            else:
                self.message.msg_type = self._get_media_type(entry)
                self.message.media = self.concat_media(entry)

    def _get_media_type(self, entry):
        if entry.get("media_type") == "animation" and entry.get("mime_type") == "video/mp4":
            return 1
        elif entry.get("media_type") == "sticker" and entry.get("file").endswith(".webp"):
            return 2
        elif entry.get('photo'):
            return 3
        elif entry.get('media_type') == "video_file":
            return 5
        elif entry.get("media_type") == "sticker" and entry.get("file").endswith(".tgs"):
            return 8
        elif entry.get("media_type") == "voice_message":
            return 9
        elif entry.get("media_type") == "video_message":
            return 10
        elif entry.get("media_type") == "audio_file":
            return 11
        else:
            return 100

    def concat_media(self, entry):
        return MediaFile.create(entry)

    def concat_text(self, text_data):
        content = ''
        if type(text_data) == list:
            for part in text_data:
                if type(part) == dict:
                    content += JsonParser1.conv[part['type']](part)
                else:
                    content += part
        elif type(text_data) == str:
            content = text_data

        return content

    def concat_location(self, info):
        loc = Location(**info)
        loc.save()
        return loc

    def concat_poll(self, poll_data):
        return Poll.create(poll_data)

    def get_message(self):
        return self.message
