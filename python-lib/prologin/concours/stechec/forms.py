from django import forms
from django.conf import settings
from django.forms import widgets
from django.utils.html import escape, conditional_escape

from itertools import chain, groupby

from prologin.concours.stechec import models


class ChampionUploadForm(forms.Form):
    name = forms.CharField(max_length=25, required=True, label="Nom du champion")
    tarball = forms.FileField(required=True, label="Archive des sources (.tgz)")
    comment = forms.CharField(required=True, widget=forms.widgets.Textarea(), label="Commentaire")

    def clean_name(self):
        name = self.cleaned_data['name']
        try:
            models.Champion.objects.get(name=name)
        except models.Champion.DoesNotExist:
            return name
        raise forms.ValidationError("Nom déjà utilisé")


# Unused since we use a ModelChoiceField to create a match, but could still be
# useful in some way ?
class ChampionField(forms.Field):
    def clean(self, value):
        super(ChampionField, self).clean(value)
        try:
            return models.Champion.objects.get(
                id=int(value.strip()),
                deleted=False,
                status='ready'
            )
        except ValueError:
            raise forms.ValidationError("Numéro de champion invalide.")
        except models.Champion.DoesNotExist:
            raise forms.ValidationError("Champion inexistant")


class MapSelect(widgets.Select):
    def render_options(self, choices, selected_choices):
        def render_option(map):
            title = map.name
            official = map.official
            attrs = (map.id in selected_choices) and ' selected="selected"' or ''
            if official:
                attrs += ' class="award"'

            return '<option value="%d"%s>%s</option>' % (
                map.id, attrs,
                conditional_escape(title)
            )
        selected_choices = set(v for v in selected_choices)
        output = []
        for author, maps in chain(self.choices, choices):
            output.append('<optgroup label="%s">' % escape(author))
            for map_id, map in maps:
                output.append(render_option(map))
            output.append('</optgroup>')
        return '\n'.join(output)


class MatchCreationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(MatchCreationForm, self).__init__(*args, **kwargs)

        self.champions = []
        for i in range(1, settings.STECHEC_NPLAYERS + 1):
            f = forms.ModelChoiceField(label="Champion %d" % i,
                    queryset=models.Champion.objects.all())
            self.fields['champion_%d' % i] = f
            self.champions.append(f)

        if settings.STECHEC_USE_MAPS:
            self.fields['map'] = forms.ChoiceField(required=True,
                    widget=MapSelect(attrs={'class': 'mapselect'}),
                    label="Map utilisée")

            self.fields['map'].choices = [
                (author, [(map.id, map) for map in maps])
                for author, maps in groupby(
                    models.Map.objects.order_by('author__username', 'name'),
                    lambda map: map.author
                )
            ]

    def clean_map(self):
        try:
            value = models.Map.objects.get(id=self.cleaned_data['map'])
        except models.Map.DoesNotExist:
            raise forms.ValidationError("Cette carte n'existe pas")
        return value


class MapCreationForm(forms.Form):
    name = forms.CharField(max_length=25, required=True, label="Nom de la map")
    contents = forms.CharField(required=True, widget=forms.widgets.Textarea(), label="Contenu")
