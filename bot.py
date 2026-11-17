import asyncio
import json
import os
from pathlib import Path
from aiohttp import web
import disnake
from disnake.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN", "")
SHARED_SECRET = os.getenv("BOTCONTROL_SHARED_SECRET", "")
PORT = int(os.getenv("PORT", "10000"))
CONFIG_PATH = Path(os.getenv("VOID_CONFIG_PATH", "config.json"))

DEFAULT_CONFIG = {
    "guild_id": "",
    "channels": {"rules": "", "tryouts": "", "requirements": "", "checks": "", "roster": "", "boosts": "", "tickets": ""},
    "sections": {
        "rules": {"title": "VOID Rules", "description": "Welcome to VOID! Read and follow all rules. Ignorance is not an excuse.", "items": [
            "No problematic discussions: politics, religion, hate speech or disrespectful behavior.",
            "No NSFW or explicit adult content.",
            "No spamming or repeatedly sending similar messages, emojis or media.",
            "No racism, discriminatory jokes, media or slurs.",
            "No ban evasion using alternate accounts.",
            "No doxxing or sharing personal information without permission.",
            "No alternate accounts or bots without staff permission.",
            "Use common sense and act respectfully.",
            "No harassment, aggressive arguments or unwanted repeated DMs.",
            "No advertising, self-promotion or inviting members to leave VOID.",
            "No illegal content or pirated materials.",
            "No disruptive behavior, begging, impersonation or threats.",
            "No severe profanity; bypassing words such as tf/lmao are allowed.",
            "Do not reveal personal information or passwords; use Discord display names.",
            "Follow staff instructions. Do not ping trial moderators without a valid reason.",
            "Keep real-life topics out of public chat.",
            "Speak English only in public chat.",
            "Do not post in channels restricted by staff.",
            "Do not ping owners without a valid reason; use a ticket or DM.",
            "Follow Discord Terms of Service."
        ]},
        "tryouts": {"title": "VOID Tryout Rules", "description": "Please read the rules carefully before requesting a tryout match.", "items": [
            "No aim assist or auto shoot. If using aim assist, set it to 0.5 or lower.",
            "Minimum level: 100/300+ (confirm exact threshold with staff).",
            "Minimum rank: Platinum 1+.",
            "Minimum winrate: 55%.",
            "DL: Assault Rifle, Handgun, Fists and Grenade only.",
            "SDL: Sniper, Handgun, Fists and Grenade only.",
            "CL: Any weapon except Flamethrower, Riot+Shorty, Grenade Launcher, Distortion, RPG and Minigun.",
            "Autopass: over 80% winrate, over Level 350, Onyx rank or known community creator; screenshot proof required."
        ]},
        "requirements": {"title": "VOID Requirements", "description": "VOID clan joining requirements.", "items": ["Minimum level: 100", "Platinum 2+", "R3+ (RCL)", "1,200 wins", "65% winrate", "Good movement and aim", "You must meet at least 4 of 6 requirements."]},
        "checks": {"title": "VOID Checks", "description": "Information about clan checks. Edit this text in BotControl.", "items": []},
        "roster": {"title": "VOID Roster", "description": "VOID clan roster.", "items": []},
        "boosts": {"title": "VOID Boost Perks", "description": "Boost our server to unlock exclusive perks and rewards! Your support helps the VOID community grow.", "items": ["💎 1 BOOST: Extra Entries in giveaways; Bypass Slowmode in chat channels; Ability to change your nickname", "🔥 2 BOOSTS: 1 Custom Emoji; Custom Role (custom color & emoji next to name); 1 Custom Sticker", "⚠️ Perks will be lost if you leave or unboost the server (added emoji/sticker will stay).", "🎟️ HOW TO CLAIM: Open a ticket in #tickets to claim your perks!"]}
    }
}

def load_config():
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            merged = {**DEFAULT_CONFIG, **data}
            merged["channels"] = {**DEFAULT_CONFIG["channels"], **data.get("channels", {})}
            merged["sections"] = {**DEFAULT_CONFIG["sections"], **data.get("sections", {})}
            return merged
        except (OSError, json.JSONDecodeError):
            pass
    return json.loads(json.dumps(DEFAULT_CONFIG))

config = load_config()

def save_config():
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

intents = disnake.Intents.default()
intents.guilds = True
intents.members = True
GUILD_ID = 1563860488243249253
bot = commands.InteractionBot(
    intents=intents,
    test_guilds=[GUILD_ID],
    command_sync_flags=commands.CommandSyncFlags(sync_commands_debug=True),
)

def is_owner(inter):
    return inter.guild is not None and (inter.author.guild_permissions.administrator or inter.author.id == inter.guild.owner_id)

def make_embed(section):
    embed = disnake.Embed(
        title=str(section.get("title", "VOID"))[:256],
        description=str(section.get("description", ""))[:4000],
        color=0x7864E8
    )
    items = section.get("items", [])
    if items:
        body = "\n".join("• " + str(x) for x in items)
        embed.add_field(name="Information", value=body[:1024], inline=False)
    embed.set_footer(text="VOID Clan • Thank you.")
    return embed

http_runner = None

