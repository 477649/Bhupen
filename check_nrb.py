import os
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
import smtplib
from pathlib import Path


# -------------------------------------------------------
# SECTION 1: Monthly Statistics (BFR)
# -------------------------------------------------------
URL_BFR = "https://www.nrb.org.np/category/monthly-statistics/?department=bfr"
FILE_BFR = Path("last_seen_month.txt")

# -------------------------------------------------------
# SECTION 2: Current Macro-Economic and Financial Situation
# -------------------------------------------------------
URL_MACRO = "https://www.nrb.org.np/category/current-macroeconomic-situation/?department=red&fy=2082-83"
FILE_MACRO = Path("last_seen_macro.txt")

# -------------------------------------------------------
# SECTION 3: Payment Systems Indicators (PSD)
# -------------------------------------------------------
URL_INDICATOR = "https://www.nrb.org.np/category/indicators/"
FILE_INDICATOR = Path("last_seen_indicator.txt")

# ------------------ COMMON FUNCTIONS -------------------

def get_latest_title_from_url(url, prefix=None):
    """
    Returns the correct 'latest' item based on website structure:
    - Macro: bottom-most month label (e.g. "Three Months (Mid-October/ Ashwin)")
    - Indicators: top-most link starting with "Payment Systems Indicators"
    - Default: first link starting with prefix (e.g. "208")
    """
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # ---------- MACRO LOGIC (newest month at bottom) ----------
    if "current-macroeconomic-situation" in url:
        month_titles = []

        # Look through all tags and pick texts that look like month labels
        for tag in soup.find_all(True):  # True = any tag
            text = tag.get_text(strip=True)
            # Very loose but robust pattern: contains "Month (" and "Mid"
            if "Month (" in text and "Mid" in text:
                month_titles.append(text)

        if month_titles:
            # newest month is always shown last in that section
            return month_titles[-1]

        # If we reach here, we didn't find any month labels
        raise RuntimeError("Macro month titles not found on page: " + url)

    # ---------- PAYMENT INDICATORS (newest at top) ----------
    if "/category/indicators" in url:
        for a in soup.find_all("a"):
            text = a.get_text(strip=True)
            if text.startswith("Payment Systems Indicators"):
                return text

    # ---------- DEFAULT LOGIC (Monthly Stats and others) ----------
    for a in soup.find_all("a"):
        text = a.get_text(strip=True)
        if prefix and text.startswith(prefix):
            return text
        if text.startswith("208"):
            return text

    raise RuntimeError(f"No matching link found on page: {url}")


def send_email(subject: str, body: str):
    to_email = os.getenv("TO_EMAIL")
    from_email = os.getenv("FROM_EMAIL")
    cc_email = os.getenv("CC_EMAIL")
    app_password = os.getenv("APP_PASSWORD")

    if not (to_email and from_email and app_password):
        raise RuntimeError("Email environment variables missing")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    recipients = [to_email]

    # CC support
    if cc_email:
        cc_list = [x.strip() for x in cc_email.split(",") if x.strip()]
        msg["Cc"] = ", ".join(cc_list)
        recipients.extend(cc_list)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_email, app_password)
        server.sendmail(from_email, recipients, msg.as_string())


def check_section(url, file_path, section_name, prefix=None):
    print(f"\nChecking: {section_name}")

    latest = get_latest_title_from_url(url, prefix)
    print("Latest found:", latest)

    if file_path.exists():
        last_seen = file_path.read_text(encoding="utf-8").strip()
    else:
        last_seen = ""

    print("Last seen:", repr(last_seen))

    if latest != last_seen:
        print("UPDATE FOUND — Sending email!")

        subject = f"NRB Update Detected: {section_name}"
        body = (
            f"A new update was detected in:\n\n"
            f"{section_name}\n"
            f"Latest Entry: {latest}\n\n"
            f"Source: {url}\n\n"
            f"This message is auto-generated."
        )

        send_email(subject, body)
        file_path.write_text(latest, encoding="utf-8")

    else:
        print("No change detected.")


# ------------------ MAIN -------------------

def main():
    # SECTION 1 – Monthly statistics (top item, starts with 208)
    check_section(URL_BFR, FILE_BFR, "Monthly Statistics (BFR)", prefix="208")

    # SECTION 2 – Macro (latest month at bottom; handled in get_latest_title_from_url)
    check_section(URL_MACRO, FILE_MACRO, "Macro-Economic & Financial Situation")

    # SECTION 3 – Payment indicators (top "Payment Systems Indicators..." item)
    check_section(URL_INDICATOR, FILE_INDICATOR, "Payment Systems Indicators")


if __name__ == "__main__":
    main()
