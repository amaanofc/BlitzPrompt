from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from .models import Prompt, Category, Vote, Comment, Conversation, Message, APIUsage, PrimingPrompt
import json
import requests
from django.conf import settings
from django.db import transaction
import time
from django.db import connection
from django.db.utils import IntegrityError
from django.db import models
from .utils import get_trending_prompts, search_prompts, personalize_results
from django.views.decorators.http import require_POST
from django.db.utils import OperationalError

def home(request):
    # Get trending prompts using our new algorithm
    base_queryset = Prompt.objects.filter(published=True)
    trending_prompts = get_trending_prompts(base_queryset)[:6]
    
    return render(request, 'core/home.html', {
        'trending_prompts': trending_prompts
    })

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

@login_required
def prompt_library(request):
    category = request.GET.get('category')
    search = request.GET.get('search')
    search_type = request.GET.get('search_type', 'basic')  # Default to basic search
    sort = request.GET.get('sort', 'trending')  # Default sort by trending

    prompts = Prompt.objects.filter(published=True)
    
    # Apply category filter if specified
    if category:
        prompts = prompts.filter(categories__name=category)
    
    # Apply search if provided
    if search:
        prompts = search_prompts(prompts, search, search_type)
    
    # Apply sorting
    if sort == 'trending':
        prompts = get_trending_prompts(prompts)
    elif sort == '-total_votes':
        prompts = prompts.order_by('-total_votes')
    elif sort == '-created_at':
        prompts = prompts.order_by('-created_at')
    elif sort == 'created_at':
        prompts = prompts.order_by('created_at')
    else:
        prompts = prompts.order_by(sort)
    
    # Apply personalization if enabled in the future
    # prompts = personalize_results(prompts, request.user)
    
    paginator = Paginator(prompts, 12)  # 12 prompts per page
    page = request.GET.get('page')
    prompts = paginator.get_page(page)

    categories = Category.objects.all()
    return render(request, 'core/library.html', {
        'prompts': prompts,
        'categories': categories,
        'selected_category': category,
        'search_query': search,
        'search_type': search_type,
        'sort': sort
    })

@login_required
def prompt_detail(request, prompt_id):
    prompt = get_object_or_404(Prompt, id=prompt_id, published=True)
    comments = prompt.comments.filter(parent=None).order_by('-created_at')
    
    # Get user's current vote if any
    user_vote = 0
    is_favorited = False
    
    if request.user.is_authenticated:
        try:
            vote = Vote.objects.get(user=request.user, prompt=prompt)
            user_vote = vote.value
        except Vote.DoesNotExist:
            pass
        
        # Check if this prompt is in user's favorites
        is_favorited = request.user.favorites.filter(id=prompt_id).exists()
    
    return render(request, 'core/prompt_detail.html', {
        'prompt': prompt,
        'comments': comments,
        'user_vote': user_vote,
        'is_favorited': is_favorited
    })

def gpt_interface(request):
    """Main chat interface view"""
    if request.user.is_authenticated:
        # Get user's favorite prompts
        favorites = request.user.favorites.all()
        
        # Get user's created prompts
        user_prompts = Prompt.objects.filter(author=request.user)
        
        # Get user's priming prompts
        priming_prompts = PrimingPrompt.objects.filter(
            user=request.user, 
            is_active=True
        ).select_related('prompt').order_by('position')

        # Check if a specific conversation is requested
        conversation_id = request.GET.get('conversation_id')
        current_conversation = None
        messages = []
        
        if conversation_id:
            try:
                current_conversation = Conversation.objects.get(id=conversation_id, user=request.user)
                messages = current_conversation.messages.all()
            except Conversation.DoesNotExist:
                pass
        
        # Get user's recent conversations
        conversations = Conversation.objects.filter(user=request.user).order_by('-updated_at')[:10]
        
        # Get rate limits
        rate_limits = get_rate_limits(request.user)
        
        # Get all categories for prompt creation
        categories = Category.objects.all()
    else:
        # For non-authenticated users
        favorites = []
        user_prompts = []
        priming_prompts = []
        current_conversation = None
        messages = []
        conversations = []
        categories = []
        rate_limits = {
            'requests_used': 0,
            'requests_limit': 1000,
            'tokens_used': 0,
            'tokens_limit': 100000,
            'requests_remaining': 1000,
            'tokens_remaining': 100000
        }
    
    return render(request, 'core/interface.html', {
        'favorites': favorites,
        'user_prompts': user_prompts,
        'priming_prompts': priming_prompts,
        'current_conversation': current_conversation,
        'messages': messages,
        'conversations': conversations,
        'rate_limits': rate_limits,
        'categories': categories
    })

