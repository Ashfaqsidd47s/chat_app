from django.urls import path
from . import views

urlpatterns = [
    path( "register/", views.register, name="register"),
    path( "login/", views.login, name="login"),
    path('', views.home, name='home'),
    path('chat/', views.chat, name='chat'),
    path('logout/', views.logout, name='logout'),
    path('get_or_create_conversation/<str:user_id>/', views.get_or_create_conversation, name='get_or_create_conversation'),
    path('send_message/', views.send_message, name='send_message'),
]