# Work with Python 3.6
import os
import sys
import asyncio
import discord
from pprint import pprint

import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

if not 'DISCORD_TOKEN' in os.environ:
  print('[!] Set your DISCORD_TOKEN environment variable to your Discord client secret.')
  sys.exit(-1)

client = discord.Client()

@client.event
async def on_message(message):
  # we do not want the bot to reply to itself or web-hooks
  if message.author == client.user or type(message.author) is not discord.Member or message.author.bot:
    print("Bot:", pprint(message.author))
    return

  print(pprint(message.author.roles))
  if message.content.startswith('!hello') and any(x in str(message.author.roles) for x in ['Swyter', 'Developer', 'Volunteer']):
    msg = 'Hello {0.author.mention}'.format(message)
    await message.channel.send(msg)

  if message.content.startswith('!rank'):
    await message.add_reaction('🔨')
    
  if message.content.startswith('!embed'):
    embed = discord.Embed(colour=discord.Colour(0x1b2148), url="https://discordapp.com", description="Good news, we have deployed a new Workshop update.\nTake a look at our updated TLD [changelog here](https://steamcommunity.com/sharedfiles/filedetails/changelog/299974223#profileBlock).")
    
    embed.set_thumbnail(url="https://avatars1.githubusercontent.com/u/12862724?s=400&u=223b3e00f52394fc6b5690999970a755f5444aab&v=4")
    embed.set_author(name="New Steam Workshop update — 2019-20-23 @Swyter", url="https://steamcommunity.com/sharedfiles/filedetails/changelog/299974223#profileBlock", icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Steam_icon_logo.svg/200px-Steam_icon_logo.svg.png")
    
    embed.add_field(name="➥ Restart your Steam client to force an update", value="Updates should be automatic, but they may take a few minutes.", inline=True)
    embed.add_field(name="➥ How do I get this? I'm using the manual install", value="You need to own the game on Steam and [subscribe here](https://steamcommunity.com/sharedfiles/filedetails/?id=299974223#profileBlock).")

    await message.channel.send(embed=embed)

@client.event
async def on_ready():
  print('Logged in as')
  print(client.user.name)
  print(client.user.id)
  print('------')

@client.event
async def on_member_join(member):
  print(pprint(member))
  print('User joined: ', member)

  if member.name in ['cpt', 'cp', 'sgt', 'tp'] and \
     member.name == member.display_name and \
     member.avatar == None and \
     len(member.roles) <= 1:
    client.ban(member, reason='[Automatic] Suspected bot or automated account.')
    msg = 'Preemptively banned {0.mention}, probably some automated account. 🔨'.format(member)
    await message.channel.send(msg)

@client.event
async def on_message_delete(message):
  print('Deleted message:', pprint(message))

while True:
  try:
    client.loop.run_until_complete(client.start(os.environ["DISCORD_TOKEN"]))
  except KeyboardInterrupt:
    client.loop.run_until_complete(client.logout())
    # cancel all tasks lingering
  finally:
    client.loop.close()
    sys.exit(0)