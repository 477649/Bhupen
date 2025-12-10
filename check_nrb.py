import os
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
import smtplib
from pathlib import Path

URL = "https://www.nrb.org.np/category/monthly-statistics/?department=bfr"
LAST_SEEN_FILE = Path("last_seen_month.txt")


def get_latest_title():
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Find first link whose text starts with Nepali year 20xx (e.g. 2082-06 etc.)
    for a in soup.find_all("a"):
        text = a.get_text(strip=True)
        if text.startswith("208"):
            return text

    raise RuntimeError("Could not find any month link on the page.")


def send_email(subject: str, body: str):
    to_email = os.getenv("TO_EMAIL")
    from_email = os.getenv("FROM_EMAIL")
    cc_email = os.getenv("CC_EMAIL")  # NEW: CC support
    app_password = os.getenv("APP_PASSWORD")

    if not (to_email and from_email and app_password):
        raise RuntimeError("Email environment variables are not set")

    # Prepare the email message
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    # Build recipient list
    recipients = [to_email]

    # If CC_EMAIL exists, support multiple emails separated by commas
    if cc_email:
        cc_list = [email.strip() for email in cc_email.split(",") if email.strip()]
        msg["Cc"] = ", ".join(cc_list)
        recipients.extend(cc_list)

    # Send email to all recipients
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_email, app_password)
        server.sendmail(from_email, recipients, msg.as_string())


def main():
    latest = get_latest_title()
    print("Latest title on website:", latest)

    # Read the last seen value from file (if exists)
    if LAST_SEEN_FILE.exists():
        last_seen = LAST_SEEN_FILE.read_text(encoding="utf-8").strip()
    else:
        last_seen = ""

    print("Last seen stored:", repr(last_seen))

    # ---------- ONLY SEND EMAIL WHEN NEW DATA IS FOUND ----------
    if latest != last_seen:
        print("NEW MONTH DETECTED — Sending email and updating file.")

        subject = f"NRB Monthly Statistics Updated: {latest}"
        body = (
            "A new Monthly Statistics file has been published on NRB website.\n\n"
            f"Latest entry: {latest}\n"
            f"URL: {URL}\n\n"
            "You are receiving this notification because a new month was detected."
        )

        # Send notification email
        send_email(subject, body)

        # Update the tracking file
        LAST_SEEN_FILE.write_text(latest, encoding="utf-8")

    else:
        print("No change detected. No email sent.")


if __name__ == "__main__":
    main()
