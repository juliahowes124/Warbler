"""SQLAlchemy models for Warbler."""

from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()


class Follow(db.Model):
    """Connection of a follower <-> followed_user."""

    __tablename__ = 'follows'

    followee = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True,
    )

    follower = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True,
    )


class Request(db.Model):
    """ follow request from sender to recipient """

    __tablename__ = 'requests'

    sender = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True
    )

    recipient = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True
    )


class Like(db.Model):
    """Connection of a message <-> user"""

    __tablename__ = 'likes'

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True,
    )

    message_id = db.Column(
        db.Integer,
        db.ForeignKey('messages.id', ondelete="cascade"),
        primary_key=True,
    )


class User(db.Model):
    """User in the system."""

    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    email = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    username = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    image_url = db.Column(
        db.Text,
        default="/static/images/default-pic.png",
    )

    header_image_url = db.Column(
        db.Text,
        default="/static/images/warbler-hero.jpg"
    )

    bio = db.Column(
        db.Text,
    )

    location = db.Column(
        db.Text,
    )

    password = db.Column(
        db.Text,
        nullable=False,
    )

    admin = db.Column(
        db.Boolean,
        default=False
    )

    is_private = db.Column(
        db.Boolean,
        default=False
    )

    messages = db.relationship('Message', order_by='Message.timestamp.desc()')

    liked_messages = db.relationship('Message', secondary="likes")

    followers = db.relationship(
        "User",
        secondary="follows",
        primaryjoin=(Follow.followee == id),
        secondaryjoin=(Follow.follower == id)
    )

    following = db.relationship(
        "User",
        secondary="follows",
        primaryjoin=(Follow.follower == id),
        secondaryjoin=(Follow.followee == id)
    )

    following_requests = db.relationship(
        "User",
        secondary="requests",
        primaryjoin=(Request.sender == id),
        secondaryjoin=(Request.recipient == id)
    )

    follower_requests = db.relationship(
        "User",
        secondary="requests",
        primaryjoin=(Request.recipient == id),
        secondaryjoin=(Request.sender == id)
    )

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"

    def is_followed_by(self, other_user):
        """Is this user followed by `other_user`?"""

        found_user_list = [user for user in self.followers if user == other_user]
        return len(found_user_list) == 1

    def is_following(self, other_user):
        """Is this user following `other_user`?"""

        found_user_list = [user for user in self.following if user == other_user]
        return len(found_user_list) == 1

    def is_pending_follow(self, other_user):
        """ Is this user waiting for other_user to accept follow request? """
        found_user_list = [user for user in self.following_requests if user == other_user]
        return len(found_user_list) == 1

    @classmethod
    def signup(cls, username, email, password, image_url, admin):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
            image_url=image_url,
            admin=admin
        )

        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.

        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If can't find matching user (or if password is wrong), returns False.
        """
        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False


class Message(db.Model):
    """An individual message ("warble")."""

    __tablename__ = 'messages'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    text = db.Column(
        db.String(140),
        nullable=False,
    )

    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow(),
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )

    user = db.relationship('User')
    likers = db.relationship('User', secondary="likes")

    def __repr__(self):
        return f"<Message #{self.id}: {self.text}, {self.user_id}>"


def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    db.app = app
    db.init_app(app)