@login_required
def toggle_favorite(request, prompt_id):
    """Toggle a prompt as favorite/unfavorite for the current user"""
    try:
        # Get the prompt
        prompt = Prompt.objects.get(id=prompt_id)
        
        # Track the previous state for logging
        was_favorited = request.user.favorites.filter(id=prompt_id).exists()
        
        # Use a transaction to prevent race conditions
        with transaction.atomic():
            # Check if the prompt is already in favorites
            if was_favorited:
                # Remove from favorites
                request.user.favorites.remove(prompt)
                is_favorited = False
            else:
                # Add to favorites
                request.user.favorites.add(prompt)
                is_favorited = True
        
        print(f"DEBUG: Toggle favorite for prompt {prompt_id} - Before: {was_favorited}, After: {is_favorited}")
        
        return JsonResponse({
            'success': True,
            'is_favorited': is_favorited,
            'prompt_id': prompt_id,
            'prompt_title': prompt.title
        })
    except Prompt.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Prompt not found',
            'is_favorited': False
        }, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e),
            'is_favorited': None
        }, status=500)

@login_required
def publish_prompt(request, prompt_id):
    try:
        prompt = Prompt.objects.get(id=prompt_id)
        # Only allow the author to publish their prompt
        if prompt.author != request.user:
            return JsonResponse({'error': 'You can only publish your own prompts'}, status=403)
            
        prompt.published = True
        prompt.save()
        return JsonResponse({'published': True})
    except Prompt.DoesNotExist:
        return JsonResponse({'error': 'Prompt not found'}, status=404)

