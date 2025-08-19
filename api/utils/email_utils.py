from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def send_registration_email(user):
    """
    Sends a registration confirmation email with OTP to the user.
    Includes both plain text and HTML versions.
    """
    subject = f"Welcome {user.name_for_email} to UniProject Portal!"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [user.email]

    context = {"user": user}

    # Render plain text + HTML templates
    text_content = render_to_string("emails/registration_email.txt", context)
    html_content = render_to_string("emails/registration_email.html", context)

    # Create the email with both formats
    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    msg.attach_alternative(html_content, "text/html")

    try:
        msg.send()
        return True
    except Exception as e:
        print(f"Email send failed: {str(e)}")
        return False
