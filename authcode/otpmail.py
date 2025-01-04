import smtplib
from email.mime.text import MIMEText
from queue import Queue
from threading import Lock
import dotenv

class SMTPConnectionPool:
    def __init__(self, host, port, username, password, pool_size):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.pool_size = pool_size
        self.pool = Queue(maxsize=pool_size)
        self.lock = Lock()

        # Initialize the pool
        for _ in range(pool_size):
            connection = self.create_connection()
            self.pool.put(connection)

    def create_connection(self):
        connection = smtplib.SMTP(self.host, self.port)
        connection.set_debuglevel(1)
        connection.starttls()
        connection.login(self.username, self.password)
        return connection

    def get_connection(self):
        with self.lock:
            if self.pool.empty():
                return self._create_connection()
            return self.pool.get()

    def release_connection(self, connection):
        with self.lock:
            if self.pool.qsize() < self.pool_size:
                self.pool.put(connection)
            else:
                connection.quit()

    def close_all(self):
        while not self.pool.empty():
            connection = self.pool.get()
            connection.quit()


# Initialize a global SMTP connection pool
def initialize_pool():
    path = ".env"  # Update with the actual path to your .env file
    EMAIL_ADDRESS = dotenv.get_key(path, "EMAIL_ADDRESS")
    EMAIL_PASSWORD = dotenv.get_key(path, "EMAIL_PASSWORD")
    SMTP_SERVER = dotenv.get_key(path, "SMTP_SERVER")
    SMTP_PORT = int(dotenv.get_key(path, "SMTP_PORT"))
    return SMTPConnectionPool(SMTP_SERVER, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD, pool_size=5)


def send_mail(recipient_email, otp, pool):
    """
    Sends an email to the recipient's email address with the OTP for 2FA.

    Args:
        recipient_email (str): The email address of the recipient.
        otp (str): The one-time password to be sent for 2FA.

    Returns:
        None
    """
    path = ".env"  # Update with the actual path to your .env file
    EMAIL_ADDRESS = dotenv.get_key(path, "EMAIL_ADDRESS")

    # Get a connection from the pool
    connection = None
    try:
        connection = pool.get_connection()

        # Create the email message
        message = MIMEText(f"Your OTP for 2FA login @MAAL authentication gateway is {otp}.\n"
                           f"Please do not share this OTP with anyone.\n"
                           f"Keep visiting us\n"
                           f"Regards,\nTeam MAAL")
        message["Subject"] = "OTP for 2FA Login"
        message["From"] = EMAIL_ADDRESS
        message["To"] = recipient_email

        # Send the email
        connection.sendmail(EMAIL_ADDRESS, recipient_email, message.as_string())
    except Exception as e:
        print(f"Error sending email: {e}")
    finally:
        # Release the connection back to the pool
        if connection:
            pool.release_connection(connection)
