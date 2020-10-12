import smtplib


class SMS:
    def __init__(self, gmail_username, gmail_password):
        self.username = gmail_username
        self.password = gmail_password
        self.carriers = {
            'att': '@mms.att.net',
            'tmobile': ' @tmomail.net',
            'verizon': '@vtext.com',
            'sprint': '@page.nextel.com'
        }

    def send(self, message, number, carrier="att"):
        # Replace the number with your own, or consider using an argument\dict for multiple people.
        to_number = '{}{}'.format(number, self.carriers[carrier.lower()])

        # Establish a secure session with gmail's outgoing SMTP server using your gmail account
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(self.username, self.password)

        # Send text message through SMS gateway of destination number
        server.sendmail(self.username, to_number, message)
