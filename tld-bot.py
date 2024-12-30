# Work with Python 3.6
import os
import sys
import asyncio
import discord, discord.ext.commands, discord.ext.tasks
import traceback
import datetime, time, signal, json

from pprint import pprint
from aiohttp import connector

from beautiful_soup import check_workshop_update

# swy: ugly discord.log file boilerplate
import logging, io

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(ch)

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
def twitter_send_tweet(text, show_preview=True):
    try:
        import tweepy
    except Exception as e:
        print('  [e] cannot send tweets, you may not have ran `pip install tweepy`; skipping.', e); traceback.print_exc()
        return

    if not all(var in os.environ  for var in ('TWITTER_API_KEY', 'TWITTER_API_SECRET', 'TWITTER_ACCOUNT_ACCESS_TOKEN', 'TWITTER_ACCOUNT_ACCESS_TOKEN_SECRET')):
        print('  [e] cannot send tweets; you are missing the various keys and tokens needed to call the mess that is the badly documented Twitter API; skipping.')
        return

    try:
        client = tweepy.Client(
            consumer_key = os.environ['TWITTER_API_KEY'],                  consumer_secret = os.environ['TWITTER_API_SECRET'],
            access_token = os.environ['TWITTER_ACCOUNT_ACCESS_TOKEN'], access_token_secret = os.environ['TWITTER_ACCOUNT_ACCESS_TOKEN_SECRET']
        )
        client.create_tweet(text=text) # swy: card_uri is only supported in the 1.1 api, removed in 2.0, we can't use this: , card_uri=(show_preview and None or 'tombstone://card')) # swy: https://stackoverflow.com/questions/65550090/how-to-prevent-automatic-link-preview-generation-for-status-update-in-twitter-ap
    except Exception as e:
        print('  [!] exception while sending tweet. Ignoring:', e)
        pass

def mastodon_send_toot(text, show_preview=True):
    # swy: keep twitter as fallback, for now
    twitter_send_tweet(text, show_preview)
    # swy: much easier than interfacing with the Twitter API, to get the token for other accounts we'd need to use OAuth
    #      but as we only want to post on the account that owns the bots we get the token directly, as long as we have the write:status permission
    try:
        import requests
    except Exception as e:
        print('  [e] cannot send toots because the request module is missing; skipping.', e); traceback.print_exc()
        return

    if not all(var in os.environ  for var in ('MASTODON_ACCOUNT_ACCESS_TOKEN', 'MASTODON_ACCOUNT_ACCESS_URL')):
        print('  [e] cannot send toots; you are missing the various keys and tokens needed to call the Mastodon API; skipping.')
        return

    try:
      resp = requests.post(f"https://{os.environ['MASTODON_ACCOUNT_ACCESS_URL']}/api/v1/statuses", data = {'status': text, 'visibility': 'unlisted', 'language': 'en'}, headers = {'Authorization': f"Bearer {os.environ['MASTODON_ACCOUNT_ACCESS_TOKEN']}"})
      resp.close() # swy: this library is terribly designed and leaks HTTPS sessions: https://stackoverflow.com/a/45180470/674685

    except Exception as e:
        print('  [!] exception while sending toot. Ignoring:', e)
        pass

import random

# swy: the final question will have three good and three bad answers, so have some extras of each to mix them up
questions = [
  {'question': 'Which of these factions are good?',                'answers_good': ["Gondor", "Rohan", "Elves", "Hobbits" ], 'answers_bad': ["Harad", "Mordor", "Isengard", "Khand", "Umbar"      ] },
  {'question': 'Which of these are part of the Fellowship?',       'answers_good': ["Frodo", "Aragorn", "Gimli", "Gandalf"], 'answers_bad': ["Sauron", "Gríma", "Saruman", "Galadriel", "Gollum"  ] },
  {'question': 'Which races are part of the Tolkien legendarium?', 'answers_good': ["Trolls", "Orcs", "Dragons", "Dwarves"], 'answers_bad': ["Centaurs", "Tauren", "Lizards", "Gnomes", "Kobolds" ] },
]

