from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

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

    def __str__(self):
        return self.title

    def update_vote_count(self):
        self.total_votes = self.votes.aggregate(models.Sum('value'))['value__sum'] or 0
        self.save()

class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name='votes')
    value = models.IntegerField(validators=[MinValueValidator(-1), MaxValueValidator(1)])
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'prompt')

class Comment(models.Model):
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    is_edited = models.BooleanField(default=False)

    def __str__(self):
        return f"Comment by {self.author.username} on {self.prompt.title}"

    class Meta:
        ordering = ['-created_at']