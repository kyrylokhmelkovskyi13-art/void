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
    "channels": {"rules": "", "requirements": "", "checks": "", "roster": "", "boosts": "", "tickets": ""},
    "sections": {
        "rules": {"title": "VOID Rules", "description": "Welcome to VOID! Read and follow all rules.", "items": []},
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
bot = commands.InteractionBot(intents=intents)

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

@bot.slash_command(name="void", description="VOID clan management")
async def void_root(inter):
    await inter.response.send_message("VOID Manager is online.", ephemeral=True)

@void_root.sub_command(name="publish", description="Publish a VOID information section")
async def publish(inter, section: str = commands.Param(choices=["rules","requirements","checks","roster","boosts"])):
    if not is_owner(inter):
        return await inter.response.send_message("Administrator permission required.", ephemeral=True)
    channel_id = config["channels"].get(section)
    channel = inter.guild.get_channel(int(channel_id)) if str(channel_id).isdigit() else None
    if channel is None:
        return await inter.response.send_message(f"Set the {section} channel ID in BotControl first.", ephemeral=True)
    await channel.send(embed=make_embed(config["sections"][section]))
    await inter.response.send_message(f"Published VOID {section}.", ephemeral=True)

@void_root.sub_command(name="preview", description="Preview a VOID information section")
async def preview(inter, section: str = commands.Param(choices=["rules","requirements","checks","roster","boosts"])):
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

async def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is required.")
    runner = await start_http()
    try:
        await bot.start(TOKEN)
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
