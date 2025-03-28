from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('interface/', views.gpt_interface, name='interface'),
    path('library/', views.prompt_library, name='prompt_library'),
    path('prompt/<int:prompt_id>/', views.prompt_detail, name='prompt_detail'),
    path('toggle-favorite/<int:prompt_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('publish-prompt/<int:prompt_id>/', views.publish_prompt, name='publish_prompt'),
    path('delete-prompt/<int:prompt_id>/', views.delete_prompt, name='delete_prompt'),
    path('add-comment/<int:prompt_id>/', views.add_comment, name='add_comment'),
    path('delete-comment/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('profile/', views.profile, name='profile'),
    path('favorites/', views.favorites, name='favorites'),
    path('create-prompt/', views.create_prompt, name='create_prompt'),
    path('api/prompt/<int:prompt_id>/', views.get_prompt_info, name='get_prompt_info'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/prompts/<int:prompt_id>/', views.prompt_api, name='prompt_api'),
    path('api/conversations/', views.conversations_api, name='conversations_api'),
    path('api/conversations/<int:conversation_id>/', views.conversation_detail_api, name='conversation_detail_api'),
    path('api/rate-limits/', views.rate_limits_api, name='rate_limits_api'),
    path('api/vote/', views.api_vote, name='api_vote'),
    
    # Priming prompts management
    path('api/priming-prompts/', views.priming_prompts_api, name='priming_prompts_api'),
    path('api/priming-prompts/update/', views.update_priming_prompts, name='update_priming_prompts'),
    path('api/priming-prompts/toggle/<int:prompt_id>/', views.toggle_priming_prompt, name='toggle_priming_prompt'),
] 