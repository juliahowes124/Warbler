"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follow
from sqlalchemy.exc import IntegrityError
from flask_bcrypt import Bcrypt

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()
bcrypt = Bcrypt()

class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        db.session.rollback()

        User.query.delete()
        Message.query.delete()
        Follow.query.delete()

        u1 = User(
            email="test@test.com",
            username="testuser1",
            password= bcrypt.generate_password_hash('HASHED PASSWORD').decode('UTF-8')
        )

        u2 = User(
            email="test@gmail.com",
            username="testuser2",
            password=bcrypt.generate_password_hash('PASSWORD').decode('UTF-8')
        )

        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()

        self.client = app.test_client()
        self.u1 = User.query.all()[0]
        self.u2 = User.query.all()[1]
    

    def test_user_model(self):
        """Does basic model work?"""

        # User should have no messages & no followers
        self.assertEqual(len(self.u1.messages), 0)
        self.assertEqual(len(self.u1.followers), 0)

    def test__repr__(self):
        """Does the repr method work as expected?"""

        response = self.u1.__repr__()

        self.assertEqual(response, f"<User #{self.u1.id}: {self.u1.username}, {self.u1.email}>")
    

    def test_is_following(self):
        """Is this user following other user?"""
      
        follow = Follow(followee=self.u2.id, follower=self.u1.id)
        db.session.add(follow)
        db.session.commit()

        self.assertEqual(self.u1.is_following(self.u2), True)
        self.assertEqual(self.u2.is_following(self.u1), False)
    
    
    def test_is_followed_by(self):
        """Is this user followed by other user?"""
        follow = Follow(followee=self.u2.id, follower=self.u1.id)
        db.session.add(follow)
        db.session.commit()

        self.assertEqual(self.u2.is_followed_by(self.u1), True)
        self.assertEqual(self.u1.is_followed_by(self.u2), False)


    def test_signup(self):
        """successfully signs a user up"""
        response = User.signup("user3","user@hotmail.com,","pword", "google.com", False)
        db.session.add(response)
        db.session.commit()

        self.assertIsInstance(response, User)
        self.assertEqual(len(User.query.all()), 3)
        self.assertEqual(response, User.query.all()[2])
    
    def test_invalid_email_signup(self):
        """tests invalid signup data"""
        bad_response = User.signup("user3", None, "pword", "google.com", False)
        
        db.session.add(bad_response)

        with self.assertRaises(IntegrityError):
            db.session.commit()

        db.session.rollback()
        #tests for duplicate email
        bad_response2 = User.signup("testuser1", "user3@gmail.com", "pword", "google.com", False)
        
        db.session.add(bad_response2)

        with self.assertRaises(IntegrityError):
            db.session.commit()
    
    def test_authenticate(self):
        """tests for successful return of a user when given a valid username and password"""

        response = User.authenticate(self.u1.username, "HASHED PASSWORD")

        self.assertIsInstance(response, User)
      
        bad_response = User.authenticate(self.u1.username, "WRONG PASSWORD")

        self.assertFalse(bad_response)
        
        bad_username = User.authenticate("wrong_username", "HASHED PASSWORD")

        self.assertFalse(bad_username)


    





        



