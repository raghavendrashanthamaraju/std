from django.contrib import admin
from .models import Profile,Post,Comment,Contact


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'date_of_birth', 'photo']
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'body']
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'body']
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['user_from', 'user_to']