class TldDiscordValidator(discord.ext.commands.Cog):
  def __init__(self, bot: discord.ext.commands.Bot, log_to_channel):
    self.bot = bot
    self.log_to_channel = log_to_channel

    self.kick_stuck_members.start()

    print('[i] Doors of Durin validator plug-in ready')

  @discord.ext.commands.Cog.listener()
  async def on_ready(self):
    self.channel_test = self.bot.get_channel( 470890531061366787) #   Swyter test -- #general
    self.channel_door = self.bot.get_channel(1090711662320955563) # The Last Days -- #doors-of-durin

    # swy: there's a permanent message with a button (TldVerifyPresentation), when clicking it we
    #      create a random quiz (TldVerifyQuiz) that only the clicker can see
    class TldVerifyPresentation(discord.ui.View):
        def __init__(self):
          super().__init__(timeout=None)
          self.add_item(discord.ui.Button(label="Visit the mod's homepage", style=discord.ButtonStyle.link, url="https://tldmod.github.io"))

        @discord.ui.button(label="Verify my account", style=discord.ButtonStyle.blurple, custom_id='tld:verify')
        async def blurple_button(self, interaction: discord.Interaction, button: discord.ui.Button):
          await client.log_to_channel(interaction.user, f" has clicked on the verify button.")

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

              @discord.ui.select(placeholder=question_text, min_values=3, max_values=3, options=ans_options)
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
                memberpass_role = discord.utils.get(interaction.guild.roles, name="Member")

                if unverified_role:
                  await interaction.user.remove_roles(unverified_role)
                  await interaction.user.add_roles(memberpass_role)

                await client.log_to_channel(interaction.user, f"has **passed** validation by responding {rand_answers_good}.")

                # swy: add a distinctive «badge» in the join log message to distinguish it from the people that get kicked out
                async for message in interaction.guild.system_channel.history(limit=30):
                  if message.is_system() and message.type == discord.MessageType.new_member and message.author == interaction.user:
                    await message.add_reaction('💯')
                    break

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
    await client.log_to_channel(member, f" has **joined**. Account created at {member.created_at}. Quarantining and adding *Unverified* role.")

    unverified_role = discord.utils.get(member.guild.roles, name="Unverified")

    if unverified_role:
      await member.add_roles(unverified_role)
      mes = await self.channel_door.send(f"{member.mention}") # swy: ping them to make the hidden channel pop up more
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

  @kick_stuck_members.before_loop
  async def kick_stuck_members_before_task_launch(self):
    await self.bot.wait_until_ready()

  def cog_unload(self):
    self.kick_stuck_members.cancel()


# swy: use this to be able to read RSS or Atom feeds
#      make the feedparser dependency optional
def get_rss_feed(rss_feed_url):
    try:
        import feedparser
        # swy: retrieve the URL data ourselves with an actual timeout to avoid the obnoxious
        #      "Shard ID None heartbeat blocked for more than 280 seconds" errors: https://stackoverflow.com/a/39330232/674685
        import requests
        resp = requests.get(rss_feed_url, timeout=5)
        content = io.BytesIO(resp.content)
        resp.close() # swy: this library is terribly designed and leaks HTTPS sessions: https://stackoverflow.com/a/45180470/674685
        # --
        return feedparser.parse(content)
    except:
        print('  [e] cannot parse this, make sure you `pip install feedparser`; skipping.')
        pass

class TldRssMastodonAndTwitterPoster(discord.ext.commands.Cog):
    def __init__(self, bot):
      self.bot = bot

      # swy: bridge RSS feeds ourselves by posting new stuff to Twitter/Mastodon now that dlvr.it no longer has a free plan
      self.rss_feeds = [
        'http://rss.moddb.com/mods/the-last-days/downloads/feed/rss.xml', # MODDB // Files RSS feed - The Last Days
        'http://rss.moddb.com/mods/the-last-days/reviews/feed/rss.xml',   # MODDB // Review RSS feed - The Last Days
      # 'http://rss.moddb.com/mods/the-last-days/videos/feed/rss.xml',    # MODDB // Videos & Audio RSS feed - The Last Days
        'https://github.com/tldmod/tldmod/commits/master.atom',           # Recent Commits to tldmod - master
      ]

      self.rss_last_posted_json_filename = 'tld-bot-rss-last-posted.json'

      # swy: assume we've published any posts dated before this point in time, we don't have a persistent database
      self.rss_feeds_last_published_update = {}
      self.rss_base_date = (datetime.datetime.now(datetime.timezone.utc)).timetuple() # swy: test it with (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=50)).timetuple()

      try: # swy: load the dates where each RSS feed last posted an entry from a previous run, if any
        with open(self.rss_last_posted_json_filename, 'r') as f:
          self.rss_feeds_last_published_update = json.loads(f.read())
      except:
        pass
      
       # swy: if the returned JSON data exists for this entry/JSON key, then convert the text/digit list into an actual Python time structure that can be compared against,
       #      if not, then use the default base date (i.e. new posts from today, since we launched the bot).
      for rss_feed_url in self.rss_feeds:
        self.rss_feeds_last_published_update[rss_feed_url] =   (rss_feed_url in self.rss_feeds_last_published_update)              and \
                                                               time.struct_time(self.rss_feeds_last_published_update[rss_feed_url]) or \
                                                               self.rss_base_date
        print(f"[i] feed exists: {rss_feed_url:40} | last checked: { time.strftime("%Y-%m-%d %H:%M", self.rss_feeds_last_published_update[rss_feed_url]) }")
      
      self.task = self.update_rss_feed_in_the_background.start()
      print('[i] RSS poster plug-in ready')

    @discord.ext.tasks.loop(minutes=2, reconnect=False)
    async def update_rss_feed_in_the_background(self, *args):
      # swy: loop for every RSS feed in the list
      for rss_feed_url in self.rss_feeds:
        cur_feed = get_rss_feed(rss_feed_url)
        if not cur_feed:
          continue
        # swy: loop for every update, from oldest to newest
        for i, entry in enumerate(reversed(cur_feed.entries)):
          # swy: if this RSS entry is more recent than the last one we published, publish it.
          #      mark it as the new baseline for that specific RSS feed in this session, so we don't post it twice
          if entry.updated_parsed > self.rss_feeds_last_published_update[rss_feed_url]:
            mastodon_send_toot(
              f'''{entry.title} {entry.link}''', False # swy: don't show previews where possible (Twitter)
            )
            print(f"[i] new RSS entry published: {entry.title} {entry.link} {entry.updated_parsed} {self.rss_feeds_last_published_update[rss_feed_url]}")
            self.rss_feeds_last_published_update[rss_feed_url] = entry.updated_parsed
        
            # swy: save it persistently every time we publish it
            with open(self.rss_last_posted_json_filename, 'w') as f:
              f.write(json.dumps(self.rss_feeds_last_published_update, indent=4, sort_keys=True, default=str)) # swy: https://stackoverflow.com/a/36142844/674685
              
    @update_rss_feed_in_the_background.before_loop
    async def update_rss_feed_in_the_background_before_launch(self):
      await self.bot.wait_until_ready()


