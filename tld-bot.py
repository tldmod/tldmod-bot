# Work with Python 3.6
import os
import sys
import asyncio
import discord, discord.ext.commands, discord.ext.tasks
import traceback
import datetime, time, signal

from pprint import pprint
from aiohttp import connector

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

# swy: first thing; you'll need to generate your own $TWITTER_API_KEY and $TWITTER_API_SECRET from https://developer.twitter.com/apps, which now requires adding a phone number. >:(
#
#      to act in name of an user/account you need to get the "access tokens"; you can get the user-access-token and user-access-token-secret for random accounts by running
#      `twurl authorize -j -t $TWITTER_API_KEY -s $TWITTER_API_SECRET` (install that with `gem install twurl`) and retrieving the token and secret fields
#      from your ~/.twurlrc file. If you just want to post from the account that owns the app/bot, you *can't* just grab those user-access-tokens
#      directly from https://developer.twitter.com/apps and skip the `twurl` OAuth 1.0 stuff shown above because those are *read-only* access.
#
#      By default Twitter only gives you "Essential" access, so you can't use the older 1.1 API that all the Internet talks about, (i.e. no `api = tweepy.API(auth); api.update_status(text)`)
#      to send tweets you need to use the 2.0 API, which for tweepy means using the `tweepy.Client,` functions. Easy peasy. :(
def twitter_send_tweet(text):
    try:
        import tweepy
    except:
        print('  [e] cannot send tweets, you may not have ran `pip install tweepy`; skipping.')
        return

    if not all(var in os.environ  for var in ('TWITTER_API_KEY', 'TWITTER_API_SECRET', 'TWITTER_ACCOUNT_ACCESS_TOKEN', 'TWITTER_ACCOUNT_ACCESS_TOKEN_SECRET')):
        print('  [e] cannot send tweets; you are missing the various keys and tokens needed to call the mess that is the badly documented Twitter API; skipping.')
        return

    try:
        client = tweepy.Client(
            consumer_key = os.environ['TWITTER_API_KEY'],                  consumer_secret = os.environ['TWITTER_API_SECRET'],
            access_token = os.environ['TWITTER_ACCOUNT_ACCESS_TOKEN'], access_token_secret = os.environ['TWITTER_ACCOUNT_ACCESS_TOKEN_SECRET']
        )
        client.create_tweet(text=text)
    except Exception as e:
        print('  [!] exception while sending tweet. Ignoring:', e)

def mastodon_send_toot(text):
    # swy: keep twitter as fallback, for now
    twitter_send_tweet(text)
    # swy: much easier than interfacing with the Twitter API, to get the token for other accounts we'd need to use OAuth
    #      but as we only want to post on the account that owns the bots we get the token directly, as long as we have the write:status permission
    try:
        import requests
    except:
        print('  [e] cannot send toots because the request module is missing; skipping.')
        return

    if not all(var in os.environ  for var in ('MASTODON_ACCOUNT_ACCESS_TOKEN', 'MASTODON_ACCOUNT_ACCESS_URL')):
        print('  [e] cannot send toots; you are missing the various keys and tokens needed to call the Mastodon API; skipping.')
        return

    try:
      requests.post(f"https://{os.environ['MASTODON_ACCOUNT_ACCESS_URL']}/api/v1/statuses", data = {'status': text}, headers = {'Authorization': f"Bearer {os.environ['MASTODON_ACCOUNT_ACCESS_TOKEN']}"})
    except Exception as e:
        print('  [!] exception while sending toot. Ignoring:', e)

import random

# swy: the final question will have three good and three bad answers, so have some extras of each to mix them up
questions = [
  {'question': 'Which of these factions are good?',                'answers_good': ["Gondor", "Rohan", "Elves", "Hobbits"],  'answers_bad': ["Harad", "Mordor", "Isengard", "Umbar"]   },
  {'question': 'Which of these are part of the Fellowship?',       'answers_good': ["Frodo", "Aragorn", "Gimli", "Gandalf"], 'answers_bad': ["Faramir", "Bilbo", "Galadriel", "Gollum"]},
  {'question': 'Which races are part of the Tolkien legendarium?', 'answers_good': ["Trolls", "Orcs", "Dragons", "Dwarves"], 'answers_bad': ["Centaurs", "Undead", "Lizards", "Gnomes"]   },
]

