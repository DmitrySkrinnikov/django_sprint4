from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import (
    View,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)

from django.db.models import Count, Manager, QuerySet
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Post, Category, Comment, User
from .forms import UserEditForm, CommentForm, PostForm


def get_filtered_posts(manager: Manager,
                       only_published: bool = True,
                       ban_delayed: bool = True,
                       **conditions) -> QuerySet:
    if ban_delayed:
        conditions['pub_date__date__lt'] = timezone.now()
    if only_published:
        conditions['is_published'] = True

    return manager.filter(
        **conditions,
    ).select_related(
        'author',
        'location',
        'category',
    ).annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')


class PostMixin:
    model = Post
    pk_url_kwarg = 'post_id'
    ordering = '-pub_date'
    paginate_by = 10


class PostRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(
                reverse(
                    'blog:post_detail',
                    kwargs={'post_id': self.kwargs['post_id']}
                )
            )

        post = self.get_object()
        if post.author != request.user:
            return HttpResponseRedirect(
                reverse(
                    'blog:post_detail',
                    kwargs={'post_id': self.kwargs['post_id']}
                )
            )
        return super().dispatch(request, *args, **kwargs)


class CommentMixin(LoginRequiredMixin):
    model = Comment
    form_class = CommentForm
    pk_url_kwarg = 'comment_id'
    template_name = 'blog/comment.html'

    def get_post(self):
        return get_object_or_404(Post, pk=self.kwargs['post_id'])

    def form_valid(self, form):
        form.instance.post = self.get_post()
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        ) + '#comments'


class CommentRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        сomment = self.get_object()
        if сomment.author != request.user:
            return HttpResponseRedirect(
                reverse(
                    'blog:post_detail',
                    kwargs={'post_id': self.kwargs['post_id']}
                )
            )
        return super().dispatch(request, *args, **kwargs)


class PostListView(PostMixin, ListView):
    template_name = 'blog/index.html'
    queryset = get_filtered_posts(Post.objects, category__is_published=True)


class PostDetailView(PostMixin, DetailView):
    template_name = 'blog/detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comments.order_by('created_at')
        context['form'] = CommentForm()
        return context

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if not post.is_published and (not request.user.is_authenticated
                                      or request.user != post.author):
            raise Http404("Пост не найден.")
        return super().dispatch(request, *args, **kwargs)


class PostCreateView(LoginRequiredMixin, PostMixin, CreateView):
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username},
        )


class PostUpdateView(PostRequiredMixin, PostCreateView, UpdateView):
    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']},
        )


class PostDeleteView(PostRequiredMixin, PostCreateView, DeleteView):
    pass


class CategoryPostsListView(PostListView):
    template_name = 'blog/category.html'

    def get_queryset(self):
        category_slug = self.kwargs.get('category')
        self.category = get_object_or_404(
            Category,
            slug=category_slug,
            is_published=True,
        )
        return get_filtered_posts(self.category.posts)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class CommentCreateView(CommentMixin, CreateView):
    pass


class CommentUpdateView(CommentRequiredMixin, CommentMixin, UpdateView):
    pass


class CommentDeleteView(CommentRequiredMixin, CommentMixin, DeleteView):
    pass


class PostView(View):

    def get(self, request, *args, **kwargs):
        view = PostDetailView.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = CommentCreateView.as_view()
        return view(request, *args, **kwargs)


class UserProfilelView(PostListView):
    template_name = 'blog/profile.html'

    def dispatch(self, request, *args, **kwargs):
        self.profile_user = get_object_or_404(
            User,
            username=self.kwargs['username']
        )
        self.is_owner = (request.user.is_authenticated
                         and (request.user == self.profile_user)
                         )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['profile'] = self.profile_user
        return context_data

    def get_queryset(self):
        if self.is_owner:
            return get_filtered_posts(
                Post.objects,
                author__username=self.kwargs['username'],
                only_published=False,
                ban_delayed=False
            )
        else:
            return get_filtered_posts(
                Post.objects,
                author__username=self.kwargs['username']
            )


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserEditForm
    template_name = 'blog/user.html'

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.object.username}
        )