# swy: implement our bot thingie; discord.ext.commands.Bot is a higher level derivative of discord.Client we used until very recently
class TldDiscordClient(discord.ext.commands.Bot):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  async def setup_hook(self):
    # swy: create the background task and run it in the background
    self.bg_task = self.loop.create_task(self.workshop_background_task())

    # swy: enable the member verification plug-in
    await self.add_cog(TldDiscordValidator(self, self.log_to_channel))
    # swy: enable the RSS update microblogging poster
    await self.add_cog(TldRssMastodonAndTwitterPoster(self))

    def handle_exit(*args):
      raise KeyboardInterrupt
    if os.name != 'nt':
      loop = asyncio.get_running_loop()
      loop.add_signal_handler(signal.SIGTERM, handle_exit, signal.SIGTERM)
      loop.add_signal_handler(signal.SIGABRT, handle_exit, signal.SIGABRT, None)
      loop.add_signal_handler(signal.SIGINT,  handle_exit, signal.SIGINT) # swy: catch Ctrl-C, just in case: https://stackoverflow.com/a/1112350/674685

  async def close(self):
    # swy: cancel all lingering tasks and close shop
    await self.change_presence(status=discord.Status.offline)
    print("[-] exiting...")
    await super().close() # swy: https://stackoverflow.com/a/69684341/674685

  async def on_ready(self):
    print('Logged in as')
    print(self.user.name)
    print(self.user.id)
    print('------')
    await self.change_presence(activity=discord.CustomActivity(name='Pondering the orb.'))

  async def log_to_channel(self, user: discord.Member, text):
    channel_log = user.guild.get_channel(1090685607635865710)
    if channel_log:
      await channel_log.send(f"{user.mention} `{user.name}#{user.discriminator} ({user.id})` {text}")

  async def connect(self, *, reconnect: bool = True) -> None:
    print("connect")
    return await super().connect(reconnect=reconnect)
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
        print("    base date timestamp:", base_date)
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
      elif new_update == None:
        # swy: wait around ten minutes if the Workshop keeps having internal errors or transient connection problems, don't spam it
        print("[e] making the scrapper sleep for 10 minutes.")
        await asyncio.sleep(60 * 10)

      # task runs every 30 seconds; infinitely
      await asyncio.sleep(30)


# --

intents = discord.Intents.default()
intents.members = True # swy: we need this to be able to see the joins and changes

# swy: launch our bot thingie, allow for Ctrl + C
client = TldDiscordClient(intents=intents, command_prefix=None)

try:
  while True:
    asyncio.run(client.start(os.environ["DISCORD_TOKEN"]))
except KeyboardInterrupt:
  print("[i] ctrl-c detected")
  asyncio.run(client.close()) # swy: make sure the bot disappears from the member list immediately
  sys.exit(130) # swy: means Bash's 128 + 2 (SIGINT) i.e. exiting gracefully
except Exception as e:
  print('  [!] loop error. Ignoring:', e)
  traceback.print_exc()
  pass
