# VOID Discord Bot

A separate Disnake bot for the VOID clan, with an authenticated control API for BotControl.

## Features
- Slash commands: `/void preview` and `/void publish`.
- Sections: rules, tryouts, requirements, checks, roster and boost perks.
- Owner/admin-only publishing.
- Authenticated `GET/PUT /control/config` API for BotControl.
- JSON config file; do not commit real tokens or secrets.

## Deploy
1. Create a Render Python Worker from this repository.
2. Build: `pip install -r requirements.txt`
3. Start: `python bot.py`
4. Set `DISCORD_TOKEN` and `BOTCONTROL_SHARED_SECRET` in Render environment variables.
5. Enable the Server Members Intent only if you later add member roster syncing.

## BotControl connection
Add a VOID service to BotControl's `BOT_SERVICES` environment variable using the Render service ID and public control URL. Configure the same `BOTCONTROL_SHARED_SECRET` on both services.

BotControl includes a VOID Clan Manager editor page. Add the VOID service to the server-side BOT_SERVICES allowlist before using it.
