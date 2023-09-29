import re

from django.contrib.postgres.search import SearchQuery
from django.core.paginator import PageNotAnInteger, EmptyPage
from django.shortcuts import render, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from tg_log_viewer.settings import LOG_MESSAGES_PER_PAGE

from .models import Message
from .paginator import UserPaginator


# todo should be either prepared in the DB or converted by js on user's side
def message_prepare(message):
    message.content = re.sub(r'\[.*?\]\(https://t\.me/anime_lepra/(\d+)\)', r'<a href="/goto/\1">message#\1</a>', message.content)
    message.content = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">🌐\1</a>', message.content)
    message.content = re.sub(r'\n', r'<br>', message.content)


def main(request):
    title = 'something something'

    content = {
        'title': title,
    }

    return render(request, 'mainapp/index.html', context=content)


@login_required
def log(request, page=1):
    title = 'log viewer'

    log_messages = Message.objects.order_by('tg_id')
    # user_list = Message.objects.values('username').distinct().order_by('username').all()
    user_list = []

    paginator = UserPaginator(log_messages, LOG_MESSAGES_PER_PAGE)
    try:
        msg_paginator = paginator.page(page)
    except PageNotAnInteger:
        msg_paginator = paginator.page(1)
    except EmptyPage:
        msg_paginator = paginator.page(paginator.num_pages)

    # pprint(msg_paginator)
    # for message in msg_paginator:
    #     message_prepare(message)

    content = {
        'title': title,
        'object_list': msg_paginator,
        'user_list': user_list,
    }
    return render(request, 'mainapp/log.html', context=content)


class SearchResultsView(ListView):
    model = Message
    paginate_by = 500
    template_name = 'mainapp/search.html'

    def get_context_data(self, **kwargs):
        context = super(SearchResultsView, self).get_context_data(**kwargs)
        context['title'] = f"Search: '{self.request.GET.get('query')}'"
        if self.request.GET.get('user'):
            context['title'] += f' ({self.request.GET.get("user")})'
        context['user_list'] = Message.distinct_users
        context['current_user'] = self.request.GET.get('user')
        return context

    def get_queryset(self):
        key = self.request.GET.get('query')
        user = self.request.GET.get('user')
        qs = Message.objects.order_by('tg_id')
        if key != '':
            qs = qs.filter(vector__vector=SearchQuery(key, config='russian'))
        if user != '':
            qs = qs.filter(from_name__iexact=user)
        messages = qs.all()
        return messages

    @method_decorator(login_required())
    def dispatch(self, *args, **kwargs):
        return super(ListView, self).dispatch(*args, **kwargs)

#
# @login_required
# def expand(request, pk=2):
#     title = f'message {pk} in log'
#     BEFORE = 50
#     AFTER = 150
#
#     nearby_messages = Message.objects.filter(id__gte=pk-BEFORE, id__lt=pk+AFTER).order_by('pk')
#     for message in nearby_messages:
#         message_prepare(message)
#
#     content = {
#         'title': title,
#         'object_list': nearby_messages,
#         'highlight': pk,
#     }
#
#     return render(request, 'mainapp/peek.html', context=content)


@login_required
def peek(request, pk):
    title = f'message {pk} in log'
    RANGE = 3

    nearby_messages = Message.objects.filter(tg_id__gte=pk-RANGE, tg_id__lt=pk+RANGE+1).order_by('pk')
    for message in nearby_messages:
        message_prepare(message)

    content = {
        'title': title,
        'object_list': nearby_messages,
        'highlight': pk,
    }

    # print(nearby_messages)

    return render(request, 'mainapp/peek.html', context=content)


@login_required
def goto(request, pk=2):
    title = f'redirecting to message "{pk}" in log...'

    message_to_go = Message.objects.filter(tg_id__gte=pk).order_by('tg_id').first()

    return HttpResponseRedirect(f'/log/page/{message_to_go.message_page_num}#{message_to_go.tg_id}')