@login_required
@require_POST
def api_vote(request):
    """API endpoint for voting on prompts"""
    max_retries = 3
    retry_delay = 0.1  # seconds
    
    for attempt in range(max_retries):
        try:
            data = json.loads(request.body)
            prompt_id = data.get('prompt_id')
            value = data.get('value')
            
            if not prompt_id or value not in [-1, 0, 1]:
                return JsonResponse({'success': False, 'error': 'Invalid data'})
            
            with transaction.atomic():
                # Get prompt without locking for initial validation
                prompt = get_object_or_404(Prompt, id=prompt_id)
                
                # Check if user has already voted - without locking
                current_vote = None
                try:
                    current_vote = Vote.objects.get(user=request.user, prompt=prompt)
                except Vote.DoesNotExist:
                    pass
                
                # Handle the vote operation
                if current_vote:
                    if value == 0:
                        # Remove vote if value is 0
                        current_vote.delete()
                    else:
                        # Update existing vote
                        current_vote.value = value
                        current_vote.save()
                elif value != 0:  # Don't create a new vote with value 0
                    # Create new vote
                    Vote.objects.create(user=request.user, prompt=prompt, value=value)
                
                # Update prompt's vote count without locking the entire table
                prompt.update_vote_count()
                
                # Get user's current vote if any
                try:
                    user_vote = Vote.objects.get(user=request.user, prompt=prompt).value
                except Vote.DoesNotExist:
                    user_vote = 0
                
                return JsonResponse({
                    'success': True,
                    'total_votes': prompt.total_votes,
                    'user_vote': user_vote
                })
        
        except OperationalError as e:
            # Check if it's a database lock error
            if "database is locked" in str(e) and attempt < max_retries - 1:
                # Wait a bit before retrying
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                continue
            # On the last attempt, re-raise the exception
            raise
                
        except IntegrityError:
            # Handle duplicate voting attempts gracefully
            try:
                prompt = get_object_or_404(Prompt, id=prompt_id)
                try:
                    user_vote = Vote.objects.get(user=request.user, prompt=prompt).value
                except Vote.DoesNotExist:
                    user_vote = 0
                    
                return JsonResponse({
                    'success': True,
                    'total_votes': prompt.total_votes,
                    'user_vote': user_vote
                })
            except Exception as e:
                return JsonResponse({'success': False, 'error': 'An unexpected error occurred'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

@login_required
@transaction.atomic
def add_comment(request, prompt_id):
    try:
        prompt = Prompt.objects.select_for_update().get(id=prompt_id)
        data = json.loads(request.body) if request.body else {}
        content = data.get('content', '').strip()
        parent_id = data.get('parent_id')

        if not content:
            return JsonResponse({'error': 'Comment content is required'}, status=400)

        parent = None
        if parent_id:
            parent = Comment.objects.select_for_update().get(id=parent_id)

        try:
            comment = Comment.objects.create(
                prompt=prompt,
                author=request.user,
                content=content,
                parent=parent
            )
        except IntegrityError as e:
            if 'unique_comment_per_author' in str(e):
                return JsonResponse({'error': 'You already posted this exact comment'}, status=400)
            if 'unique_reply_per_author' in str(e):
                return JsonResponse({'error': 'You already posted this exact reply'}, status=400)
            return JsonResponse({'error': 'Database error'}, status=400)

        # Update counter using atomic update
        Prompt.objects.filter(id=prompt_id).update(
            total_comments=models.F('total_comments') + 1
        )

        return JsonResponse({
            'id': comment.id,
            'content': comment.content,
            'author': comment.author.username,
            'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def profile(request):
    user_prompts = Prompt.objects.filter(author=request.user)
    favorite_prompts = request.user.favorites.all()
    
    context = {
        'user_prompts': user_prompts,
        'published_count': user_prompts.filter(published=True).count(),
        'draft_count': user_prompts.filter(published=False).count(),
        'favorite_prompts': favorite_prompts
    }
    return render(request, 'core/profile.html', context)

@login_required
def favorites(request):
    favorite_prompts = request.user.favorites.all()
    return render(request, 'core/favorites.html', {
        'favorite_prompts': favorite_prompts
    })

@login_required
def create_prompt(request):
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            content = request.POST.get('content')
            description = request.POST.get('description')
            categories = request.POST.getlist('categories')
            new_category = request.POST.get('new_category', '').strip()
            is_priming = request.POST.get('is_priming') == 'on'
            priming_order = int(request.POST.get('priming_order', 0))
            
            # Validate required fields
            if not title or not content:
                return JsonResponse({
                    'success': False,
                    'error': 'Title and content are required'
                }, status=400)
            
            # First check if an identical prompt exists
            existing_prompt = Prompt.objects.filter(
                title=title,
                content=content,
                author=request.user
            ).first()
            
            if existing_prompt:
                # Don't create a new one, just return the existing one
                return JsonResponse({
                    'success': True,
                    'prompt_id': existing_prompt.id,
                    'message': 'Prompt already exists'
                })
            
            # Create the prompt in a transaction to prevent duplicates
            with transaction.atomic():
                # Double-check within transaction to prevent race conditions
                existing_prompt = Prompt.objects.filter(
                    title=title,
                    content=content,
                    author=request.user
                ).first()
                
                if existing_prompt:
                    return JsonResponse({
                        'success': True,
                        'prompt_id': existing_prompt.id,
                        'message': 'Prompt already exists'
                    })
                
                # Create the prompt
                prompt = Prompt.objects.create(
                    title=title,
                    content=content,
                    description=description,
                    author=request.user,
                    is_priming=is_priming,
                    priming_order=priming_order
                )
                
                # Add categories if any
                if categories:
                    prompt.categories.set(categories)
                
                # Handle new category creation
                if new_category:
                    # Check if the category already exists (case insensitive)
                    existing_category = Category.objects.filter(name__iexact=new_category).first()
                    if existing_category:
                        # Use existing category
                        prompt.categories.add(existing_category)
                    else:
                        # Create new category
                        new_cat = Category.objects.create(
                            name=new_category,
                            description=f"User-created category: {new_category}"
                        )
                        prompt.categories.add(new_cat)
                
                # If it's a priming prompt, add to favorites automatically
                if is_priming:
                    request.user.favorites.add(prompt)
                    
                    # Get the current maximum position
                    max_position = PrimingPrompt.objects.filter(user=request.user).aggregate(max_pos=models.Max('position'))
                    position = (max_position['max_pos'] or 0) + 1
                    
                    # Create the priming prompt entry
                    PrimingPrompt.objects.create(
                        user=request.user,
                        prompt=prompt,
                        position=position,
                        is_active=True
                    )
                
                return JsonResponse({
                    'success': True,
                    'prompt_id': prompt.id,
                    'message': 'Prompt created successfully'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error creating prompt: {str(e)}'
            }, status=500)
    
    # For GET requests, return the form
    categories = Category.objects.all()
    return render(request, 'core/create_prompt.html', {
        'categories': categories
    })

@login_required
def get_prompt_info(request, prompt_id):
    try:
        prompt = Prompt.objects.get(id=prompt_id)
        # Check if the user has access (authored or published)
        if prompt.author == request.user or prompt.published:
            # Get category names
            categories = [category.name for category in prompt.categories.all()]
            
            return JsonResponse({
                'success': True,
                'title': prompt.title,
                'content': prompt.content,
                'description': prompt.description,
                'published': prompt.published,
                'is_author': prompt.author == request.user,
                'categories': categories
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'You do not have access to this prompt'
            }, status=403)
    except Prompt.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Prompt not found'
        }, status=404)

@login_required
def delete_prompt(request, prompt_id):
    try:
        prompt = Prompt.objects.get(id=prompt_id)
        # Only allow the author to delete their prompt
        if prompt.author != request.user:
            return JsonResponse({'error': 'You can only delete your own prompts'}, status=403)
            
        prompt_title = prompt.title
        prompt.delete()
        return JsonResponse({'success': True, 'message': f'Prompt "{prompt_title}" has been deleted'})
    except Prompt.DoesNotExist:
        return JsonResponse({'error': 'Prompt not found'}, status=404)

@login_required
def delete_comment(request, comment_id):
    try:
        comment = Comment.objects.get(id=comment_id)
        
        # Only allow the comment author to delete it
        if comment.author != request.user:
            return JsonResponse({'error': 'You can only delete your own comments'}, status=403)
        
        # Get the prompt to update comment count
        prompt = comment.prompt
        
        # Delete the comment
        comment.delete()
        
        # Update comment count on the prompt
        prompt.total_comments -= 1
        prompt.save()
        
        return JsonResponse({'success': True})
    except Comment.DoesNotExist:
        return JsonResponse({'error': 'Comment not found'}, status=404)

@login_required
def chat_api(request):
    """API endpoint for chat interactions"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'Please login or create an account to chat with the AI',
            'login_url': '/login/',
            'signup_url': '/signup/',
            'require_auth': True
        }, status=401)
    
    try:
        data = json.loads(request.body)
        message = data.get('message')
        conversation_id = data.get('conversation_id')
        prompt_id = data.get('prompt_id')
        model = data.get('model', 'deepseek-chat')
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Get or create conversation
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=request.user)
            except Conversation.DoesNotExist:
                return JsonResponse({'error': 'Conversation not found'}, status=404)
        else:
            # Create a new conversation
            conversation = Conversation.objects.create(
                user=request.user,
                title=message[:30] + "..." if len(message) > 30 else message
            )
            
            # Add system message
            Message.objects.create(
                conversation=conversation,
                role='system',
                content=conversation.system_prompt
            )
        
        # Get selected prompt if any
        selected_prompt = None
        if prompt_id:
            try:
                selected_prompt = Prompt.objects.get(id=prompt_id)
                
                # Add to favorites if not already
                if not request.user.favorites.filter(id=prompt_id).exists():
                    request.user.favorites.add(selected_prompt)
                
                # Increment usage count
                selected_prompt.usage_count += 1
                selected_prompt.save()
            except Prompt.DoesNotExist:
                pass
        
        # Add user message
        Message.objects.create(
            conversation=conversation,
            role='user',
            content=message
        )
        
        # Prepare API request
        headers = {
            'Authorization': f'Bearer {settings.DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Get all messages from this conversation
        conversation_messages = []
        for msg in conversation.messages.all():
            role = msg.role
            content = msg.content
            
            # Add to messages list
            conversation_messages.append({
                'role': role,
                'content': content
            })
        
        # Get and add all active priming prompts in their defined order
        priming_prompts = PrimingPrompt.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('prompt').order_by('position')
        
        # Insert priming prompts at the beginning, right after system message
        system_index = next((i for i, msg in enumerate(conversation_messages) if msg['role'] == 'system'), 0)
        insert_index = system_index + 1
        
        for pp in priming_prompts:
            conversation_messages.insert(insert_index, {
                'role': 'system',
                'content': pp.prompt.get_formatted_prompt()
            })
            insert_index += 1
            
        # Add the selected prompt as a system message if present
        if selected_prompt:
            # Insert before the user's message
            idx = next((i for i, msg in enumerate(conversation_messages) if msg['role'] == 'user'), len(conversation_messages))
            conversation_messages.insert(idx - 1, {
                'role': 'system',
                'content': selected_prompt.get_formatted_prompt()
            })
        
        # Create API request data
        request_data = {
            'model': model,
            'messages': conversation_messages,
            'max_tokens': 2000,
            'temperature': 0.7,
            'top_p': 0.9,
            'frequency_penalty': 0.5,
            'presence_penalty': 0.5
        }
        
        # Update conversation's updated_at timestamp
        conversation.save()
        
        # Make API request
        start_time = time.time()
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers=headers,
            json=request_data
        )
        
        # Track API usage
        api_usage = APIUsage.objects.create(
            user=request.user,
            model=model
        )
        
        if response.status_code == 200:
            response_data = response.json()
            ai_response = response_data['choices'][0]['message']['content']
            
            # Calculate tokens if available
            if 'usage' in response_data:
                api_usage.tokens_count = response_data['usage'].get('total_tokens', 0)
                api_usage.save()
            
            # Save assistant message
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=ai_response,
                prompt_used=selected_prompt
            )
            
            # Get rate limits
            rate_limits = get_rate_limits(request.user)
            
            return JsonResponse({
                'response': ai_response,
                'conversation_id': conversation.id,
                'conversation_title': conversation.title,
                'prompt_id': prompt_id,
                'rate_limits': rate_limits,
                'elapsed_time': round(time.time() - start_time, 2)
            })
        else:
            error_msg = f"API Error: {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg += f" - {error_data['error']['message']}"
            except:
                error_msg += f" - {response.text}"
            
            return JsonResponse({'error': error_msg}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def prompt_api(request, prompt_id):
    """API endpoint to get prompt details"""
    try:
        prompt = get_object_or_404(Prompt, id=prompt_id)
        is_favorited = request.user.favorites.filter(id=prompt_id).exists()
        
        categories = [category.name for category in prompt.categories.all()]
        
        return JsonResponse({
            'id': prompt.id,
            'title': prompt.title,
            'description': prompt.description,
            'content': prompt.content,
            'author': prompt.author.username,
            'is_favorited': is_favorited,
            'is_author': prompt.author.id == request.user.id,
            'published': prompt.published,
            'usage_count': prompt.usage_count,
            'categories': categories,
            'total_votes': prompt.total_votes,
            'created_at': prompt.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def conversations_api(request):
    """API endpoint to list user conversations"""
    try:
        conversations = Conversation.objects.filter(user=request.user)
        
        data = []
        for conv in conversations:
            data.append({
                'id': conv.id,
                'title': conv.title,
                'preview': conv.preview,
                'created_at': conv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': conv.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                'message_count': conv.messages.count()
            })
        
        return JsonResponse({'conversations': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def conversation_detail_api(request, conversation_id):
    """API endpoint to get conversation details and messages"""
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        
        messages = []
        for msg in conversation.messages.all():
            messages.append({
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({
            'id': conversation.id,
            'title': conversation.title,
            'system_prompt': conversation.system_prompt,
            'created_at': conversation.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': conversation.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'messages': messages
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def rate_limits_api(request):
    """API endpoint to get user's API rate limits"""
    try:
        rate_limits = get_rate_limits(request.user)
        return JsonResponse(rate_limits)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_rate_limits(user):
    """Helper function to calculate current rate limits"""
    import datetime
    from django.utils import timezone
    from django.db.models import Sum
    
    # Get usage in the last 24 hours
    day_ago = timezone.now() - datetime.timedelta(days=1)
    requests_24h = APIUsage.objects.filter(user=user, timestamp__gte=day_ago).count()
    tokens_24h = APIUsage.objects.filter(user=user, timestamp__gte=day_ago).aggregate(
        Sum('tokens_count')
    )['tokens_count__sum'] or 0
    
    # Set limits (these could be customizable per user or stored in settings)
    requests_limit = 1000  # Default limit of 1000 requests per day
    tokens_limit = 100000  # Default limit of 100,000 tokens per day
    
    return {
        'requests_used': requests_24h,
        'requests_limit': requests_limit,
        'tokens_used': tokens_24h,
        'tokens_limit': tokens_limit,
        'requests_remaining': max(0, requests_limit - requests_24h),
        'tokens_remaining': max(0, tokens_limit - tokens_24h)
    }

@login_required
def priming_prompts_api(request):
    """API endpoint to get all priming prompts for the current user."""
    try:
        # Get the user's priming prompts
        priming_prompts = PrimingPrompt.objects.filter(user=request.user).select_related('prompt').order_by('position')
        
        # Get the user's prompts and favorites - ensure we're getting the same structure from both
        user_prompts = list(Prompt.objects.filter(author=request.user).values('id', 'title', 'description'))
        favorite_prompts = list(request.user.favorites.all().values('id', 'title', 'description'))
        
        # Combine user prompts and favorites
        all_available_prompts = user_prompts + favorite_prompts
        
        # Remove duplicates by creating a dictionary with prompt IDs as keys
        unique_prompts = {}
        for prompt in all_available_prompts:
            unique_prompts[prompt['id']] = prompt
        
        # Format the priming prompts data
        priming_prompts_data = []
        for pp in priming_prompts:
            priming_prompts_data.append({
                'id': pp.prompt.id,
                'title': pp.prompt.title,
                'description': pp.prompt.description,
                'position': pp.position,
                'is_active': pp.is_active
            })
        
        # Format all available prompts data - this should be a list, not a dictionary
        user_prompts_data = list(unique_prompts.values())
        
        return JsonResponse({
            'success': True,
            'priming_prompts': priming_prompts_data,
            'user_prompts': user_prompts_data
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def update_priming_prompts(request):
    """API endpoint to update the order of priming prompts."""
    try:
        data = json.loads(request.body)
        prompts = data.get('prompts', [])
        
        with transaction.atomic():
            # Delete existing priming prompts
            PrimingPrompt.objects.filter(user=request.user).delete()
            
            # Create new priming prompts with updated positions
            for prompt_data in prompts:
                prompt_id = prompt_data.get('id')
                position = prompt_data.get('position', 0)
                
                # Verify the prompt exists
                prompt = get_object_or_404(Prompt, id=prompt_id)
                
                # Create the priming prompt
                PrimingPrompt.objects.create(
                    user=request.user,
                    prompt=prompt,
                    position=position,
                    is_active=True
                )
        
        return JsonResponse({
            'success': True
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def toggle_priming_prompt(request, prompt_id):
    """API endpoint to toggle a priming prompt's active status."""
    try:
        # Get the priming prompt
        priming_prompt = get_object_or_404(PrimingPrompt, user=request.user, prompt_id=prompt_id)
        
        # Toggle the active status
        priming_prompt.is_active = not priming_prompt.is_active
        priming_prompt.save()
        
        return JsonResponse({
            'success': True,
            'is_active': priming_prompt.is_active
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)