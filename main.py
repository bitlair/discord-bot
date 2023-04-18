#!/usr/bin/env python3

# Bitlair HobbyBot

from time import sleep
from string import Template
from discord import Intents
from discord.ext import commands
from discord_webhook import DiscordWebhook,DiscordEmbed
import datetime
import pytz
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
import os

# hunter2
token = os.getenv('DISCORD_TOKEN')
webhook_url = ""
description = 'Bitlair Bot'
state_template = Template('$topic is now $state')
timezone = pytz.timezone('Europe/Amsterdam')

# Discord bot stuff
intents = Intents.default()
intents.message_content = True
intents.members = True
HobbyBot = commands.Bot(command_prefix='!', description=description, intents=intents)


# Define bot commands
@HobbyBot.event
async def on_ready():
    print(f'Logged in as {HobbyBot.user} (ID: {HobbyBot.user.id})')

# !state 
@HobbyBot.command(description='Bitlair Space State')
async def state(ctx):
    async with ctx.typing():
        spaceState = subscribe.simple("bitlair/state/bitlair", hostname="bitlair.nl").payload.decode()
        if spaceState == "open":
            await ctx.send("Bitlair is OPEN! :sunglasses:")
        elif spaceState == "closed":
            await ctx.send("Bitlair is closed :pensive:")

# !co2 
@HobbyBot.command(description='co2 levels')
async def co2(ctx):
    async with ctx.typing():
        hoofdruimte = subscribe.simple("bitlair/climate/hoofdruimte_ingang/co2_ppm", hostname="bitlair.nl").payload.decode()
        werkplaats = subscribe.simple("bitlair/climate/werkplaats/co2_ppm", hostname="bitlair.nl").payload.decode()
        await ctx.send("Hoofdruimte: " + hoofdruimte + " ppm\nWerkplaats: " + werkplaats + " ppm")
# !temp 
@HobbyBot.command(description='Temperature')
async def temp(ctx):
    async with ctx.typing():
        hoofdruimte = subscribe.simple("bitlair/climate/hoofdruimte_ingang/temperature_c", hostname="bitlair.nl").payload.decode()
        werkplaats = subscribe.simple("bitlair/climate/werkplaats/temperature_c", hostname="bitlair.nl").payload.decode()
        await ctx.send("Hoofdruimte: " + hoofdruimte + "°C\nWerkplaats: " + werkplaats + "°C")

# !humid
@HobbyBot.command(description='Humidity')
async def humid(ctx):
    async with ctx.typing():
        hoofdruimte = subscribe.simple("bitlair/climate/hoofdruimte_ingang/humidity_pct", hostname="bitlair.nl").payload.decode()
        werkplaats = subscribe.simple("bitlair/climate/werkplaats/humidity_pct", hostname="bitlair.nl").payload.decode()
        await ctx.send("Hoofdruimte: " + hoofdruimte + " pct\nWerkplaats: " + werkplaats + " pct")

# !np
@HobbyBot.command(description='Now Playing')
async def np(ctx):
    async with ctx.typing():
        await ctx.send("Now playing: Darude - Sandstorm")


# define mqtt client stuff
#
# subscribe to topics
def on_connect(client, userdata, flags, rc):
    client.subscribe("bitlair/state/bitlair")
    client.subscribe("bitlair/state/djo")

# post to mqtt discord channel when state changes
def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        msg = msg.payload.decode()

        if topic == "bitlair/state/bitlair":
            topic = topic.split("/")[2].capitalize()
            msg = state_template.substitute(topic=topic, state=msg.upper())
        elif topic == "bitlair/state/djo":
            topic = topic.split("/")[2].upper()
            msg = state_template.substitute(topic=topic, state=msg.upper())
        else: return
        webhook = DiscordWebhook(url=webhook_url, rate_limit_retry=True)
        embed = DiscordEmbed(title='MQTT', description=msg, color=15105570, timestamp=datetime.datetime.now(tz = timezone).isoformat())
        webhook.add_embed(embed)
        webhook.execute()
        # prevent triggering rate limits
        sleep(1)
    except Exception as e:
        print(e)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("bitlair.nl", 1883, 60)

# Start mqtt loop and discord bot
client.loop_start()
HobbyBot.run(token)

# Exit when bot crashes
client.loop_stop(force=True)
