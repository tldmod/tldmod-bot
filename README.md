# tldmod-bot
Maintenance Discord server bot for the Mount&Blade mod *[The Last Days of the Third Age](https://discord.gg/uczcz34)*.

It mainly takes care of publishing embedded notifications when our _Steam Workshop_ item gets a new update, and links to its changelog.
This is done by continuously polling against the Steam page, and scrapping the HTML and then comparing against a saved/persistent timestamp with the last pushed update to avoid spamming or going crazy with older, or already notified updates.

## How to use
Make a executable `start-bot.sh` with these contents to run it and log the mirrored output with `tee`.
```bash
export PATH=".:..:$PATH"
export DISCORD_TOKEN='tH15iS4.lEgITtOk3N-P13A5eJUsTU53nnE+1M-W4i7nG.leAkd'

# swy: generate your own app (and API key pair) from: https://developer.twitter.com/apps
export TWITTER_API_KEY='62kjk2kjs0ds0s00sdf0erQk3'
export TWITTER_API_SECRET='3kl3kl34jagladfjkag78df7878df87agjk3bjkq34kngjkgak'

# swy: retrieve from `twurl authorize -c $TWITTER_API_KEY -s $TWITTER_API_SECRET; cat ~/.twurlrc` (copy 'token' and 'secret')
#      with this you can gain access to any account you want; the Twitter app account can be different from the access-token account
export TWITTER_ACCOUNT_ACCESS_TOKEN='7603448958-klñafsdf98adafjkafnknkaggjkagjkgajklasd'
export TWITTER_ACCOUNT_ACCESS_TOKEN_SECRET='545jsgsgiojiogfjagklsklasdfklfklñ5ga9agr9$g'

# swy: generate your own app from: https://botsin.space/settings/applications/new
export MASTODON_ACCOUNT_ACCESS_TOKEN='k-76kLl3nnjeeeuckj6sdFGñl9k8k7k65h3hb44k7dd'
export MASTODON_ACCOUNT_ACCESS_URL='botsin.space'

python -u tld-bot.py 2>&1 | tee -a discord.out
```

You can use something like `tmux` to daemonize it in your server. Good luck.

## Requisites

Python, [discord.py](https://discordpy.readthedocs.io/en/latest/), a chat server, one token and some patience.
