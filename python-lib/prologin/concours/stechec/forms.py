from crispy_forms.helper import FormHelper
from crispy_forms import layout, bootstrap
from django import forms
from django.conf import settings
from django.forms import widgets
from django.contrib.auth.forms import AuthenticationForm
from django.utils.html import escape, conditional_escape

from itertools import chain, groupby

from prologin.concours.stechec import models


class BaseFormHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        self.is_horizontal = kwargs.pop('horizontal', True)
        self.label_width = kwargs.pop('label_width', 2)
        self.field_width = kwargs.pop('field_width', 8)
        self.width_size = kwargs.pop('width_size', 'sm')
        super().__init__(*args, **kwargs)
        self.layout = layout.Layout()
        if self.is_horizontal:
            self.form_class = 'form-horizontal'
            self.field_class = self._grid_class('field')
            self.label_class = self._grid_class('label')

    def _grid_class(self, type, offset=False):
        attr = self.label_width if type == 'label' else self.field_width
        return 'col-{}-{}{} '.format(self.width_size, 'offset-' if offset else '', attr)

    def append_field(self, field):
        self.layout.fields.append(field)

    def append_submit(self, label):
        btn = bootstrap.StrictButton(label, css_class='btn-primary', type="submit")
        if self.is_horizontal:
            self.append_field(
                layout.Div(
                    layout.Div(
                        btn,
                        css_class=self._grid_class('label', offset=True) + self._grid_class('field')),
                    css_class="form-group"
                )
            )
        else:
            self.append_field(btn)


class ChampionUploadForm(forms.Form):
    name = forms.CharField(max_length=25, required=True, label="Nom")
    tarball = forms.FileField(required=True, label="Sources",
                              help_text="Archive au format <tt>.tgz</tt>")
    comment = forms.CharField(required=True,
                              widget=forms.widgets.Textarea(attrs={'rows': 3}),
                              label="Commentaire")

    def clean_name(self):
        name = self.cleaned_data['name']
        try:
            models.Champion.objects.get(name=name)
        except models.Champion.DoesNotExist:
            return name
        raise forms.ValidationError("Nom déjà utilisé")

    helper = BaseFormHelper()
    helper.append_field('name')
    helper.append_field('tarball')
    helper.append_field('comment')
    helper.append_submit("Envoyer le champion")


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
        self.helper = BaseFormHelper()
        self.champions = []
        for i in range(1, settings.STECHEC_NPLAYERS + 1):
            f = forms.ModelChoiceField(label="Champion %d" % i,
                                       queryset=models.Champion.objects.all())
            self.fields['champion_%d' % i] = f
            self.helper.append_field('champion_%d' % i)
            self.champions.append(f)

        if settings.STECHEC_USE_MAPS:
            self.fields['map'] = forms.ChoiceField(required=True,
                                                   widget=MapSelect(attrs={'class': 'mapselect'}),
                                                   label="Carte utilisée")

            self.fields['map'].choices = [
                (author, [(map.id, map) for map in maps])
                for author, maps in groupby(
                    models.Map.objects.order_by('author__username', 'name'),
                    lambda map: map.author
                )
            ]

        self.helper.append_submit("Lancer le match")

    def clean_map(self):
        try:
            value = models.Map.objects.get(id=self.cleaned_data['map'])
        except models.Map.DoesNotExist:
            raise forms.ValidationError("Cette carte n'existe pas")
        return value


class MapCreationForm(forms.Form):
    name = forms.CharField(max_length=25, required=True, label="Nom")
    contents = forms.CharField(required=True,
                               widget=forms.widgets.Textarea(attrs={'class': 'monospace'}),
                               label="Contenu")

    helper = BaseFormHelper()
    helper.append_field('name')
    helper.append_field('contents')
    helper.append_submit("Envoyer la carte")


class LoginForm(AuthenticationForm):
    helper = BaseFormHelper()
    helper.append_field('username')
    helper.append_field('password')
    helper.append_submit("Se connecter")