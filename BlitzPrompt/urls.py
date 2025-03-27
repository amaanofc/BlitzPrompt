"""
URL configuration for BlitzPrompt project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from core import views  # Import your app's views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('interface/', views.gpt_interface, name='interface'),
    path('library/', views.prompt_library, name='prompt_library'),
    path('prompt/<int:prompt_id>/', views.prompt_detail, name='prompt_detail'),
    path('toggle-favorite/<int:prompt_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('publish-prompt/<int:prompt_id>/', views.publish_prompt, name='publish_prompt'),
    path('vote-prompt/<int:prompt_id>/', views.vote_prompt, name='vote_prompt'),
    path('add-comment/<int:prompt_id>/', views.add_comment, name='add_comment'),
]