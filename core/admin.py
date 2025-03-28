from django.contrib import admin
from .models import Category, Prompt, Vote, Comment, Conversation, Message, APIUsage

# Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'id')
    search_fields = ('name',)

# Prompt Admin
@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published', 'created_at', 'total_votes')
    list_filter = ('published', 'created_at', 'categories')
    search_fields = ('title', 'description', 'content', 'author__username')
    filter_horizontal = ('categories',)
    date_hierarchy = 'created_at'
    
# Vote Admin
@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'prompt', 'value', 'voted_at')
    list_filter = ('value', 'voted_at')
    search_fields = ('user__username', 'prompt__title')
    date_hierarchy = 'voted_at'

# Comment Admin
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'prompt', 'parent', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('author__username', 'content', 'prompt__title')
    date_hierarchy = 'created_at'

# Conversation Admin
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'user__username')
    date_hierarchy = 'created_at'

# Message Admin
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content', 'conversation__title', 'conversation__user__username')
    date_hierarchy = 'created_at'

# API Usage Admin
@admin.register(APIUsage)
class APIUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'timestamp', 'requests_count', 'tokens_count')
    list_filter = ('timestamp',)
    search_fields = ('user__username',)
    date_hierarchy = 'timestamp'