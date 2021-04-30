import os

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from functools import wraps

from forms import UserAddForm, LoginForm, MessageForm, UserEditForm
from models import db, connect_db, User, Message, Like, Request
from admin import ADMINPASSWORD

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL_FIXED', 'postgresql:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# User signup/login/logout

def check_authenticated(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        if not g.user:
            flash("Access unauthorized.", "danger")
            return redirect("/")
        return func(*args, **kwargs)
    return wrap


def check_correct_user_or_admin(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        if not g.user.is_admin and kwargs.get("user_id") != g.user.id:
            flash("Access unauthorized.", "danger")
            return redirect("/")
        return func(*args, **kwargs)
    return wrap


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""
    g.form = MessageForm()

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
                is_admin=form.admin_password.data == ADMINPASSWORD 
            )
            db.session.add(user)
            db.session.commit()

        except IntegrityError:
            flash("Username already exists!", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)
    
        if user:
            do_login(user)
            flash(f"Welcome, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""
    do_logout()
    flash("Logged out.", "success")

    return redirect("/login")

##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    is_self = g.user and user.id == g.user.id
    is_following = g.user and g.user.is_following(user)
    is_public = not user.is_private
    is_admin = g.user.is_admin
    can_view = is_self or is_following or is_public or is_admin

    return render_template('users/show.html', user=user, can_view=can_view)
    

@app.route('/users/<int:user_id>/following')
@check_authenticated
def show_following(user_id):
    """Show list of people this user is following."""

    user = User.query.get_or_404(user_id)
    is_self = g.user and user.id == g.user.id
    is_following = g.user and g.user.is_following(user)
    is_public = user.is_private

    if not is_self and not is_following and not is_public:
        flash("Not authorized!", "danger")
        return redirect(f"/users/{user_id}")

    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""
    user = User.query.get_or_404(user_id)

    is_self = g.user and user.id == g.user.id
    is_following = g.user and g.user.is_following(user)
    is_public = user.is_private

    if not is_self and not is_following and not is_public:
        flash("Not authorized!", "danger")
        return redirect(f"/users/{user_id}")

    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
@check_authenticated
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    followed_user = User.query.get_or_404(follow_id)
    
    if followed_user.is_private:
        g.user.following_requests.append(followed_user)
        db.session.commit()
        return redirect(f"/users/{follow_id}")

    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
@check_authenticated
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/<int:user_id>/profile', methods=["GET", "POST"])
@check_authenticated
@check_correct_user_or_admin
def profile(user_id):
    """Update profile for current user."""
    user = g.user
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        user = User.authenticate(user.username, form.password.data)
        if user:
            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data or None
            user.header_image_url = form.header_image_url.data or None
            user.bio = form.bio.data
            user.is_private = form.is_private.data
            user.is_admin = form.admin_password.data == ADMINPASSWORD

            db.session.commit()

            return redirect(f"/users/{user.id}")
        else:
            flash("Invalid username/password")

    return render_template("/users/edit.html", form=form)


@app.route('/users/<int:user_id>/delete', methods=["POST"])
@check_authenticated
@check_correct_user_or_admin
def delete_user(user_id):
    """Delete user."""
    user = User.query.get_or_404(user_id)

    if g.user.id == user.id:
        do_logout()

    db.session.delete(user)
    db.session.commit()

    return redirect("/signup")


@app.route('/notifications')
@check_authenticated
def show_notifications():
    return render_template('users/notifications.html', user=g.user)  

##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["POST"])
@check_authenticated
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""
    msg = Message.query.get(message_id)

    is_self = g.user and msg.user.id == g.user.id
    is_following = g.user and g.user.is_following(msg.user)
    is_public = msg.user.is_private
    is_admin = g.user.is_admin

    if not is_self and not is_following and not is_public and not is_admin:
        flash("Not authorized!", "danger")
        return redirect('/')

    return render_template('messages/show.html', message=msg)


@app.route('/users/<int:user_id>/messages/<int:message_id>/delete', methods=["POST"])
@check_authenticated
@check_correct_user_or_admin
def messages_destroy(user_id, message_id):
    """Delete a message."""

    msg = Message.query.get(message_id)

    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


@app.route('/messages/<int:message_id>/likes', methods=['POST'])
@check_authenticated
def add_liked_message(message_id):
    """ Like a messages """

    message = Message.query.get(message_id)

    if message.user.id == g.user.id:
        flash("You can't like your own messages!", "danger")
        return redirect("/")

    if message in g.user.liked_messages:
        g.user.liked_messages.remove(message)
        db.session.commit()
    else:
        g.user.liked_messages.append(message)
        db.session.commit()
    
    return redirect('/')


@app.route('/users/<int:user_id>/likes')
def show_liked_messages(user_id):
    user = User.query.get_or_404(user_id)

    is_self = g.user and user.id == g.user.id
    is_following = g.user and g.user.is_following(user)
    is_public = user.is_private
    is_admin = g.user.is_admin

    if not is_self and not is_following and not is_public and not is_admin:
        flash("Not authorized!", "danger")
        return redirect('/')

    return render_template('users/likes.html', user=user)   


@app.route("/requests/accept/<int:sender_id>", methods=["POST"])
@check_authenticated
def accept_follow_request(sender_id):
    sender = User.query.get_or_404(sender_id)
    req = Request.query.get_or_404([sender_id, g.user.id])
    g.user.followers.append(sender)
    db.session.delete(req)
    db.session.commit()
    return redirect("/notifications")


@app.route("/requests/delete/<int:sender_id>", methods=["POST"])
@check_authenticated
def delete_follow_request(sender_id):
    req = Request.query.get_or_404([sender_id, g.user.id])

    db.session.delete(req)
    db.session.commit()

    return redirect("/notifications")



##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        user_id_to_display = [user.id for user in g.user.following]
        user_id_to_display.append(g.user.id)
        messages = (Message
                    .query
                    .filter(Message.user_id.in_(user_id_to_display))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        return render_template('home.html', messages=messages)

    else:
        return render_template('home-anon.html')


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response


@app.errorhandler(404)
def error_handler404(e):
    return render_template('404.html')