class TldDiscordValidator(discord.ext.commands.Cog):
  def __init__(self, bot: discord.ext.commands.Bot, log_to_channel):
    self.bot = bot
    self.log_to_channel = log_to_channel

    print('[i] doors-of-durin validator plug-in ready')

  @discord.ext.commands.Cog.listener()
  async def on_ready(self):
    self.channel_test = self.bot.get_channel( 470890531061366787) # Swyter test -- #general
    self.channel_door = self.bot.get_channel(1090711662320955563) # The Last Days -- #doors-of-durin

    self.kick_stuck_members.start()

    # swy: there's a permanent message with a button (TldVerifyPresentation), when clicking it we
    #      create a random quiz (TldVerifyQuiz) that only the clicker can see
    class TldVerifyPresentation(discord.ui.View):
        def __init__(self):
          super().__init__(timeout=None)
          self.add_item(discord.ui.Button(label="Visit the mod's homepage", style=discord.ButtonStyle.link, url="https://tldmod.github.io"))

        @discord.ui.button(label="Verify my account", style=discord.ButtonStyle.blurple, custom_id='tld:verify')
        async def blurple_button(self, interaction: discord.Interaction, button: discord.ui.Button):

          # swy: select one question from the lot
          rand_quest = random.choice(questions)

          # swy: randomize the order so that the first three aren't always the same
          random.shuffle(rand_quest['answers_good'])
          random.shuffle(rand_quest['answers_bad' ])

          # swy: get the first three of each after shuffling
          rand_answers_good = rand_quest['answers_good'][:3]
          rand_answers_bad  = rand_quest['answers_bad' ][:3]

          # swy: fill out the combobox; we need to randomize the order again after mixing the good and bad ones
          question_text = rand_quest['question']
          answers_all   = (rand_answers_good + rand_answers_bad); random.shuffle(answers_all)
          ans_options   = [discord.SelectOption(label=cur_answer)  for cur_answer in answers_all]

          class TldVerifyQuiz(discord.ui.View):
              def __init__(self):
                super().__init__(timeout=30)
                self.rand_answers_good = rand_answers_good

              @discord.ui.select(placeholder=question_text, min_values = 3, max_values = 3, options = ans_options)
              async def select_menu(self, interaction: discord.Interaction, select: discord.ui.Select):
                print("click")

                # swy: are all the options correct? even one bad one will cause it to fail
                if len(set(select.values).intersection(rand_answers_good)) != len(rand_answers_good):
                  self.is_finished=True
                  await interaction.response.send_message(f"Darn, try again!", ephemeral=True)
                  await client.log_to_channel(interaction.user, f"has **failed** validation by responding {select.values}.")
                  return

                await interaction.response.send_message(f"Awesome! I like {select.values[0]} too!\nNow you are in. Head over to {interaction.guild.rules_channel.mention}.", ephemeral=True)

                # swy: unquarantine the user by getting rid of this role
                unverified_role = discord.utils.get(interaction.guild.roles, name="Unverified")

                if unverified_role:
                  await interaction.user.remove_roles(unverified_role)

                await client.log_to_channel(interaction.user, f"has **passed** validation by responding {rand_answers_good}.")

          await interaction.response.send_message("Respond to the following question:", view=TldVerifyQuiz(), ephemeral=True)

    # swy: make the first post's buttons persistent across bot reboots
    self.bot.add_view(TldVerifyPresentation())

    #await self.channel_door.send(
    #  "As much as the team hates to do this, we've been receiving too much spam from new accounts lately. 🐧\n" +
    #  "So we need to make sure you are a real person to let you in. Pretty easy; a one-question quiz about *The Lord of the Rings*!", view=TldVerifyView()
    #)

  @discord.ext.commands.Cog.listener()
  async def on_member_join(self, member : discord.Member):
    print('User joined: ', pprint(member), time.strftime("%Y-%m-%d %H:%M"))
    await client.log_to_channel(member, f" has **joined**. Account created at {member.created_at}.")

  @discord.ext.commands.Cog.listener()
  async def on_member_update(self, before: discord.Member, after: discord.Member):
    if not after.pending and before.pending != after.pending:
      print('User', after)

      unverified_role = discord.utils.get(after.guild.roles, name="Unverified")

      if unverified_role:
        await after.add_roles(unverified_role)
        await client.log_to_channel(after, f"has **passed** the **Rules Screening** check. Quarantining and adding *Unverified* role.")
        mes = await self.channel_door.send(f"{after.mention}") # swy: ping them to make the hidden channel pop up more
        await mes.delete(delay=2) # swy: phantom ping

  @discord.ext.tasks.loop(seconds=30)
  async def kick_stuck_members(self):
    guild = self.channel_door.guild
    unverified_role = discord.utils.get(guild.roles, name="Unverified")
    
    for member in unverified_role.members:
      # swy: ignore users (with more roles than just this and @everyone) that may have this role for testing or to mess around
      if len(member.roles) > 2:
        continue

      then = member.joined_at; now = datetime.datetime.now(datetime.timezone.utc)

      if (now - then) > datetime.timedelta(minutes=10):
        await client.log_to_channel(member, f"is getting **kicked** for being on quarantine for too long.")
        await member.kick(reason='bot: waited too long before passing the test')

