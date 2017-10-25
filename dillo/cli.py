"""Commandline interface for Dillo."""

import logging

from flask import current_app
from flask_script import Manager

from pillar.api.utils import authentication
from pillar.cli import manager

import dillo.setup
import dillo.api.posts.rating

log = logging.getLogger(__name__)

manager_dillo = Manager(current_app, usage="Perform Dillo operations")

manager.add_command("dillo", manager_dillo)


@manager_dillo.command
@manager_dillo.option('-r', '--replace', dest='replace', action='store_true', default=False)
def setup_for_dillo(project_url, replace=False):
    """Adds Dillo node types to the project.

    Use --replace to replace pre-existing Dillo node types
    (by default already existing Dillo node types are skipped).
    """

    authentication.force_cli_user()
    dillo.setup.setup_for_dillo(project_url, replace=replace)


@manager_dillo.command
def index_nodes_rebuild():
    """Clear all nodes, update settings and reindex all posts."""

    from dillo.api.posts.hooks import algolia_index_post_save

    nodes_index = current_app.algolia_index_nodes

    log.info('Dropping index: {}'.format(nodes_index))
    nodes_index.clear_index()
    index_nodes_update_settings()

    db = current_app.db()
    nodes_dillo_posts = db['nodes'].find({
        '_deleted': {'$ne': True},
        'node_type': 'dillo_post',
        'properties.status': 'published',
    })

    log.info('Reindexing all nodes')
    for post in nodes_dillo_posts:
        algolia_index_post_save(post)


@manager_dillo.command
def index_nodes_update_settings():
    """Configure indexing backend as required by the project"""
    nodes_index = current_app.algolia_index_nodes

    # Automatically creates index if it does not exist
    nodes_index.set_settings({
        'searchableAttributes': [
            'name',
            'content',
        ],
        'customRanking': [
            'desc(hot)',
            'desc(created)',
        ],
        'attributesForFaceting': [
            'searchable(category)',
            'project._id',
        ]
    })


@manager_dillo.command
def reset_users_karma():
    """Recalculate the users karma"""
    dillo.api.posts.rating.rebuild_karma()


