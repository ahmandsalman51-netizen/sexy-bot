import os
import asyncio
import logging
import discord
from discord import app_commands
from discord.ext import commands

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DiscordBot")

# Intents (Ban / Unban ke liye default intents kaafi hain, but members & message_content required for DMs)
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Prefix Setup ('.' prefix support)
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print("==========================================")
    print(f"SUCCESS: Logged in as {bot.user} (ID: {bot.user.id})")
    print("==========================================")
    
    # Syncing Slash Commands Globally
    try:
        synced = await bot.tree.sync()
        print(f"--> SYNCED {len(synced)} SLASH COMMANDS SUCCESSFULLY!")
    except Exception as e:
        print(f"--> SLASH SYNC ERROR: {e}")

    # Rich Presence Status: Listening to Anna The Nuker
    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name="Anna The Nuker"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print("--> STATUS UPDATED TO: Listening to Anna The Nuker")

# Shared Logic for Mass DMing
async def execute_mass_dm(ctx_or_interaction, message: str, is_slash=False):
    guild = ctx_or_interaction.guild
    user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author

    # Check Permissions (Owner or Admin)
    is_owner = user.id == guild.owner_id
    is_admin = user.guild_permissions.administrator

    if not (is_owner or is_admin):
        embed = discord.Embed(
            title="⛔ Access Denied",
            description="Only the **Server Owner** or members with **Administrator** permission can use this command.",
            color=discord.Color.red()
        )
        if is_slash:
            await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx_or_interaction.send(embed=embed)
        return

    members = [m for m in guild.members if not m.bot]
    total_members = len(members)

    init_embed = discord.Embed(
        title="📢 Mass Direct Message Operation Started",
        description=f"Sending message to **{total_members}** members with 3s delay...",
        color=discord.Color.blue()
    )
    init_embed.add_field(name="Server", value=guild.name, inline=True)
    init_embed.add_field(name="Total Target Users", value=str(total_members), inline=True)

    if is_slash:
        await ctx_or_interaction.response.defer(ephemeral=True)
        await ctx_or_interaction.followup.send(embed=init_embed, ephemeral=True)
    else:
        status_msg = await ctx_or_interaction.send(embed=init_embed)

    successful = 0
    failed = 0

    for member in members:
        try:
            # Plain Normal Text Message (No Embed)
            await member.send(message)
            successful += 1
            print(f"Sent normal DM to {member}")
        except Exception as e:
            failed += 1
            print(f"Failed to send DM to {member}: {e}")

        await asyncio.sleep(3)

    summary_embed = discord.Embed(
        title="✅ Mass DM Operation Completed",
        color=discord.Color.green()
    )
    summary_embed.add_field(name="Targeted Members", value=str(total_members), inline=False)
    summary_embed.add_field(name="Successfully Sent", value=f"```yaml\n{successful}\n```", inline=True)
    summary_embed.add_field(name="Failed / DMs Closed", value=f"```yaml\n{failed}\n```", inline=True)

    if is_slash:
        await ctx_or_interaction.followup.send(embed=summary_embed, ephemeral=True)
    else:
        await status_msg.reply(embed=summary_embed)

# 1. Slash Command: /dmall
@bot.tree.command(name="dmall", description="Send a DM to all members (Owner & Admin Only).")
@app_commands.describe(message="The message to send.")
async def slash_dmall(interaction: discord.Interaction, message: str):
    await execute_mass_dm(interaction, message, is_slash=True)

# 2. Prefix Command: .dmall
@bot.command(name="dmall")
async def prefix_dmall(ctx, *, message: str = None):
    if not message:
        await ctx.send("❌ Please provide a message! Example: `.dmall Hello members`")
        return
    await execute_mass_dm(ctx, message, is_slash=False)

# 3. Prefix Command: .unbanall (Unban all banned users)
@bot.command(name="unbanall")
async def unbanall(ctx):
    guild = ctx.guild
    user = ctx.author

    # Check Permissions (Owner or Admin)
    is_owner = user.id == guild.owner_id
    is_admin = user.guild_permissions.administrator

    if not (is_owner or is_admin):
        embed = discord.Embed(
            title="⛔ Access Denied",
            description="Only the **Server Owner** or members with **Administrator** permission can use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Fetch banned users
    try:
        banned_users = [entry async for entry in guild.bans()]
    except discord.Forbidden:
        await ctx.send("❌ Bot ke paas **Ban Members** ya **Administrator** permission nahi hai!")
        return
    except Exception as e:
        await ctx.send(f"❌ Ban list fetch karne mein error aaya: {e}")
        return

    if not banned_users:
        await ctx.send("ℹ️ Server mein koi bhi user banned nahi hai.")
        return

    total_banned = len(banned_users)

    init_embed = discord.Embed(
        title="🔓 Mass Unban Operation Started",
        description=f"Total **{total_banned}** banned users ko unban kiya ja raha hai...",
        color=discord.Color.blue()
    )
    status_msg = await ctx.send(embed=init_embed)

    unbanned_count = 0
    failed_count = 0

    for ban_entry in banned_users:
        banned_user = ban_entry.user
        try:
            await guild.unban(banned_user, reason=f"Unbanned by {user} using .unbanall")
            unbanned_count += 1
            print(f"Unbanned user: {banned_user} ({banned_user.id})")
        except Exception as e:
            failed_count += 1
            print(f"Failed to unban {banned_user}: {e}")

        # Rate limit se bachne ke liye 1 second delay
        await asyncio.sleep(1)

    summary_embed = discord.Embed(
        title="✅ Mass Unban Operation Completed",
        color=discord.Color.green()
    )
    summary_embed.add_field(name="Total Banned Found", value=str(total_banned), inline=False)
    summary_embed.add_field(name="Successfully Unbanned", value=f"```yaml\n{unbanned_count}\n```", inline=True)
    summary_embed.add_field(name="Failed", value=f"```yaml\n{failed_count}\n```", inline=True)

    await status_msg.reply(embed=summary_embed)

if __name__ == "__main__":
    print("--> BOT STARTING UP...")
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("CRITICAL ERROR: DISCORD_TOKEN IS MISSING!")
        exit(1)
    
    bot.run(token)
