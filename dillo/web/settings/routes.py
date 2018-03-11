import logging
import bson
from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from pillarsdk import User, exceptions as sdk_exceptions
from pillar.web import system_util
from pillar.web.settings import blueprint as blueprint_settings
from dillo.web.settings.forms import LinksListForm
from dillo.api.users import update_links

log = logging.getLogger(__name__)


@blueprint_settings.route('/links', methods=['GET', 'POST'])
@login_required
def links():
    """Links settings.
    """
    api = system_util.pillar_api()
    user = User.find(current_user.objectid, api=api)

    form = LinksListForm()

    if form.validate_on_submit():
        user_links = []
        for f in form.links:
            user_links.append({
                'name': f.data['name'],
                'url': f.data['url']})
        # Update user properties
        update_links(bson.ObjectId(current_user.objectid), user_links)

        flash("Profile updated", 'success')
        # Clear the list entries before populating it with the new links
        form.links.entries = []

        # If we deleted all links (can only happen via direct POST request)
        if len(user_links) == 0:
            user_links = [{'name': None, 'url': None}]

        for link in user_links:
            form.links.append_entry(link)

    # If the form fails to validate, do not update any field
    elif form.errors:
        # Handle the specific case of when we have the last link in the list.
        # In this case we will ignore the errors and assign an empty link.
        if 'links' in form.errors and len(form.links) == 1:
            errors = form.errors['links'][0]
            if 'name' in errors and 'url' in errors:
                update_links(bson.ObjectId(current_user.objectid), [{'name': None, 'url': None}])
                return redirect(url_for('settings.links'))
        for e, v in form.errors.items():
            log.debug("Error validating field %s" % e)
    else:
        # Read user properties
        if 'links' in user['extension_props_public']['dillo'] and \
                len(user['extension_props_public']['dillo']['links']) > 0:
            links = user['extension_props_public']['dillo']['links']
        else:
            links = [{'name': None, 'url': None}]
        for link in links:
            form.links.append_entry(link)

    return render_template('users/settings/links.html', form=form, title='emails')