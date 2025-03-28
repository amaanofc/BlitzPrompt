from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class Prompt(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="The actual prompt text")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    categories = models.ManyToManyField(Category)
    is_favorited = models.ManyToManyField(User, related_name='favorites', blank=True)
    usage_count = models.IntegerField(default=0)  # Track how often a prompt is used
    published = models.BooleanField(default=False)  # Public in library?
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_votes = models.IntegerField(default=0)
    total_comments = models.IntegerField(default=0)
    is_priming = models.BooleanField(default=False, help_text="If True, this prompt will be used as a priming prompt before the user's query")
    priming_order = models.IntegerField(default=0, help_text="Order in which priming prompts should be applied (lower numbers first)")

    def __str__(self):
        return self.title

    def update_vote_count(self):
        self.total_votes = self.votes.aggregate(models.Sum('value'))['value__sum'] or 0
        self.save()

    def get_formatted_prompt(self):
        """Returns the formatted prompt with any necessary formatting"""
        return self.content

class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name='votes')
    value = models.IntegerField(validators=[MinValueValidator(-1), MaxValueValidator(1)])
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'prompt')

class Comment(models.Model):
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on {self.prompt.title}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['prompt', 'author', 'content'],
                name='unique_comment_per_author',
                condition=models.Q(parent__isnull=True)
            ),
            models.UniqueConstraint(
                fields=['parent', 'author', 'content'],
                name='unique_reply_per_author',
                condition=models.Q(parent__isnull=False)
            )
        ]
        indexes = [
            models.Index(fields=['created_at']),
        ]

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=255, default="New Chat")
    system_prompt = models.TextField(default="You are a helpful AI assistant that provides clear and concise responses.")
    priming_prompts = models.ManyToManyField(Prompt, blank=True, related_name='conversations_using')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    @property
    def preview(self):
        """Return a preview of the last message"""
        last_message = self.messages.exclude(role='system').order_by('-created_at').first()
        if last_message:
            return last_message.content[:50] + "..." if len(last_message.content) > 50 else last_message.content
        return "No messages yet"
    
    class Meta:
        ordering = ['-updated_at']

class Message(models.Model):
    ROLE_CHOICES = (
        ('system', 'System'),
        ('user', 'User'),
        ('assistant', 'Assistant'),
    )
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    prompt_used = models.ForeignKey(Prompt, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.role} message in {self.conversation.title}"
    
    class Meta:
        ordering = ['created_at']

class APIUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_usage')
    timestamp = models.DateTimeField(auto_now_add=True)
    requests_count = models.IntegerField(default=1)
    tokens_count = models.IntegerField(default=0)
    model = models.CharField(max_length=50, default='deepseek-chat')
    
    def __str__(self):
        return f"API usage by {self.user.username} at {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']