# swy: implement our bot thingie; discord.ext.commands.Bot is a higher level derivative of discord.Client we used until very recently
class TldDiscordClient(discord.ext.commands.Bot):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  async def setup_hook(self):
    # swy: create the background task and run it in the background
    self.bg_task = self.loop.create_task(self.workshop_background_task())

    # swy: enable the member verification plug-in
    await self.add_cog(TldDiscordValidator(self, self.log_to_channel))

  async def on_ready(self):
    print('Logged in as')
    print(self.user.name)
    print(self.user.id)
    print('------')

  async def log_to_channel(self, user: discord.Member, text):
    channel_log = user.guild.get_channel(1090685607635865710)
    if channel_log:
      await channel_log.send(f"{user.mention} `{user.name}#{user.discriminator} ({user.id})` {text}")

  async def on_message(self, message):
    channel_buil = self.get_channel(492923251329204224) # TLD discord -- #nightly-builds
    
    # swy: since we turned #nightly-builds into an announcement channel we need to manually click
    #      on the Publish button for each of them to appear/show up on servers that follow it.
    #      This applies both to our Steam Workshop notifications, and the GitHub change webhook
    if message.channel == channel_buil and message.channel.type == discord.ChannelType.news:
      print('Publishing message in announcement channel:', message, message.content)
      await message.publish()

    # swy: no weird commands here, boy!
    if message.content.lower().startswith('!rank'):
      await message.add_reaction('🔨')
     
    # swy: thanks!
    if message.content.lower().startswith('good bot'):
      await message.add_reaction('🐧')
      await message.add_reaction('🤖')

    # swy: we do not want the bot to reply to itself or web-hooks
    if message.author == self.user or type(message.author) is not discord.Member or message.author.bot:
      return
      
    # swy: ignore messages from users that aren't in the whitelist
    if not any(x in str(message.author.roles) for x in ['Swyter', 'Developer', 'Volunteer']):
      return

#   print(pprint(message.author.roles))
    
    # swy: useful for testing
    if message.content.startswith('!hello'):
      msg = 'Hello {0.author.mention}'.format(message)
      await message.channel.send(msg)

  async def on_member_join(self, member : discord.Member):
    return
    #if (member.name in ['cpt', 'cp', 'sgt', 'tp'] or not any(x in member.name for x in 'aeiou')) and \
    #   member.name.islower() and \
    #   len(member.name) < 5 and \
    #   member.name == member.display_name and \
    #   member.avatar == None and \
    #   len(member.roles) <= 1:
    #   
    #  channel_test = member.guild.system_channel
    #  
    #  if (not channel_test):
    #    channel_test = self.get_channel(470890531061366787)
    #   
    #  # swy: send a message to the #off-topic channel
    #  await channel_test.send('Preemptively banned {0.mention}, probably some automated account. 🔨'.format(member))
    #  await member.guild.ban(member, reason='[Automatic] Suspected bot or automated account.')

  async def on_message_delete(self, message: discord.Message):
    # swy: we do not want the bot to report deleting itself or web-hooks
    if message.is_system:
      return
    if message.author == self.user or type(message.author) is not discord.Member or message.author.bot:
      return

    print('Deleted message:', pprint(message), message.content, time.strftime("%Y-%m-%d %H:%M"), message.created_at, message.channel.name)
    self.log_to_channel(message.author, f"someone has deleted {message.author.mention}'s message: `{message.content}`, made at _{message.created_at}_, in {message.channel.mention}/`{message.channel.name} ({message.channel.id})`.")

  async def workshop_background_task(self):
    await self.wait_until_ready()
    print('[i] background workshop scrapper ready')
    
    channel_buil = self.get_channel(492923251329204224) # TLD discord -- #nightly-builds
    channel_gene = self.get_channel(492783429872517121) # TLD discord -- #general
    channel_test = self.get_channel(470890531061366787) # Swyter test -- #general
    base_date = datetime.datetime.now()
