from application.modules.posts.model import Post
from application.modules.posts.model import PostType
from application.modules.posts.model import Category
from application.modules.posts.model import Comment
from application.modules.admin import *


class PostView(CustomModelView):
    column_searchable_list = ('title',)
    column_list = ('title', 'uuid', 'creation_date')
    form_overrides = dict(content=CKTextAreaField)
    create_template = 'admin/contents/create.html'
    edit_template = 'admin/contents/edit.html'


class PostTypeView(CustomModelView):
    column_searchable_list = ('name',)
    column_list = ('name', 'url')
    form_excluded_columns = ('post',)


class CategoryView(CustomModelView):
    column_searchable_list = ('name',)
    column_list = ('name', 'url')
    form_excluded_columns = ('post',)


class CommentView(CustomModelView):
    column_list = ('uuid', 'post.title', 'user.email')
    form_excluded_columns = ('user',)
    form_overrides = dict(content=CKTextAreaField)
    create_template = 'admin/contents/create.html'
    edit_template = 'admin/contents/edit.html'


backend.add_view(PostView(Post, db.session, name='Posts', url='posts'))
backend.add_view(PostTypeView(PostType, db.session, name='PostType',
                              url='post-types'))
backend.add_view(CategoryView(Category, db.session, name='Categories',
                              url='categories'))
backend.add_view(CommentView(Comment, db.session, name='Comments',
                             url='comments'))
