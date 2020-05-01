from django.contrib import admin
from dpaste.models import Snippet


@admin.register(Snippet)
class SnippetAdmin(admin.ModelAdmin):
    list_display = (
        'lexer',
        'published',
        'expires',
    )
