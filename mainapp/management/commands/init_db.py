from django.core.management.base import BaseCommand
from mainapp.models import Message
from django.contrib.auth.models import User

import json, os, re


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        super_user = User.objects.create_superuser('Valion', 'gwellir@gmail.com', 'NOFate86')
        user = User.objects.create_user('log', 'log@localhost', 'logview20')