@manager_dillo.command
def import_legacy(input_docs, community_name):
    import json
    from flask import g
    import dateutil.parser
    from pillar.auth import UserClass
    from eve.methods.post import post_internal
    from pillar.api.utils.authentication import force_cli_user
    from dillo.setup import _get_project
    try:
        with open(input_docs) as f:
            read_data = json.loads(f.read())
    except FileNotFoundError:
        print(f"Path '{input_docs}' does not exist.")
        return

    user_collection = current_app.db()['users']
    nodes_collection = current_app.db()['nodes']
    project = _get_project(community_name)

    force_cli_user()
    # Insert users
    for user_id, user_doc in read_data['users'].items():
        print(f'Importing user {user_doc["id"]}')
        db_user = user_collection.find_one({'email': user_doc['email']})
        if db_user:
            print('User already exists')
            user_doc['_id'] = db_user['_id']
            continue
        from pillar.api.local_auth import create_local_user
        from pillar.api.utils.authentication import find_user_in_db, upsert_user
        # create_local_user(user_doc['email'])
        provider = user_doc['auth'][0]['provider']
        if provider == 'local':
            u_id = create_local_user(user_doc['email'], 'password')
        else:
            user_doc['id'] = user_doc['auth'][0]['user_id']
            u = find_user_in_db(user_doc, provider=provider)
            u_id, _ = upsert_user(u)
        # Update users list with user._id
        user_doc['_id'] = u_id
        # Set karma
        user_collection.find_one_and_update(
            {'_id': u_id},
            {'$set': {'extension_props_public': user_doc['extension_props_public']}})
    # Insert posts
    posts_lookup = {}
    for post_id, post_doc in read_data['posts'].items():
        int_id = post_doc['id']
        print(f'Importing post {int_id}')

        db_post = nodes_collection.find_one({
            'project': project['_id'],
            'node_type': 'dillo_post',
            'properties.shortcode': post_doc['properties']['shortcode']
        })
        if db_post:
            print('Post already imported')
            posts_lookup[int_id] = db_post['_id']
            continue

        u_doc = user_collection.find_one({'_id': db_post['user']})
        u = UserClass.construct(u_doc['_id'], u_doc)
        g.current_user = u

        post_doc['project'] = project['_id']
        post_doc['node_type'] = 'dillo_post'
        post_doc['user'] = read_data['users'][str(post_doc['user'])]['_id']
        post_doc['name'] = post_doc['name'][:123]
        for r in post_doc['properties']['ratings']:
            # Swap id with _id
            r['user'] = read_data['users'][str(r['user'])]['_id']
        post_doc.pop('id', None)
        _created = post_doc.pop('_created')
        _updated = post_doc.pop('_updated', None)
        resp, _, _, _, _ = post_internal('nodes', post_doc)

        update_query = {'_created': dateutil.parser.parse(_created)}
        if _updated:
            update_query['_updated'] = dateutil.parser.parse(_updated)

        nodes_collection.find_one_and_update(
            {'_id': resp['_id']},
            {'$set': update_query})
        print(resp)
        posts_lookup[int_id] = resp['_id']

    comments_lookup = {}
    for comment_id, comment_doc in read_data['comments'].items():
        int_id = comment_doc['id']
        print(f'Importing comment {int_id}')

        db_comment = nodes_collection.find_one({
            'project': project['_id'],
            'node_type': 'comment',
            '_created': dateutil.parser.parse(comment_doc['_created'])
        })
        if db_comment:
            print('Comment already imported')
            comments_lookup[int_id] = db_comment['_id']
            continue

        user_id = read_data['users'][str(comment_doc['user'])]['_id']

        u_doc = user_collection.find_one({'_id': user_id})
        u = UserClass.construct(user_id, u_doc)
        g.current_user = u

        comment_doc['project'] = project['_id']
        comment_doc['name'] = 'Comment'
        comment_doc['node_type'] = 'comment'
        comment_doc['user'] = user_id

        parent_post = comment_doc.get('parent_post')
        try:
            if parent_post:
                parent = comments_lookup[parent_post]
            else:
                parent = posts_lookup[comment_doc['post_id']]
        except KeyError:
            # If a post does not exist, do not add comments
            continue
        comment_doc['parent'] = parent
        for r in comment_doc['properties']['ratings']:
            # Swap id with _id
            r['user'] = read_data['users'][str(r['user'])]['_id']

        content = comment_doc['properties']['content']
        if len(content) < 5:
            content = content + ' ' * (5 - len(content))
            comment_doc['properties']['content'] = content

        comment_doc.pop('id', None)
        comment_doc.pop('post_id', None)
        comment_doc.pop('parent_post', None)
        _created = comment_doc.pop('_created')
        _updated = comment_doc.pop('_updated', None)
        resp, _, _, _, _ = post_internal('nodes', comment_doc)

        update_query = {'_created': dateutil.parser.parse(_created)}
        if _updated:
            update_query['_updated'] = dateutil.parser.parse(_updated)

        nodes_collection.find_one_and_update(
            {'_id': resp['_id']},
            {'$set': update_query})

        print(resp)
        comments_lookup[int_id] = resp['_id']


@manager_dillo.command
def process_posts(community_name):
    from flask import g
    from pillar.auth import UserClass
    from dillo.api.posts.hooks import process_picture_oembed, before_replacing_post
    from dillo.setup import _get_project
    project = _get_project(community_name)

    nodes_collection = current_app.db()['nodes']
    user_collection = current_app.db()['users']
    nc = nodes_collection.find({
        'node_type': 'dillo_post',
        'properties.status': 'published',
        'project': project['_id'],
    })

    # Log in as admin user (all created files will be owned by this user)
    admin = user_collection.find_one({'username': 'admin'})
    u = UserClass.construct('CLI', admin)
    g.current_user = u

    for n in nc:
        n_id = n['_id']
        print(f'Processing node {n_id}')
        process_picture_oembed(n, n)
        before_replacing_post(n, n)
        nodes_collection.find_one_and_replace({'_id': n_id}, n)
