from django.core.management.base import BaseCommand
from api.models import UserMaster
from django.contrib.auth.hashers import Argon2PasswordHasher

class Command(BaseCommand):
    help = 'Create admin user'

    def handle(self, *args, **kwargs):
        email = input("Enter email-id for Admin :- ")
        password = input("Enter password for Admin :- ")

        hasher=Argon2PasswordHasher()
        hashed_password=hasher.encode(password,hasher.salt())

        if not UserMaster.objects.filter(email=email).exists():
            # Create the admin user
            admin_user = UserMaster.objects.create(
                email=email,
                password=hashed_password,
                usertype="Admin",
                status="Active",  # Set status to 'Active'
            )

            # Self-reference: set created_by to its own ID
            admin_user.created_by = admin_user
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"Admin user created with email: {email}"))
        else:
            self.stdout.write(self.style.WARNING("Admin user already exists."))
