#!/usr/bin/env python3

# Bitlair HobbyBot

import asyncio
from typing import Optional
from time import sleep
from string import Template
from discord import Intents
from discord.ext import commands
from discord_webhook import DiscordWebhook, DiscordEmbed
from datetime import datetime
import pytz
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
import os
import sys


mqtt_host = os.getenv('MQTT_HOST')
if not mqtt_host:
    print('MQTT_HOST unset')
    sys.exit(1)

token = os.getenv('DISCORD_TOKEN')
if not token:
    print('DISCORD_TOKEN unset')
    sys.exit(1)

webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
if not webhook_url:
    print('DISCORD_WEBHOOK_URL unset')
    sys.exit(1)

timezone = pytz.timezone('Europe/Amsterdam')

# Discord bot stuff
intents = Intents.default()
intents.message_content = True
intents.members = True
HobbyBot = commands.Bot(command_prefix='!', description='Bitlair Bot', intents=intents)

def mqtt_get_one(topic):
    try:
        msg = subscribe.simple(topic, hostname=mqtt_host, keepalive=10)
        return msg.payload.decode()
    except err:
        print(err)
        return ''

# Define bot commands
@HobbyBot.event
async def on_ready():
    print(f'Logged in as {HobbyBot.user} (ID: {HobbyBot.user.id})')

# !state
@HobbyBot.command(description='Bitlair Space State')
async def state(ctx):
    async with ctx.typing():
        spaceState = mqtt_get_one("bitlair/state")
        if spaceState == "open":
            await ctx.send("Bitlair is OPEN! :sunglasses:")
        elif spaceState == "closed":
            await ctx.send("Bitlair is closed :pensive:")

# !co2
@HobbyBot.command(description='co2 levels')
async def co2(ctx):
    async with ctx.typing():
        hoofdruimte = mqtt_get_one("bitlair/climate/hoofdruimte_ingang/co2_ppm")
        await ctx.send("Hoofdruimte: %s ppm\n" % hoofdruimte)
# !temp
@HobbyBot.command(description='Temperature')
async def temp(ctx):
    async with ctx.typing():
        hoofdruimte = mqtt_get_one("bitlair/climate/hoofdruimte_ingang/temperature_c")
        await ctx.send("Hoofdruimte: %s °C\n" % hoofdruimte )

# !humid
@HobbyBot.command(description='Humidity')
async def humid(ctx):
    async with ctx.typing():
        hoofdruimte = mqtt_get_one("bitlair/climate/hoofdruimte_ingang/humidity_pct")
        await ctx.send("Hoofdruimte: %s pct\n" % hoofdruimte)

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
    client.subscribe("bitlair/photos")


def webhook_message(msg):
    webhook = DiscordWebhook(url=webhook_url, rate_limit_retry=True, content=msg)
    webhook.execute()


# post to mqtt discord channel when state changes
def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        msg = msg.payload.decode()

        if topic == 'bitlair/state/bitlair':
            webhook_message('Bitlair is now %s' % msg.upper())
        elif topic == 'bitlair/state/djo':
            webhook_message('DJO is now %s' % msg.upper())
        elif topic == 'bitlair/photos':
            webhook = DiscordWebhook(url=webhook_url, rate_limit_retry=True)
            embed = DiscordEmbed(title='WIP Cam', color='fc5d1d')
            embed.set_url('https://bitlair.nl/fotos/view/' + msg)
            embed.set_image('https://bitlair.nl/fotos/photos/' + msg)
            webhook.add_embed(embed)
            webhook.execute()
        else:
            return
        sleep(1)  # Prevent triggering rate limits.
    except Exception as e:
        print(e)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(mqtt_host, 1883, 60)

# Start mqtt loop and discord bot
client.loop_start()
HobbyBot.run(token)

# Exit when bot crashes
client.loop_stop(force=True)
