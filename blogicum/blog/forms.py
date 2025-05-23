from django import forms
from django.contrib.auth import get_user_model

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        exclude = ('author',)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)


class UserEditForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('first_name',
                  'last_name',
                  'last_login',
                  'email',
                  )
