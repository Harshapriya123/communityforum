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
    try:
        with open(input_docs) as f:
            read_data = json.loads(f.read())
    except FileNotFoundError:
        print(f"Path '{input_docs}' does not exist.")
        return

    # Insert users
    for user_id, user_doc in read_data['users'].items():
        print(user_doc['username'])
        from pillar.api.local_auth import create_local_user
        from pillar.api.utils.authentication import find_user_in_db, upsert_user
        # create_local_user(user_doc['email'])
        if 'auth' in user_doc and user_doc['auth']:
            user_doc['id'] = user_doc['auth'][0]['user_id']
            provider = user_doc['auth'][0]['provider']
            u = find_user_in_db(user_doc, provider=provider)
            u_id, _ = upsert_user(u)
            return
    # Update users list with user._id

    # Insert posts
