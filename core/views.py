from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import Prompt, Category, Vote, Comment
import json
import requests
from django.conf import settings
from django.db import transaction

def home(request):
    # Get trending prompts (top 6 by votes)
    trending_prompts = Prompt.objects.filter(published=True).order_by('-total_votes')[:6]
    
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
    sort = request.GET.get('sort', '-total_votes')  # Default sort by votes

    prompts = Prompt.objects.filter(published=True)
    
    if category:
        prompts = prompts.filter(categories__name=category)
    if search:
        prompts = prompts.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(content__icontains=search)
        )
    
    prompts = prompts.order_by(sort)
    paginator = Paginator(prompts, 12)  # 12 prompts per page
    page = request.GET.get('page')
    prompts = paginator.get_page(page)

    categories = Category.objects.all()
    return render(request, 'core/library.html', {
        'prompts': prompts,
        'categories': categories,
        'selected_category': category,
        'search_query': search
    })

@login_required
def prompt_detail(request, prompt_id):
    prompt = get_object_or_404(Prompt, id=prompt_id, published=True)
    comments = prompt.comments.filter(parent=None).order_by('-created_at')
    return render(request, 'core/prompt_detail.html', {
        'prompt': prompt,
        'comments': comments
    })

@login_required
def gpt_interface(request):
    if request.user.is_authenticated:
        favorites = request.user.favorites.all()
        favorited_ids = [p.id for p in favorites]
    else:
        favorites = []
        favorited_ids = []
    
    # Get categories for the create prompt tab
    categories = Category.objects.all()
    
    # Check if a prompt was requested via query parameter
    prompt_id = request.GET.get('prompt_id')
    selected_prompt = None
    
    if prompt_id:
        try:
            # Try to get the prompt
            selected_prompt = Prompt.objects.get(id=prompt_id)
            
            # If user doesn't have this prompt in favorites, add it
            if request.user.is_authenticated and not request.user.favorites.filter(id=prompt_id).exists():
                request.user.favorites.add(selected_prompt)
                favorites = request.user.favorites.all()  # Refresh favorites
                favorited_ids = [p.id for p in favorites]
        except Prompt.DoesNotExist:
            pass
    
    if request.method == 'POST':
        try:
            prompt_id = request.POST.get('prompt_id')
            user_query = request.POST.get('query')
            
            selected_prompt = Prompt.objects.get(id=prompt_id)
            
            # Get all priming prompts for the user, ordered by priming_order
            priming_prompts = Prompt.objects.filter(
                is_priming=True,
                published=True
            ).order_by('priming_order')
            
            # Construct the full prompt with priming prompts
            full_prompt = []
            
            # Add priming prompts first
            for priming_prompt in priming_prompts:
                full_prompt.append(priming_prompt.get_formatted_prompt())
            
            # Add the selected prompt
            full_prompt.append(selected_prompt.get_formatted_prompt())
            
            # Add the user's query
            full_prompt.append(f"\nUser Query: {user_query}")
            
            # Join all parts with double newlines
            final_prompt = "\n\n".join(full_prompt)
            
            # DeepSeek API integration
            headers = {
                'Authorization': f'Bearer {settings.DEEPSEEK_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'deepseek-chat',  # Required model parameter
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a helpful AI assistant that provides clear and concise responses.'
                    },
                    {
                        'role': 'user',
                        'content': final_prompt
                    }
                ],
                'max_tokens': 1000,
                'temperature': 0.7,
                'top_p': 0.9,
                'frequency_penalty': 0.5,
                'presence_penalty': 0.5
            }
            
            response = requests.post(
                'https://api.deepseek.com/v1/chat/completions',
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                ai_response = response.json()['choices'][0]['message']['content']
            else:
                ai_response = f"Error: Unable to get response from DeepSeek (Status: {response.status_code})"
                if response.text:
                    ai_response += f"\nDetails: {response.text}"

            selected_prompt.usage_count += 1
            selected_prompt.save()
            
            return render(request, 'core/interface.html', {
                'response': ai_response,
                'favorites': favorites,
                'selected_prompt': selected_prompt,
                'favorited_ids': favorited_ids,
                'categories': categories,
                'user_query': user_query
            })
        except Exception as e:
            return render(request, 'core/interface.html', {
                'error': str(e),
                'favorites': favorites,
                'selected_prompt': selected_prompt,
                'favorited_ids': favorited_ids,
                'categories': categories
            })
    
    return render(request, 'core/interface.html', {
        'favorites': favorites,
        'selected_prompt': selected_prompt,
        'favorited_ids': favorited_ids,
        'categories': categories
    })

@login_required
def toggle_favorite(request, prompt_id):
    try:
        prompt = Prompt.objects.get(id=prompt_id)
        
        # Check if the prompt is already in favorites
        is_favorited = request.user.favorites.filter(id=prompt_id).exists()
        
        if is_favorited:
            # Remove from favorites
            request.user.favorites.remove(prompt)
            is_favorited = False
        else:
            # Add to favorites - using set() instead of add() to prevent duplicates
            request.user.favorites.set([prompt], clear=False)
            is_favorited = True
            
        return JsonResponse({'is_favorited': is_favorited})
    except Prompt.DoesNotExist:
        return JsonResponse({'error': 'Prompt not found'}, status=404)

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
def vote_prompt(request, prompt_id):
    try:
        prompt = Prompt.objects.get(id=prompt_id)
        value = int(request.POST.get('value', 0))
        
        if value not in [-1, 0, 1]:
            return JsonResponse({'error': 'Invalid vote value'}, status=400)
            
        vote, created = Vote.objects.get_or_create(
            user=request.user,
            prompt=prompt,
            defaults={'value': value}
        )
        
        if not created:
            if value == 0:
                vote.delete()
            else:
                vote.value = value
                vote.save()
                
        prompt.update_vote_count()
        return JsonResponse({
            'total_votes': prompt.total_votes,
            'user_vote': value
        })
    except Prompt.DoesNotExist:
        return JsonResponse({'error': 'Prompt not found'}, status=404)

@login_required
def add_comment(request, prompt_id):
    try:
        prompt = Prompt.objects.get(id=prompt_id)
        
        # Parse data correctly based on request type
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            content = data.get('content')
            parent_id = data.get('parent_id')
        else:
            content = request.POST.get('content')
            parent_id = request.POST.get('parent_id')
        
        if not content:
            return JsonResponse({'error': 'Comment content is required'}, status=400)
            
        parent = None
        if parent_id:
            parent = Comment.objects.get(id=parent_id)
            
        comment = Comment.objects.create(
            prompt=prompt,
            author=request.user,
            content=content,
            parent=parent
        )
        
        prompt.total_comments += 1
        prompt.save()
        
        return JsonResponse({
            'id': comment.id,
            'content': comment.content,
            'author': comment.author.username,
            'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Prompt.DoesNotExist:
        return JsonResponse({'error': 'Prompt not found'}, status=404)
    except Comment.DoesNotExist:
        return JsonResponse({'error': 'Parent comment not found'}, status=404)

@login_required
def profile(request):
    user_prompts = Prompt.objects.filter(author=request.user)
    favorite_prompts = request.user.favorites.all()
    
    return render(request, 'core/profile.html', {
        'user_prompts': user_prompts,
        'favorite_prompts': favorite_prompts
    })

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
            title = request.POST.get('title')
            description = request.POST.get('description')
            content = request.POST.get('content')
            category_ids = request.POST.getlist('categories')
            
            # Use atomic transaction to prevent duplicates
            with transaction.atomic():
                # Check if a similar prompt already exists for this user
                existing_prompt = Prompt.objects.filter(
                    title=title,
                    author=request.user,
                    content=content
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
                    description=description,
                    content=content,
                    author=request.user
                )
    
                # Add selected categories
                for category_id in category_ids:
                    try:
                        category = Category.objects.get(id=category_id)
                        prompt.categories.add(category)
                    except Category.DoesNotExist:
                        pass
                
                # Automatically add to user's favorites
                request.user.favorites.add(prompt)
    
            return JsonResponse({
                'success': True,
                'prompt_id': prompt.id
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def get_prompt_info(request, prompt_id):
    try:
        prompt = Prompt.objects.get(id=prompt_id)
        # Check if the user has access (authored or published)
        if prompt.author == request.user or prompt.published:
            return JsonResponse({
                'success': True,
                'title': prompt.title,
                'content': prompt.content,
                'description': prompt.description,
                'published': prompt.published,
                'is_author': prompt.author == request.user
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