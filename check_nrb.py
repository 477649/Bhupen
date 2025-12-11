import os
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
import smtplib
from pathlib import Path


# -------------------------------------------------------
# SECTION 1 (Original): Monthly Statistics (BFR)
# -------------------------------------------------------
URL_BFR = "https://www.nrb.org.np/category/monthly-statistics/?department=bfr"
FILE_BFR = Path("last_seen_month.txt")


# -------------------------------------------------------
# SECTION 2: Current Macro-Economic and Financial Situation
# -------------------------------------------------------
URL_MACRO = "https://www.nrb.org.np/category/current-macroeconomic-situation/?department=red&fy=2082-83"
FILE_MACRO = Path("last_seen_macro.txt")


# -------------------------------------------------------
# SECTION 3: Digital Indicators (PSD)
# -------------------------------------------------------
URL_INDICATOR = "https://www.nrb.org.np/departments/psd/#-indicators-"
FILE_INDICATOR = Path("last_seen_indicator.txt")



# ------------------ COMMON FUNCTIONS -------------------

def get_latest_title_from_url(url, prefix=None):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Read <a> tags
    for a in soup.find_all("a"):
        text = a.get_text(strip=True)

        # If prefix provided, match it
        if prefix:
            if text.startswith(prefix):
                return text

        # Default rule (Nepali date starting with 208X)
        if text.startswith("208"):
            return text

    raise RuntimeError("No matching link found on page: " + url)



def send_email(subject: str, body: str):
    to_email = os.getenv("TO_EMAIL")
    from_email = os.getenv("FROM_EMAIL")
    cc_email = os.getenv("CC_EMAIL")  # CC support
    app_password = os.getenv("APP_PASSWORD")

    if not (to_email and from_email and app_password):
        raise RuntimeError("Email environment variables are not set")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    recipients = [to_email]

    # CC support for multiple emails
    if cc_email:
        cc_list = [email.strip() for email in cc_email.split(",") if email.strip()]
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
        print("NEW UPDATE FOUND — Sending email!")

        subject = f"NRB Update Detected in {section_name}"
        body = (
            f"A new update has been detected in:\n\n"
            f"{section_name}\n"
            f"Latest Entry: {latest}\n\n"
            f"URL: {url}\n\n"
            "You are receiving this notification because new data was found."
        )

        send_email(subject, body)
        file_path.write_text(latest, encoding="utf-8")
    else:
        print("No change detected.")




# ------------------ MAIN RUN -------------------

def main():

    # SECTION 1 — Monthly Statistics
    check_section(URL_BFR, FILE_BFR, "Monthly Statistics (BFR)", prefix="208")

    # SECTION 2 — Current Macro-Economic & Financial Situation
    check_section(URL_MACRO, FILE_MACRO, "Current Macro-Economic & Financial Situation",
                  prefix="Current")

    # SECTION 3 — Digital Indicators
    check_section(URL_INDICATOR, FILE_INDICATOR, "Digital Payment Indicators",
                  prefix="")  # detects first <a> link



if __name__ == "__main__":
    main()
