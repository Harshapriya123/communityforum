from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.template.defaultfilters import truncatechars
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.generic import TemplateView, ListView
from sorl.thumbnail import get_thumbnail
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from dillo.models.posts import get_trending_tags, Post, PostWithMedia
from dillo.models.events import Event
from dillo.templatetags.dillo_filters import markdown


class PostListView(TemplateView):
    template_name = 'dillo/posts_base.pug'

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        """Force the creation of CSRF cookie."""
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        session_layout = self.request.session.get('layout', 'list')
        request_layout = self.request.GET.get('layout', session_layout)  # 'list' or 'grid'
        if session_layout != request_layout:
            self.request.session['layout'] = request_layout

        context['query_url'] = reverse('embed_posts_list')
        context['layout'] = request_layout
        context['layout_switch'] = 'grid' if request_layout == 'list' else 'list'
        context['upcoming_events'] = (
            Event.objects.filter(starts_at__gt=timezone.now(), visibility='public')
            .order_by('starts_at')
            .all()
        )
        context['trending_tags'] = get_trending_tags()
        # Display processing posts only if user is authenticated
        if self.request.user.is_authenticated:
            processing_posts = Post.objects.filter(
                status='processing', user=self.request.user, visibility='public'
            )
            context['processing_posts'] = {
                'posts': [str(post.hash_id) for post in processing_posts]
            }
        return context


class PostListEmbedView(ListView):
    """List of all published posts."""

    context_object_name = 'posts'
    model = Post

    def get_queryset(self):
        # By default, show only non-hidden posts
        is_hidden = Q(is_hidden_by_moderator=False)
        # If authenticated, show hidden posts only to the post owner
        if self.request.user.is_authenticated:
            is_hidden = is_hidden | Q(is_hidden_by_moderator=True, user=self.request.user)
        # Retrieve only Posts (no Rigs or Jobs)
        return Post.objects.filter(
            is_hidden, status='published', visibility='public', postwithmedia__isnull=False,
        ).order_by('-published_at')

    def get_template_names(self):
        current_layout = self.request.session.get('layout', 'list')
        next_layout = self.request.GET.get('layout', current_layout)  # 'list' or 'grid'
        if current_layout != next_layout:
            self.request.session['layout'] = next_layout
        if next_layout == 'list':
            return ['dillo/posts_list_embed.pug']
        elif next_layout == 'grid':
            return ['dillo/posts_grid_embed.pug']

    def get_paginate_by(self, queryset):
        current_layout = self.request.session.get('layout', 'list')
        next_layout = self.request.GET.get('layout', current_layout)
        if next_layout == 'list':
            return 3
        elif next_layout == 'grid':
            return 15


class UserListEmbedView(ListView):
    """List users. Must be overridden."""

    def get_users_list(self):
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_list'] = self.get_users_list()
        return context

    template_name = 'dillo/profiles_list_embed.pug'
    paginate_by = 10


class OgData:
    """Open Graph and Twitter data.

    Used to render Open Graph info in pages.
    """

    def make_excerpt(self, description):
        description_parsed = markdown(description)
        description_sripped = strip_tags(description_parsed)
        description_truncated = truncatechars(description_sripped, 120)
        return description_truncated

    def make_thumbnail_url(self, image_field):
        if not image_field:
            return f"{settings.STATIC_URL}images/animato.png"
        thumbnail = get_thumbnail(image_field, '1280x720', crop='center', quality=80)
        return thumbnail.url

    def __init__(self, title=None, description=None, image_field=None, image_alt=None):
        self.title = title
        self.description = self.make_excerpt(description)
        self.image_url = self.make_thumbnail_url(image_field)
        self.image_alt = image_alt
