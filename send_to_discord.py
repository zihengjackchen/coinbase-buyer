from discord import SyncWebhook
import config

webhook = SyncWebhook.from_url(config.WEBHOOK_URL)

def send_to_discord(message):
    webhook.send(message)   
    print(message)

def test():
    webhook.send("Hello World")