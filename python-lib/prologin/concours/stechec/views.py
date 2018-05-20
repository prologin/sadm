from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Max, Min
from django.http import (HttpResponseRedirect, HttpResponse,
                         HttpResponseForbidden, Http404)
from django.shortcuts import get_object_or_404
from django.views.generic import (DetailView, ListView, FormView, TemplateView,
                                  RedirectView)
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin

import collections
import os
import socket
import urllib.parse

from prologin.concours.stechec import forms
from prologin.concours.stechec import models
# Use API throttling in the standard view
from prologin.concours.stechec.restapi.permissions import CreateMatchUserThrottle
# Imported for side-effect
import prologin.concours.stechec.monitoring


class ChampionView(DetailView):
    context_object_name = "champion"
    model = models.Champion
    template_name = "stechec/champion-detail.html"

    @property
    def can_see_log(self):
        ch = self.get_object()
        return self.request.user == ch.author or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super(ChampionView, self).get_context_data(**kwargs)
        context['can_see_log'] = self.can_see_log
        return context

    def get(self, request, *args, **kwargs):
        match = self.get_object()
        if (settings.STECHEC_FIGHT_ONLY_OWN_CHAMPIONS and not
            self.request.user.is_staff) and match.author != request.user:
            return HttpResponseForbidden()
        return super().get(request, *args, **kwargs)


class ChampionsListView(ListView):
    context_object_name = "champions"
    paginate_by = 50
    template_name = "stechec/champions-list.html"
    title = "Tous les champions"

    def get_context_data(self, **kwargs):
        context = super(ChampionsListView, self).get_context_data(**kwargs)
        context['title'] = self.title
        context['user'] = self.request.user
        context['show_for_all'] = self.show_for_all
        context['explanation_text'] = self.explanation_text
        return context


class AllChampionsView(ChampionsListView):
    queryset = models.Champion.objects.filter(deleted=False).select_related('author')
    explanation_text = 'Voici la liste de tous les champions participant actuellement.'
    show_for_all = True

    def get(self, request, *args, **kwargs):
        if (settings.STECHEC_FIGHT_ONLY_OWN_CHAMPIONS and not
            self.request.user.is_staff):
            return HttpResponseForbidden()
        return super().get(request, *args, **kwargs)


class MyChampionsView(ChampionsListView):
    explanation_text = 'Voici la liste de tous vos champions participant actuellement.'
    title = "Mes champions"
    show_for_all = False

    def get_queryset(self):
        user = self.request.user
        return models.Champion.objects.filter(deleted=False, author=user)


class MatchesListView(ListView): # Abstract class!
    context_object_name = "matches"
    paginate_by = 100
    template_name = "stechec/matches-list.html"
    title = "Tous les matches"

    def get_context_data(self, **kwargs):
        context = super(MatchesListView, self).get_context_data(**kwargs)
        context['title'] = self.title
        context['user'] = self.request.user
        context['explanation_text'] = self.explanation_text
        context['show_creator'] = self.show_creator
        matches = []
        map_cache = {}
        for m in context['matches']:
            if settings.STECHEC_USE_MAPS:
                map = m.map
                matches.append((m, map.id, map.name))
            else:
                matches.append((m, None, None))
        context['matches'] = matches
        return context


class MatchView(DetailView):
    context_object_name = "match"
    template_name = "stechec/match-detail.html"

    def get_queryset(self):
        queryset = models.Match.objects
        if (settings.STECHEC_FIGHT_ONLY_OWN_CHAMPIONS and not
            self.request.user.is_staff):
            queryset = queryset.filter(author=self.request.user.id)
        queryset = (queryset.annotate(Max('matchplayer__score'))
                            .annotate(Min('matchplayer__id')))
        return queryset


class AllMatchesView(MatchesListView):
    queryset = models.Match.objects.all().select_related('author')
    explanation_text = "Voici la liste de tous les matches ayant été réalisés."
    show_creator = True

    def get_queryset(self):
        qs = models.Match.objects.all()
        if (settings.STECHEC_FIGHT_ONLY_OWN_CHAMPIONS and not
            self.request.user.is_staff):
            qs = qs.filter(author=self.request.user.id)
        authors = self.request.GET.getlist('author')
        if authors:
            qs = qs.filter(author__pk__in=authors)
        champions = self.request.GET.getlist('champion')
        if champions:
            qs = qs.filter(players__pk__in=champions)
        champion_authors = self.request.GET.getlist('champion-author')
        if champion_authors:
            qs = qs.filter(players__author__pk__in=champion_authors)
        return qs

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MyMatchesView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return '{}?author={}'.format(reverse('matches-all'),
                                     self.request.user.pk)


class MyChampionMatchesView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return '{}?champion-author={}'.format(reverse('matches-all'),
                                              self.request.user.pk)


class AllMapsView(ListView):
    context_object_name = "maps"
    paginate_by = 100
    template_name = "stechec/maps-list.html"
    queryset = models.Map.objects.order_by('-official', '-id').select_related('author')


class MapView(DetailView):
    context_object_name = "map"
    template_name = "stechec/map-detail.html"
    model = models.Map


class NewChampionView(FormView):
    form_class = forms.ChampionUploadForm
    template_name = 'stechec/champion-new.html'

    def form_valid(self, form):
        champion = models.Champion(
            name=form.cleaned_data['name'],
            author=self.request.user,
            status='new',
            comment=form.cleaned_data['comment']
        )
        champion.save()
        # It's important to save() before sources =, as the latter needs the row id
        champion.sources = form.cleaned_data['tarball']

        return HttpResponseRedirect(champion.get_absolute_url())


