from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import smtplib
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from decouple import config

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def fetch_google_sheet():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.readonly']
        credentials = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        client = gspread.authorize(credentials)
        worksheet = client.open_by_url(config('GOOGLE_SHEET_URL')).sheet1
        values = worksheet.get_all_values()
        df = pd.DataFrame(values[1:], columns=values[0])
        return df
    except Exception as e:
        print("Error fetching Google Sheet:", e)
        return None

@app.route('/')
def index():
    df = fetch_google_sheet()
    if df is None:
        flash('Error fetching Google Sheet.', 'danger')
        return render_template('index.html', events=[])
    events = df["Which event are you signing up for?"].unique().tolist()
    return render_template('index.html', events=events)

@app.route('/send_emails', methods=['POST'])
def send_emails():
    event_name = request.form['event_name']
    participant_limit = int(request.form['participant_limit'])
    sender_email = config('SENDER_EMAIL')
    sender_password = config('SENDER_PASSWORD')
    subject = request.form['subject']
    message = request.form['message']
    file_path = request.files['file_path']

    df = fetch_google_sheet()
    if df is None:
        flash('Error fetching Google Sheet.', 'danger')
        return redirect(url_for('index'))

    df = df[df["Which event are you signing up for?"] == event_name]
    email_addresses = df['Email Address'].tolist()
    email_addresses = email_addresses[:participant_limit]

    for recipient_email in email_addresses:
        send_email(sender_email, sender_password, recipient_email, subject, message, file_path)
        print(f"Email sent to {recipient_email}")

    flash(f'Emails sent to {len(email_addresses)} participants.', 'success')
    return redirect(url_for('index'))

def send_email(sender_email, sender_password, recipient_email, subject, message, file_path):
    smtp_server = "smtp.gmail.com"
    port = 587
    sender_name = "2ID HHBN UMT Office"

    msg = MIMEMultipart()
    msg['From'] = f"{sender_name} <{sender_email}>"
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'html'))

    if file_path:
        filename = file_path.filename
        file_path.save(filename)
        with open(filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {filename}")
        msg.attach(part)

    server = smtplib.SMTP(smtp_server, port)
    server.starttls()
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, recipient_email, msg.as_string())
    server.quit()

if __name__ == "__main__":
    app.run(debug=True)
