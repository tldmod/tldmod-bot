# Work with Python 3.6
import os
import sys
import asyncio
import discord
from pprint import pprint

import datetime, time
from beautiful_soup import check_workshop_update

# swy: ugly discord.log file boilerplate
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# swy: exit if we don't have a valid bot token
if not 'DISCORD_TOKEN' in os.environ:
  print('[!] Set your DISCORD_TOKEN environment variable to your Discord client secret.')
  sys.exit(-1)

# swy: implement our bot thingie
class TldDiscordClient(discord.Client):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # create the background task and run it in the background
    self.bg_task = self.loop.create_task(self.workshop_background_task())

  async def on_ready(self):
    print('Logged in as')
    print(self.user.name)
    print(self.user.id)
    print('------')

  async def on_message(self, message):
    # swy: no weird commands here, boy!
    if message.content.lower().startswith('!rank'):
      await message.add_reaction('🔨')
     
    # swy: thanks!
    if message.content.lower().startswith('good bot'):
      await message.add_reaction('🐧')
      await message.add_reaction('🤖')

    # swy: we do not want the bot to reply to itself or web-hooks
    if message.author == self.user or type(message.author) is not discord.Member or message.author.bot:
#     print("Bot:", pprint(message.author))
      return
      
    # swy: ignore messages from users that aren't in the whitelist
    if not any(x in str(message.author.roles) for x in ['Swyter', 'Developer', 'Volunteer']):
#     print("Ignored:", pprint(message.author))
      return

    print(pprint(message.author.roles))
    
    # swy: useful for testing
    if message.content.startswith('!hello'):
      msg = 'Hello {0.author.mention}'.format(message)
      await message.channel.send(msg)

  async def on_member_join(self, member):
    print('User joined: ', pprint(member))

    if (member.name in ['cpt', 'cp', 'sgt', 'tp'] or not any(x in member.name for x in 'aeiou')) and \
       member.name.islower() and \
       len(member.name) < 5 and \
       member.name == member.display_name and \
       member.avatar == None and \
       len(member.roles) <= 1:
       
      channel_test = member.guild.system_channel
      
      if (not channel_test):
        channel_test = self.get_channel(470890531061366787)
       
      # swy: send a message to the #off-topic channel
      await channel_test.send('Preemptively banned {0.mention}, probably some automated account. 🔨'.format(member))
      await member.guild.ban(member, reason='[Automatic] Suspected bot or automated account.')
      
  async def on_message_delete(self, message):
    print('Deleted message:', pprint(message))

  async def workshop_background_task(self):
    await self.wait_until_ready()
    print('[i] background workshop scrapper ready')
    
    channel_gene = self.get_channel(492783429872517121) # TLD discord -- #general
    channel_test = self.get_channel(470890531061366787) # Swyter test -- #general
    base_date = datetime.datetime.now()
#   base_date = datetime.datetime.fromtimestamp(1535662299) # datetime.datetime.now()
    
    while not self.is_closed():
      new_update = check_workshop_update(base_date)
                
      if (new_update):
        base_date = new_update['date']; pprint(new_update)
  
        embed = discord.Embed(colour=discord.Colour(0x1b2148), description='Good news, we have deployed a new Workshop update.\nTake a look at our updated TLD [changelog here](https://steamcommunity.com/sharedfiles/filedetails/changelog/299974223#%s).' % new_update['str'])
        
        embed.set_thumbnail(url='https://avatars1.githubusercontent.com/u/12862724')
        embed.set_author(name='New Steam Workshop update — %s' % new_update['date'].strftime("%Y-%m-%d %H:%M"), url='https://steamcommunity.com/sharedfiles/filedetails/changelog/299974223#profileBlock', icon_url='https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Steam_icon_logo.svg/200px-Steam_icon_logo.svg.png')
        
        embed.add_field(name='➥ Restart your Steam client to force an update', value='Updates should be automatic, but they may take a few minutes.', inline=True)
        embed.add_field(name="➥ How do I get this? I'm using the manual install", value='You need to own the game on Steam and [subscribe here](https://steamcommunity.com/sharedfiles/filedetails/?id=299974223#profileBlock).')
  
        await channel_gene.send(embed=embed)
        await channel_test.send(embed=embed)
  
      # task runs 3 times per hour; infinitely
      await asyncio.sleep((60 / 3) * 60)
  
# swy: launch our bot thingie, allow for Ctrl + C
client = TldDiscordClient()

while True:
  try:
    client.loop.run_until_complete(client.start(os.environ["DISCORD_TOKEN"]))
  except KeyboardInterrupt:
    client.loop.run_until_complete(client.logout())
    # cancel all tasks lingering
  finally:
    client.loop.close()
    sys.exit(0)