@bot.event
async def on_ready():
    global http_runner
    command_names = [command.name for command in bot.slash_commands]
    print(f"[VOID] Connected as {bot.user} (ID: {bot.user.id})", flush=True)
    print(f"[VOID] Guild command target: {GUILD_ID}", flush=True)
    print(f"[VOID] Local slash commands loaded: {command_names}", flush=True)
    if http_runner is None:
        http_runner = await start_http()
        print(f"[VOID] HTTP health server started on port {PORT}", flush=True)


@bot.slash_command(name="void", description="VOID clan management")
async def void_root(inter):
    # Disnake invokes the parent callback before a group subcommand.
    # Only answer when the user ran bare /void with no subcommand.
    if not inter.data.options:
        await inter.response.send_message("VOID Manager is online.", ephemeral=True)

@void_root.sub_command(name="publish", description="Publish a VOID information section")
async def publish(inter, section: str = commands.Param(choices=["rules","tryouts","requirements","checks","roster","boosts"])):
    if not is_owner(inter):
        return await inter.response.send_message("Administrator permission required.", ephemeral=True)
    channel_id = config["channels"].get(section)
    channel = inter.guild.get_channel(int(channel_id)) if str(channel_id).isdigit() else None
    if channel is None:
        return await inter.response.send_message(f"Set the {section} channel ID in BotControl first.", ephemeral=True)
    await channel.send(embed=make_embed(config["sections"][section]))
    await inter.response.send_message(f"Published VOID {section}.", ephemeral=True)

@bot.slash_command(name="void_publish", description="Publish a VOID information section")
async def void_publish(inter, section: str = commands.Param(choices=["rules","tryouts","requirements","checks","roster","boosts"])):
    if not is_owner(inter):
        return await inter.response.send_message("Administrator permission required.", ephemeral=True)
    channel_id = config["channels"].get(section)
    channel = inter.guild.get_channel(int(channel_id)) if inter.guild and str(channel_id).isdigit() else None
    if channel is None:
        return await inter.response.send_message(f"Set the {section} channel ID in BotControl first.", ephemeral=True)
    await channel.send(embed=make_embed(config["sections"][section]))
    await inter.response.send_message(f"Published VOID {section}.", ephemeral=True)


@bot.slash_command(name="void_preview", description="Preview a VOID information section")
async def void_preview(inter, section: str = commands.Param(choices=["rules","tryouts","requirements","checks","roster","boosts"])):
    if not is_owner(inter):
        return await inter.response.send_message("Administrator permission required.", ephemeral=True)
    await inter.response.send_message(embed=make_embed(config["sections"][section]), ephemeral=True)


@void_root.sub_command(name="preview", description="Preview a VOID information section")
async def preview(inter, section: str = commands.Param(choices=["rules","tryouts","requirements","checks","roster","boosts"])):
    if not is_owner(inter):
        return await inter.response.send_message("Administrator permission required.", ephemeral=True)
    await inter.response.send_message(embed=make_embed(config["sections"][section]), ephemeral=True)

async def control_get(request):
    if not SHARED_SECRET or request.headers.get("Authorization") != f"Bearer {SHARED_SECRET}":
        raise web.HTTPUnauthorized(text=json.dumps({"error":"Unauthorized"}), content_type="application/json")
    return web.json_response({"config": config})

async def control_put(request):
    if not SHARED_SECRET or request.headers.get("Authorization") != f"Bearer {SHARED_SECRET}":
        raise web.HTTPUnauthorized(text=json.dumps({"error":"Unauthorized"}), content_type="application/json")
    try:
        payload = await request.json()
    except Exception:
        raise web.HTTPBadRequest(text='{"error":"Invalid JSON"}', content_type="application/json")
    if not isinstance(payload, dict):
        raise web.HTTPBadRequest(text='{"error":"Object required"}', content_type="application/json")
    if "channels" in payload:
        if not isinstance(payload["channels"], dict):
            raise web.HTTPBadRequest(text='{"error":"channels must be an object"}', content_type="application/json")
        for key, value in payload["channels"].items():
            if key not in config["channels"] or not (value == "" or (isinstance(value, str) and value.isdigit())):
                raise web.HTTPBadRequest(text='{"error":"Invalid channel configuration"}', content_type="application/json")
        config["channels"].update(payload["channels"])
    if "sections" in payload:
        if not isinstance(payload["sections"], dict):
            raise web.HTTPBadRequest(text='{"error":"sections must be an object"}', content_type="application/json")
        for key, value in payload["sections"].items():
            if key not in config["sections"] or not isinstance(value, dict):
                raise web.HTTPBadRequest(text='{"error":"Invalid section"}', content_type="application/json")
            title = value.get("title", config["sections"][key]["title"])
            description = value.get("description", config["sections"][key]["description"])
            items = value.get("items", config["sections"][key]["items"])
            if not isinstance(title, str) or not isinstance(description, str) or not isinstance(items, list) or not all(isinstance(x, str) for x in items):
                raise web.HTTPBadRequest(text='{"error":"Invalid section fields"}', content_type="application/json")
            config["sections"][key] = {"title":title[:256], "description":description[:4000], "items":items[:30]}
    save_config()
    return web.json_response({"ok": True, "config": config})

async def start_http():
    app = web.Application(client_max_size=64 * 1024)
    app.router.add_get("/health", lambda _: web.json_response({"ok": True, "bot": "VOID"}))
    app.router.add_get("/control/config", control_get)
    app.router.add_put("/control/config", control_put)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    return runner

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is required.")
    bot.run(TOKEN)
