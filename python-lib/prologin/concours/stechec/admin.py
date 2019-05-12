from django import forms
from django.conf import settings
from django.contrib import admin
from django.db.models import Max
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from prologin.concours.stechec import models

admin.site.register(models.Champion)


class MatchPlayerInline(admin.TabularInline):
    model = models.Match.players.through
    extra = 1


@admin.register(models.Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'status', 'player_list', 'ts')
    list_filter = ('status', 'tournament')
    inlines = [MatchPlayerInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('players')

    @mark_safe
    def player_list(self, obj):
        return ' vs '.join(
            ['<a href="{}">{}</a>'.format(tp.champion.get_absolute_url(),
                                          tp.champion)
             for tp in obj.matchplayers.order_by('id')])


class TournamentMapInline(admin.TabularInline):
    model = models.Tournament.maps.through
    extra = 1


class TournamentPlayerInline(admin.TabularInline):
    model = models.Tournament.players.through
    extra = 1


class TournamentAddAdminForm(forms.ModelForm):
    auto_add = forms.BooleanField(
        label="Ajouter automatiquement les derniers champions des candidats",
        initial=False, required=False)
    auto_add_deadline = forms.DateTimeField(
        label="Uniquement les champions soumis avant :",
        widget=forms.widgets.DateTimeInput(attrs={'type': 'datetime-local'}),
        initial=now, required=False)
    auto_add_staff = forms.BooleanField(
        label="Inclure également les champions des admins (déconseillé)",
        initial=False, required=False)

    class Media:
        js = ('js/tournament_add.js',)

    class Meta:
        model = models.Tournament
        fields = '__all__'


@admin.register(models.Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'ts')
    inlines = [TournamentMapInline, TournamentPlayerInline]

    add_form = TournamentAddAdminForm
    add_fieldsets = (
        (None, {'fields': ('name',)}),
        ("Champions".upper(), {'fields': ('auto_add', 'auto_add_deadline',
                                          'auto_add_staff')}),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        m = form.instance
        if form.cleaned_data.get('auto_add'):
            deadline = form.cleaned_data.get('auto_add_deadline')
            staff = form.cleaned_data.get('auto_add_staff', False)

            all_chs = models.Champion.objects.filter(status='ready',
                                                     deleted=False)
            if deadline:
                all_chs = all_chs.filter(ts__lte=deadline)
            if not staff:
                all_chs = all_chs.filter(author__is_staff=False)

            # Last champion of each user
            # https://stackoverflow.com/questions/16074498
            chs_ids = (all_chs.values('author__id')
                       .annotate(max_id=Max('id'))
                       .values('max_id'))

            chs = models.Champion.objects.filter(pk__in=chs_ids)
            for c in chs:
                m.players.add(c)


if settings.STECHEC_USE_MAPS:
    admin.site.register(models.Map)
    admin.site.register(models.TournamentMap)
