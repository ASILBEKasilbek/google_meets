from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_room, name='create_room'),
    path('<uuid:room_code>/', views.get_room, name='get_room'),
    path('<uuid:room_code>/join/', views.join_room, name='join_room'),
    path('<uuid:room_code>/members/', views.room_members, name='room_members'),
    path('my-rooms/', views.my_rooms, name='my_rooms'),
]
