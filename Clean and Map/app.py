import os
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path

from flask import Flask, abort, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

PUBLIC_EXTENSIONS = {
    ".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".webp",
    ".gif", ".avif", ".svg", ".ico", ".woff", ".woff2",
}

DEFAULT_RECIPIENTS = (
    "marcostellarmultiverse@proton.me",
    "maryeka88@gmail.com",
)


@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "Index.html")


@app.get("/<path:filename>")
def public_files(filename):
    if Path(filename).suffix.lower() not in PUBLIC_EXTENSIONS:
        abort(404)
    return send_from_directory(BASE_DIR, filename)


@app.post("/contact")
def contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    country = request.form.get("country", "").strip()
    service = request.form.get("service", "").strip()
    message = request.form.get("message", "").strip()

    # Silently accept submissions caught by the honeypot.
    if request.form.get("website", "").strip():
        return confirmation_page()

    email_pattern = r"[^@\s]+@[^@\s]+\.[^@\s]+"
    header_fields = (name, email, country, service)

    valid = (
        bool(name)
        and len(name) <= 120
        and bool(re.fullmatch(email_pattern, email))
        and len(email) <= 254
        and bool(country)
        and len(country) <= 120
        and bool(service)
        and len(service) <= 100
        and bool(message)
        and len(message) <= 5000
        and all("\r" not in value and "\n" not in value for value in header_fields)
    )

    if not valid:
        return "Please check the form fields and try again.", 400

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_username = os.getenv("SMTP_USERNAME", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("CONTACT_FROM", "").strip()

    recipients_setting = os.getenv("CONTACT_TO", "")
    recipients = [
        address.strip()
        for address in recipients_setting.split(",")
        if address.strip()
    ] or list(DEFAULT_RECIPIENTS)

    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        app.logger.error("SMTP_PORT must be a valid port number.")
        return "The contact form is temporarily unavailable. Please try again later.", 503

    if not all((smtp_host, smtp_username, smtp_password, sender)):
        app.logger.error("Contact form SMTP settings are incomplete.")
        return "The contact form is temporarily unavailable. Please try again later.", 503

    email_message = EmailMessage()
    email_message["Subject"] = f"Website enquiry: {service}"
    email_message["From"] = sender
    email_message["To"] = "undisclosed-recipients:;"
    email_message["Reply-To"] = email
    email_message.set_content(
        "New Clean & Map website enquiry\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Country: {country}\n"
        f"Service: {service}\n\n"
        f"Message:\n{message}\n"
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(email_message, to_addrs=recipients)
    except (OSError, smtplib.SMTPException):
        app.logger.exception("Could not send contact form email.")
        return "We couldn't send your request. Please try again later.", 502

    return confirmation_page()


def confirmation_page():
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Request received | Clean &amp; Map</title>
      </head>
      <body style="font:16px Arial,sans-serif;max-width:620px;margin:12vh auto;padding:24px;color:#12372a">
        <h1>Thank you for getting in touch.</h1>
        <p>Your request has been received. We’ll follow up using the email address you provided.</p>
        <a href="/">Return to Clean &amp; Map</a>
      </body>
    </html>
    """


if __name__ == "__main__":
    app.run()