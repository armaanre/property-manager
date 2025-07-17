# sender.py

import smtplib
import logging
import time
from email.message import EmailMessage
from typing import List, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

class EmailSender:
    """
    Simple SMTP client for sending plain-text emails.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        :param smtp_host: e.g. "smtp.gmail.com"
        :param smtp_port: e.g. 465 for SSL, 587 for STARTTLS
        :param username: SMTP login (also used as default From address)
        :param password: SMTP password or app-specific token
        :param use_ssl:  If True, uses SMTP_SSL; otherwise, uses STARTTLS.
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        from_addr: Optional[str] = None,
        cc: Optional[List[str]] = None
    ) -> None:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"]    = from_addr or self.username
        msg["To"]      = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)

        # Full list of recipients for send_message()
        recipients = to + (cc if cc else [])
        for attempt in range(1, self.max_retries + 1):
            try:
                smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
                smtp.login(self.username, self.password)
                smtp.send_message(msg, from_addr=msg["From"], to_addrs=recipients)
                smtp.quit()
                
                logger.info(
                        "Email sent to %s (attempt %d)",
                        recipients, attempt
                    )
                return
            except smtplib.SMTPException as e:
                logger.warning(
                    "Attempt %d/%d failed to send email to %s: %s",
                    attempt, self.max_retries, recipients, e
                )
            except Exception as e:
                logger.error(
                    "Unexpected error on attempt %d sending to %s: %s",
                    attempt, recipients, e, exc_info=True
                )

            # if not last attempt, wait before retrying
            if attempt < self.max_retries:
                backoff = self.retry_delay * (2 ** (attempt - 1))
                logger.info("Waiting %.1f seconds before retrying...", backoff)
                time.sleep(backoff)

        # All retries failed
        logger.error(
            "All %d attempts to send email to %s have failed.",
            self.max_retries, recipients
        )