class ConfirmDeleteChampion(DetailView):
    template_name = 'stechec/champion-delete.html'
    pk_url_kwarg = 'pk'
    model = models.Champion

    def get_object(self, queryset=None):
        return get_object_or_404(self.model,
                                 pk=self.kwargs[self.pk_url_kwarg],
                                 author=self.request.user)

    def post(self, request, *args, **kwargs):
        champion = self.get_object()
        champion.deleted = True
        champion.save()
        messages.success(request, "Champion {} supprimé.".format(champion.name))
        return HttpResponseRedirect(reverse('champions-mine'))


class ChampionSources(SingleObjectMixin, View):
    model = models.Champion
    pk_url_kwarg = 'pk'

    def get(self, request, *args, **kwargs):
        champion = self.get_object()
        if not (request.user.is_staff or request.user == champion.author):
            return HttpResponseForbidden()
        h = HttpResponse(champion.sources, content_type="application/stechec-dump")
        h['Content-Disposition'] = 'attachment; filename=champion-%s.tgz' % self.kwargs[self.pk_url_kwarg]
        h['Content-Encoding'] = 'application/x-gzip'
        return h


class NewMatchView(FormView):
    form_class = forms.MatchCreationForm
    template_name = 'stechec/match-new.html'

    def get_form_kwargs(self, **kwargs):
        kwargs = super().get_form_kwargs(**kwargs)
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        throttler = CreateMatchUserThrottle()
        if not throttler.allow_request(self.request, self):
            messages.error(self.request,
                           "Vos requêtes sont trop rapprochées dans le temps. "
                           "Merci de patienter environ {:.0f} secondes avant de "
                            "recommencer votre requête.".format(throttler.wait()))
            return HttpResponseRedirect(reverse('match-new'))

        with transaction.atomic():
            match = models.Match(
                author=self.request.user,
                status='creating',
                tournament=None,
                options=''
            )
            if settings.STECHEC_USE_MAPS:
                match.map = form.cleaned_data['map'].path
            match.save()

            for i in range(1, settings.STECHEC_NPLAYERS + 1):
                champ = form.cleaned_data['champion_%d' % i]
                player = models.MatchPlayer(
                    champion=champ,
                    match=match
                )
                player.save()

            match.status = 'new'
            match.save()

        messages.success(self.request, "Le match #{} a été initié.".format(match.id))
        return HttpResponseRedirect(match.get_absolute_url())


class MatchDumpView(SingleObjectMixin, View):
    model = models.Match
    pk_url_kwarg = 'pk'

    def get(self, request, *args, **kwargs):
        match = self.get_object()
        if (settings.STECHEC_FIGHT_ONLY_OWN_CHAMPIONS and not
            self.request.user.is_staff) and match.author != request.user:
            return HttpResponseForbidden()

        dump = match.dump
        if dump is None:
            raise Http404()

        h = HttpResponse(dump, content_type="application/stechec-dump")
        h['Content-Disposition'] = ('attachment; filename=dump-%s.json' %
                                    self.kwargs[self.pk_url_kwarg])
        h['Content-Encoding'] = 'gzip'
        return h


class NewMapView(FormView):
    form_class = forms.MapCreationForm
    template_name = 'stechec/map-new.html'

    def form_valid(self, form):
        map = models.Map(
            author=self.request.user,
            name=form.cleaned_data['name'],
            official=False
        )
        map.save()
        map.contents = form.cleaned_data['contents']
        return HttpResponseRedirect(map.get_absolute_url())


class MasterStatus(TemplateView):
    template_name = 'stechec/master-status.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            status = models.master_status()
            status = [(h, p, (100 * (m - s)) / m) for (h, p, s, m) in status]
            status.sort()
        except socket.error:
            status = None
        context['status'] = status
        return context


class RedmineIssueView(RedirectView):
    permanent = False

    tracker_id = None
    is_private = False
    subject = ""
    description = ""

    def get_redirect_url(self, *args, **kwargs):
        qs = {
            'issue[tracker_id]': str(self.tracker_id),
            'issue[is_private]': '1' if self.is_private else '0',
            'issue[subject]': self.subject,
            'issue[description]': self.description,
        }
        return '{}?{}'.format(settings.STECHEC_REDMINE_ISSUE_NEW,
                              urllib.parse.urlencode(qs))


class AskForHelp(RedmineIssueView):
    tracker_id = 3  # assistance
    is_private = True
    subject = "J'ai un problème : "


class ReportBug(RedmineIssueView):
    tracker_id = 1  # issue
    is_private = False
    subject = "[Remplacez ceci par un résumé court et explicite]"
    description = "\n\n".join([
        "*Où* est le problème (p. ex. adresse web, nom de la machine…) :",
        "*Comment* reproduire :",
        "Ce qui *devrait* se produire normalement :",
        "Ce qui *se produit* dans les faits :",
        ""
    ])


class RedmineIssueListView(RedirectView):
    permanent = False

    filters = []

    def get_redirect_url(self, *args, **kwargs):
        qs = collections.defaultdict(list)
        qs['set_filter'] = '1'
        for name, op, value in self.filters:
            qs['f[]'].append(str(name))
            qs['op[%s]' % name] = str(op)
            if value is not None:
                qs['v[%s][]' % name] = str(value)
        return '{}?{}'.format(settings.STECHEC_REDMINE_ISSUE_LIST,
                              urllib.parse.urlencode(qs, doseq=True))


class AskForHelpList(RedmineIssueListView):
    filters = [
        ('status_id', '*', None),
        ('tracker_id', '=', 3),
        ('author_id', '=', 'me'),
    ]


class ReportBugList(RedmineIssueListView):
    filters = [
        ('status_id', '*', None),
        ('tracker_id', '=', 1),
        ('author_id', '=', 'me'),
    ]
