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
def import_legacy(input_docs):
    import json
    from eve.methods.post import post_internal
    from pillar.api.utils.authentication import force_cli_user
    from dillo.setup import _get_project
    try:
        with open(input_docs) as f:
            read_data = json.loads(f.read())
    except FileNotFoundError:
        print(f"Path '{input_docs}' does not exist.")
        return

    project = _get_project('today')

    # Insert users
    for user_id, user_doc in read_data['users'].items():
        print(user_doc['username'])
        from pillar.api.local_auth import create_local_user
        from pillar.api.utils.authentication import find_user_in_db, upsert_user
        # create_local_user(user_doc['email'])
        if 'auth' in user_doc and user_doc['auth']:
            provider = user_doc['auth'][0]['provider']
            if provider == 'local':
                u_id = create_local_user(user_doc['email'], 'password')
            else:
                user_doc['id'] = user_doc['auth'][0]['user_id']
                u = find_user_in_db(user_doc, provider=provider)
                u_id, _ = upsert_user(u)
            # Update users list with user._id
            user_doc['_id'] = u_id
    print(read_data['users'])
    # Insert posts
    force_cli_user()
    for post_id, post_doc in read_data['posts'].items():
        print(post_doc['id'])
        post_doc['project'] = project['_id']
        post_doc['node_type'] = 'dillo_post'
        post_doc['user'] = read_data['users'][str(post_doc['user'])]['_id']
        for r in post_doc['properties']['ratings']:
            # Swap id with _id
            r['user'] = read_data['users'][str(r['user'])]['_id']
        post_doc.pop('id', None)
        post_internal('nodes', post_doc)


@manager_dillo.command
def process_posts():
    from flask import g
    from pillar.auth import UserClass
    from dillo.api.posts.hooks import process_picture_oembed, before_replacing_post
    nodes_collection = current_app.db()['nodes']
    user_collection = current_app.db()['users']
    nc = nodes_collection.find({
        'node_type': 'dillo_post',
        'properties.status': 'published',
    })

    # Log in as admin user (all created files will be owned by this user)
    admin = user_collection.find_one({'username': 'admin'})
    u = UserClass.construct('CLI', admin)
    g.current_user = u

    for n in nc:
        process_picture_oembed(n, n)
        before_replacing_post(n, n)
        nodes_collection.find_one_and_replace({'_id': n['_id']}, n)
