import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
import os


def send_email(
    file_path,
    to_email,
    from_email,
    subject,
    body,
    smtp_server,
    smtp_port,
    smtp_user,
    smtp_password,
):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    part = MIMEBase("application", "octet-stream")
    with open(file_path, "rb") as file:
        part.set_payload(file.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition", f'attachment; filename="{os.path.basename(file_path)}"'
    )
    msg.attach(part)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, to_email, msg.as_string())


def send_evaluation_report_as_mail(filepath, toEmail):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = smtp_user
    to_email = toEmail
    subject = "Correlation Analysis Report"

    # Format the body with customer information
    body = "Dear Customer,\n\nPlease find attached the correlation analysis report.\n\nBest regards,\nYour Data Science Team"

    # Send the email
    send_email(
        filepath,
        to_email,
        from_email,
        subject,
        body,
        smtp_server,
        smtp_port,
        smtp_user,
        smtp_password,
    )
    print("Email sent successfully.")
