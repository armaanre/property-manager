# inbox.py

import imaplib
import email
from email.header import decode_header
import logging

logger = logging.getLogger(__name__)

class InboxConnector:
    def __init__(self, host: str, username: str, password: str, mailbox: str = "INBOX"):
        self.host = host
        self.username = username
        self.password = password
        self.mailbox = mailbox
        self.conn: imaplib.IMAP4_SSL | None = None

    def connect(self):
        """Establishes an SSL IMAP connection and logs in."""
        logger.info("Connecting to IMAP server %s", self.host)
        self.conn = imaplib.IMAP4_SSL(self.host)
        self.conn.login(self.username, self.password)
        self.conn.select(self.mailbox)
        logger.info("Logged in as %s and selected mailbox %s", self.username, self.mailbox)

    def fetch_unread(self, limit: int = 10):
        assert self.conn, "Must call connect() first"
        # Search for unseen messages
        status, data = self.conn.search(None, 'UNSEEN')
        if status != 'OK':
            logger.error("Failed to search inbox: %s", status)
            return []

        uids = data[0].split()[:limit]
        messages = []

        for uid in uids:
            # Fetch the RFC822 message
            status, msg_data = self.conn.fetch(uid, '(RFC822)')
            if status != 'OK':
                logger.warning("Failed to fetch message UID %s: %s", uid, status)
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Decode headers
            subject, encoding = decode_header(msg.get("Subject"))[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8", errors="replace")

            from_ = msg.get("From")
            date_ = msg.get("Date")

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = part.get("Content-Disposition", "")
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        charset = part.get_content_charset() or "utf-8"
                        body += part.get_payload(decode=True).decode(charset, errors="replace")
            else:
                charset = msg.get_content_charset() or "utf-8"
                body = msg.get_payload(decode=True).decode(charset, errors="replace")

            messages.append({
                "uid": uid.decode(),
                "sender": from_,
                "subject": subject,
                "date": date_,
                "body": body.strip()
            })

            # Mark as read
            self.conn.store(uid, '+FLAGS', '\\Seen')

        return messages

    def logout(self):
        if self.conn:
            self.conn.close()
            self.conn.logout()
            logger.info("Logged out from IMAP server")
