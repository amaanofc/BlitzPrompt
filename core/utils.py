from django.db.models import F, ExpressionWrapper, FloatField, Q, Value, Case, When
from django.db.models.functions import Now
from django.utils import timezone
import datetime
import math

def get_trending_prompts(queryset, days_window=30, gravity=1.8):
    """
    Ranks prompts using a weighted score based on upvotes and recency.
    
    Parameters:
    - queryset: The base queryset of prompts to rank
    - days_window: Only consider prompts from the last N days
    - gravity: Higher values make score decay faster with time
    
    Returns:
    - Queryset ordered by trending score (descending)
    """
    # Filter to recently active prompts
    recent_date = timezone.now() - datetime.timedelta(days=days_window)
    filtered_queryset = queryset.filter(created_at__gte=recent_date)
    
    # Get the prompts with their attributes
    prompts = list(filtered_queryset.all())
    
    now = timezone.now()
    
    # Calculate trending score for each prompt
    for prompt in prompts:
        time_diff = now - prompt.created_at
        hours_diff = time_diff.total_seconds() / 3600
        prompt.trending_score = prompt.total_votes / ((1 + hours_diff/gravity) ** 1.5)
    
    # Sort by trending score
    prompts.sort(key=lambda p: p.trending_score, reverse=True)
    
    # Extract IDs in the sorted order
    prompt_ids = [prompt.id for prompt in prompts]
    
    # Use Case/When to preserve the order in the database query
    preserved_order = Case(*[When(id=id, then=pos) for pos, id in enumerate(prompt_ids)])
    
    # If no prompts were found, return empty queryset
    if not prompt_ids:
        return queryset.none()
    
    # Return a QuerySet with the order preserved
    return queryset.filter(id__in=prompt_ids).order_by(preserved_order)

def search_prompts(queryset, search_query, search_type='basic'):
    """
    Search for prompts based on the given query.
    
    Parameters:
    - queryset: The base queryset of prompts to search within
    - search_query: The user's search query
    - search_type: 'basic' for simple keyword search, 'advanced' for future extensions
    
    Returns:
    - Filtered queryset matching the search query
    """
    if not search_query:
        return queryset
    
    if search_type == 'basic':
        # Basic search: Look for keywords in title, description, and content
        return queryset.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(categories__name__icontains=search_query)
        ).distinct()
    
    elif search_type == 'tag':
        # Search by exact tag match
        return queryset.filter(categories__name__iexact=search_query).distinct()
    
    # Note: For future semantic search implementation
    # elif search_type == 'semantic':
    #     # For future implementation with embeddings
    #     # This would require storing prompt embeddings and doing vector similarity search
    #     pass
    
    return queryset  # Default fallback

def personalize_results(queryset, user, limit=None):
    """
    Personalize results based on user's history (favorite categories, upvotes, etc.)
    This is a placeholder for future personalization features.
    
    Parameters:
    - queryset: The base queryset of prompts
    - user: The current user
    - limit: Optional limit for returned results
    
    Returns:
    - Personalized queryset
    """
    if not user or not user.is_authenticated:
        return queryset[:limit] if limit else queryset
    
    # Future implementation could:
    # 1. Find categories the user has interacted with most
    # 2. Boost prompts from those categories
    # 3. Boost prompts similar to ones the user has upvoted
    
    # For now, just return the original queryset
    return queryset[:limit] if limit else queryset 