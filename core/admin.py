from django.contrib import admin
from .models import Category, Prompt, Vote

admin.site.register(Category)
admin.site.register(Prompt)
admin.site.register(Vote)