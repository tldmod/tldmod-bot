# Work with Python 3.6
import os
import sys
import discord
from pprint import pprint

if not 'DISCORD_TOKEN' in os.environ:
  print('[!] Set your DISCORD_TOKEN environment variable to your Discord client secret.')
  sys.exit(-1)

client = discord.Client()

@client.event
async def on_message(message):
  # we do not want the bot to reply to itself or web-hooks
  if message.author == client.user or message.author is not Member or message.author.bot:
    return

  print(pprint(message.author))
  print(pprint(message.author.roles))
  if message.content.startswith('!hello') and any(x in str(message.author.roles) for x in ['Swyter', 'Developer', 'Volunteer']):
    msg = 'Hello {0.author.mention}'.format(message)
    await message.channel.send(msg)

  if message.content.startswith('!rank'):
    await message.add_reaction('🔨')

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
  print(pprint(message))

client.run(os.environ["DISCORD_TOKEN"])