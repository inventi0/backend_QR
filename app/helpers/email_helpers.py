import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.logging_config import app_logger

def send_faq_answer_email(to_email: str, question: str, answer: str):
    """Отправка ответа на FAQ по email."""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT", "465")
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM_EMAIL", smtp_user)
    
    if not all([smtp_server, smtp_port, smtp_user, smtp_pass]):
        app_logger.warning("SMTP settings are not fully configured. Skipping email sending.")
        return
        
    try:
        msg = MIMEMultipart()
        msg['From'] = str(smtp_from)
        msg['To'] = to_email
        msg['Subject'] = "Ответ на ваш вопрос (FAQ)"
        
        body = f"Здравствуйте!\n\nВы задавали вопрос: {question}\n\nНаш ответ:\n{answer}\n\nС уважением,\nКоманда поддержки"
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        port = int(smtp_port)
        if port == 465:
            server = smtplib.SMTP_SSL(str(smtp_server), port)
        else:
            server = smtplib.SMTP(str(smtp_server), port)
            server.starttls()
            
        server.login(str(smtp_user), str(smtp_pass))
        server.sendmail(str(smtp_from), to_email, msg.as_string())
        server.quit()
        app_logger.info(f"Answer email sent to {to_email}")
    except Exception as e:
        app_logger.error(f"Failed to send email to {to_email}: {e}")
