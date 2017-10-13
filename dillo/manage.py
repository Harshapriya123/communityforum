import json
import logging
from flask.ext.script import Manager
from flask.ext.migrate import Migrate
from flask.ext.migrate import MigrateCommand
from application import app
from application import db
from application.modules.users.model import user_datastore
from application.modules.users.model import UserKarma
from application.modules.posts.model import Category
from application.modules.posts.model import PostType
from application.modules.admin.model import Setting

log = logging.getLogger(__name__)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


@manager.command
def setup():
    import getpass
    from flask_security.utils import encrypt_password
    print("Please input the user data for the admin (you can edit later)")
    while True:
        admin_username = raw_input('Admin username:')
        if len(admin_username) < 1:
            print ("Username is too short")
        elif user_datastore.find_user(username=admin_username):
            print ("Username already in use")
        else:
            break
    while True:
        admin_password = getpass.getpass('Admin password:')
        if len(admin_password) < 5:
            print ("Password is too short")
        else:
            break
    while True:
        admin_email = raw_input('Admin email:')
        if user_datastore.find_user(email=admin_email):
            print ("Email aready in use")
        else:
            break
    admin_role = user_datastore.find_or_create_role('admin')
    world_role = user_datastore.find_or_create_role('world')
    admin = user_datastore.create_user(
        username=admin_username,
        password=encrypt_password(admin_password),
        email=admin_email)
    db.session.commit()
    user_datastore.add_role_to_user(admin, admin_role)
    db.session.commit()
    # Add karma for the admin
    user_karma = UserKarma(
        user_id=admin.id)
    db.session.add(user_karma)
    db.session.commit()
    print("Admin user succesfully created!")
    # Add default category
    category_default = Category(
        name='News',
        url='news',
        order=0)
    db.session.add(category_default)
    db.session.commit()
    print("Added default News category")
    # Add default post types
    post_types = ['link', 'text']
    for t in post_types:
        post_type = PostType(
            name=t,
            url=t)
        db.session.add(post_type)
        db.session.commit()
        print("Added post type {0}".format(t))
    print('Congrats, Dillo was setup successfully!')


@manager.command
def runserver():
    import os
    os.environ['DEBUG'] = 'true'
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
    import config
    PORT = config.Deployment.PORT
    HOST = config.Deployment.HOST
    app.run(
        port=PORT,
        host=HOST)


@manager.command
def ensure_user_karma():
    """Workaround to assign karma to users who were created without."""
    from application.modules.users.model import User
    from application.modules.users import user_assign_karma

    for user in User.query.all():
        if not user.karma:
            log.info('Assigning karma to user {}'.format(user.id))
            user_assign_karma(user)


@manager.command
def transcend():
    from sqlalchemy import or_
    from application.modules.users.model import User, UserOauth
    from application.modules.posts.model import Post, UserPostRating, Comment, UserCommentRating

    def write_doc(docs_collections):
        with open('dillo_export.json', 'w') as outfile:
            json.dump(docs_collections, outfile, indent=4)

    def dump_users():
        # Get users
        users_collection = []
        for user in User.query.filter_by(active=1).all():
            # Attach karma
            user_doc = {
                'id': user.id,
                'full_name': u'{0} {1}'.format(user.first_name, user.last_name),
                'username': user.username,
                'email': user.email,
                'settings': None,
                'extension_props_public': {'dilo': {'karma': user.karma.value}},
                'auth': [],
            }
            # Attach auth credentials
            oauth = UserOauth.query.filter_by(user_id=user.id).all()
            for o in oauth:
                auth_doc = {
                    'provider': o.service,
                    'user_id': o.service_user_id,
                    'token': None,
                }
                user_doc['auth'].append(auth_doc)
            if user.password.startswith('$'):
                auth_doc = {
                    'provider': 'local',
                    'user_id': None,
                    'token': user.password,
                }
                user_doc['auth'].append(auth_doc)

            users_collection.append(user_doc)
            print(user_doc['username'])
        return users_collection

    # Make user mongo docs
    # Get posts

    def dump_posts():
        posts_collection = []
        for post in Post.query.filter_by(status='published').all():
            post_doc = {
                'id': post.id,
                'user': post.user_id,
                'properties': {
                    'category': post.category.name,
                    'post_type': post.post_type.name,
                    'content': post.content,
                    'rating_positive': post.rating.positive,
                    'rating_negative': post.rating.negative,
                    'status': post.status,
                    'hot': post.rating.hot,
                    'shortcode': post.uuid,
                    'slug': post.slug,
                    'picture_url': post.picture,
                    'ratings': []
                },
            }
            # Get post ratings
            ratings = UserPostRating.query.filter_by(post_id=post.id).all()
            for r in ratings:
                post_doc['properties']['ratings'].append(
                    {'user': r.user_id, 'is_positive': r.is_positive}
                )
            posts_collection.append(post_doc)
        return posts_collection

    def dump_comments():
        comments_collection = []
        for comment in Comment.query\
                .filter(or_(Comment.status == 'published', Comment.status == 'edited'))\
                .all():
            print(comment)
            comment_doc = {
                'id': comment.id,
                'user': comment.user_id,
                'post_id': comment.post_id,
                'properties': {
                    'content': comment.content,
                    'rating_positive': comment.rating.positive,
                    'rating_negative': comment.rating.negative,
                    'status': comment.status,
                    'ratings': []
                },
            }
            if comment.parent_id:
                comment_doc['parent_post'] = comment.parent_id
            ratings = UserCommentRating.query.filter_by(comment_id=comment.id).all()
            for r in ratings:
                comment_doc['properties']['ratings'].append(
                    {'user': r.user_id, 'is_positive': r.is_positive}
                )
            comments_collection.append(comment_doc)
        return comments_collection
    # Reference user and post with doc _id
    # Make comments mongo docs

    write_doc({
        'users': dump_users(),
        'posts': dump_posts(),
        'comments': dump_comments(),
    })


manager.run()
