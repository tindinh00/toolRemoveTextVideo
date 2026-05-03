import string
import random
import requests

def get_random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

class MailTM:
    def __init__(self):
        self.session = requests.Session()
        self.domain = self.get_domain()
        self.address = f"{get_random_string()}@{self.domain}"
        self.password = get_random_string()
        self.token = None
        self.create_account()
        
    def get_domain(self):
        res = self.session.get("https://api.mail.tm/domains").json()
        return res["hydra:member"][0]["domain"]
        
    def create_account(self):
        data = {"address": self.address, "password": self.password}
        self.session.post("https://api.mail.tm/accounts", json=data)
        
        res = self.session.post("https://api.mail.tm/token", json=data).json()
        self.token = res["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
    def check_mailbox(self):
        res = self.session.get("https://api.mail.tm/messages").json()
        return res.get("hydra:member", [])
        
    def read_email(self, msg_id):
        res = self.session.get(f"https://api.mail.tm/messages/{msg_id}").json()
        return res