#   base_date = datetime.datetime.fromtimestamp(1580708354) # datetime.datetime.now()

    # swy: load it from a previous run, if any
    try:
      with open('tld-bot-timestamp.txt', 'r') as f:
        base_date = datetime.datetime.fromtimestamp(int(f.read()))
    except:
      pass

    while not self.is_closed():
      new_update = check_workshop_update(base_date)
                
      if (new_update):
        base_date = new_update['date']; pprint(new_update)
  
        embed = discord.Embed(colour=discord.Colour(0x1b2148), description='Good news, we have deployed a new Workshop update.\nTake a look at our updated TLD [changelog here](https://steamcommunity.com/sharedfiles/filedetails/changelog/299974223#%s).' % new_update['str'])
        
        embed.set_thumbnail(url='https://avatars1.githubusercontent.com/u/12862724')
        embed.set_author(name='New Steam Workshop update — %s' % new_update['date'].strftime("%Y-%m-%d %H:%M"), url='https://steamcommunity.com/sharedfiles/filedetails/changelog/299974223#profileBlock', icon_url='https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Steam_icon_logo.svg/200px-Steam_icon_logo.svg.png')
        
        embed.add_field(name='➥ Restart your Steam client to force an update', value='Updates should be automatic, but they may take a few minutes.', inline=True)
        embed.add_field(name="➥ How do I get this? I'm using the manual install", value='You need to own the game on Steam and [subscribe here](https://steamcommunity.com/sharedfiles/filedetails/?id=299974223#profileBlock).')

        await channel_buil.send(embed=embed)
        await channel_gene.send(embed=embed)
        await channel_test.send(embed=embed)

        # swy: save it persistently
        with open('tld-bot-timestamp.txt', 'w') as f:
          f.write('%u' % int(time.mktime(base_date.timetuple())))

        # swy: notify the twitter people from @tldmod :)
        mastodon_send_toot(
          f'''New Steam Workshop update — {new_update['date'].strftime("%Y-%m-%d %H:%M")}.\n\n''' +
          f'''Good news, we have deployed a new Workshop update. Take a look at our updated TLD changelog here: https://steamcommunity.com/sharedfiles/filedetails/changelog/299974223#{new_update['str']}'''
        )

      # task runs every 30 seconds; infinitely
      await asyncio.sleep(30)

# --

intents = discord.Intents.default()
intents.members = True # swy: we need this to be able to see the joins and changes

# swy: launch our bot thingie, allow for Ctrl + C
client = TldDiscordClient(intents=intents, command_prefix=None)
loop = asyncio.get_event_loop()

def handle_exit():
    raise KeyboardInterrupt

if os.name != 'nt':
  loop.add_signal_handler(signal.SIGTERM, handle_exit, signal.SIGTERM)
  loop.add_signal_handler(signal.SIGABRT, handle_exit, signal.SIGABRT, None)

while True:
  try:
    loop.run_until_complete(client.start(os.environ["DISCORD_TOKEN"]))
    
  except connector.ClientConnectorError:
    traceback.print_exc()
    pass

  # swy: cancel all lingering tasks and close shop
  except KeyboardInterrupt:
    loop.run_until_complete(client.change_presence(status=discord.Status.offline))
    print("[i] ctrl-c detected")
    loop.run_until_complete(client.close())
    print("[-] exiting...")
    sys.exit(0)
