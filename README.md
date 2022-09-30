# tldmod-bot
Maintenance Discord server bot for the Mount&Blade mod *[The Last Days of the Third Age](https://discord.gg/uczcz34)*.

It mainly takes care of publishing embedded notifications when our _Steam Workshop_ item gets a new update, and links to its changelog.
This is done by continuously polling against the Steam page, and scrapping the HTML and then comparing against a saved/persistent timestamp with the last pushed update to avoid spamming or going crazy with older, or already notified updates.

## How to use
Make a executable `start-bot.sh` with these contents to run it and log the mirrored output with `tee`.
```bash
export PATH=".:..:$PATH"
export DISCORD_TOKEN='tH15iS4.lEgITtOk3N-P13A5eJUsTU53nnE+1M-W4i7nG.leAkd'
python -u tld-bot.py 2>&1 | tee -a discord.out
```

You can use something like `tmux` to daemonize it in your server. Good luck.

## Requisites

Python, [discord.py](https://discordpy.readthedocs.io/en/latest/), a chat server, one token and some patience.
