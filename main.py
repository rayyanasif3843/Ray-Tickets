import os
import json
import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button

TOKEN = os.getenv("DISCORD_TOKEN")

APPLICATION_CHANNEL_ID = 1511410675841237173

ACCEPT_ROLES = [
    1511410384517599423,
    1511410382978285783
]

SERVER_NAME = "GladXblox"

QUESTIONS = [
    f"Why do you want to be a mod in {SERVER_NAME}? (3+ sentences)",
    "How old are you?",
    "Do you have any experience in moderation?",
    "2 members are fighting aggressively, and they are not listening to you. What would you do here?",
    "What will you do if you see two staff members fighting?",
    "Will you get 800 weekly messages in your first week?",
    f"How are you going to be a better moderator than others? (3+ sentences)",
    "Do you have anything else to say?"
]

PANEL_FILE = "panel.json"
APPLICATION_FILE = "applications.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.dm_messages = True
intents.guilds = True


# ================= FILE FUNCTIONS ================= #

def load_panel():
    if not os.path.exists(PANEL_FILE):
        with open(PANEL_FILE, "w", encoding="utf-8") as f:
            json.dump({"enabled": True}, f)

    with open(PANEL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_panel(enabled):
    with open(PANEL_FILE, "w", encoding="utf-8") as f:
        json.dump({"enabled": enabled}, f, indent=4)


def load_applications():
    if not os.path.exists(APPLICATION_FILE):
        with open(APPLICATION_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

    with open(APPLICATION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_applications(data):
    with open(APPLICATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ================= EMBEDS ================= #

def requirements_embed():
    embed = discord.Embed(
        title="📝 Staff Applications",
        color=0x58A6FF
    )

    embed.description = (
        "**STAFF REQUIREMENTS**\n\n"
        "• Must be 13 or above\n"
        "• Must be active\n"
        "• Must be mature\n\n"
        "Select Staff Application below to apply."
    )

    embed.set_author(name=f"{SERVER_NAME} Staff Applications")
    return embed


def disabled_embed():
    return discord.Embed(
        title="❌ Applications Disabled",
        description="This panel has been disabled by an administrator.",
        color=discord.Color.red()
    )


def dm_closed_embed():
    return discord.Embed(
        title="❌ DMs Closed",
        description="Please enable your DMs and try again.",
        color=discord.Color.red()
    )


def started_embed():
    return discord.Embed(
        title="✅ Application Started",
        description="Check your DMs.",
        color=discord.Color.green()
    )


# ================= APPLICATION QUESTIONS ================= #

async def ask_question(user, question):
    embed = discord.Embed(
        title="📝 Staff Application",
        description=question,
        color=discord.Color.blurple()
    )

    try:
        await user.send(embed=embed)
    except discord.Forbidden:
        return None

    def check(message):
        return message.author.id == user.id and isinstance(message.channel, discord.DMChannel)

    try:
        msg = await bot.wait_for("message", timeout=600, check=check)
        return msg.content
    except asyncio.TimeoutError:
        return None


async def run_application(interaction: discord.Interaction):
    answers = []

    for question in QUESTIONS:
        answer = await ask_question(interaction.user, question)
        if answer is None:
            try:
                await interaction.user.send(
                    embed=discord.Embed(
                        title="❌ Application Cancelled",
                        description="You took too long to answer or DMs are closed.",
                        color=discord.Color.red()
                    )
                )
            except discord.Forbidden:
                pass
            return

        answers.append(answer)

    data = load_applications()
    data[str(interaction.user.id)] = {
        "user_id": interaction.user.id,
        "answers": answers,
        "status": "pending"
    }
    save_applications(data)

    channel = bot.get_channel(APPLICATION_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(APPLICATION_CHANNEL_ID)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

    application_embed = discord.Embed(
        title="📝 New Staff Application",
        color=discord.Color.blurple()
    )

    application_embed.add_field(
        name="Applicant",
        value=f"{interaction.user.mention}\nID: {interaction.user.id}",
        inline=False
    )

    for index, answer in enumerate(answers):
        question_text = QUESTIONS[index]
        application_embed.add_field(
            name=question_text[:256],
            value=answer[:1024],
            inline=False
        )

    application_embed.set_footer(text=f"Applicant ID: {interaction.user.id}")

    await channel.send(
        embed=application_embed,
        view=ReviewView(interaction.user.id)
    )

    try:
        await interaction.user.send(
            embed=discord.Embed(
                title="✅ Application Submitted",
                description="Your application has been submitted.",
                color=discord.Color.green()
            )
        )
    except discord.Forbidden:
        pass


# ================= DROPDOWN ================= #

class ApplicationSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Staff Application",
                description=f"Apply for {SERVER_NAME} Staff",
                emoji="📝"
            )
        ]

        super().__init__(
            placeholder="Choose an application...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        panel = load_panel()

        if not panel.get("enabled", True):
            await interaction.response.send_message(
                embed=disabled_embed(),
                ephemeral=True
            )
            return

        try:
            await interaction.user.send(
                embed=discord.Embed(
                    title="📨 Staff Application",
                    description="Your application will begin shortly.",
                    color=discord.Color.blurple()
                )
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=dm_closed_embed(),
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=started_embed(),
            ephemeral=True
        )

        await run_application(interaction)


class ApplicationView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationSelect())


# ================= ACCEPT / DENY BUTTONS ================= #

class AcceptButton(Button):
    def __init__(self, applicant_id):
        super().__init__(
            label="Accept",
            emoji="✅",
            style=discord.ButtonStyle.green
        )
        self.applicant_id = applicant_id

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "This can only be used in a server.",
                ephemeral=True
            )
            return

        member = guild.get_member(self.applicant_id)
        if member is None:
            try:
                member = await guild.fetch_member(self.applicant_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                await interaction.response.send_message(
                    "Applicant not found.",
                    ephemeral=True
                )
                return

        for role_id in ACCEPT_ROLES:
            role = guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Application accepted")
                except discord.Forbidden:
                    pass

        try:
            await member.send(
                embed=discord.Embed(
                    title="✅ Application Accepted",
                    description=f"You have been accepted in **{guild.name}**.",
                    color=discord.Color.green()
                )
            )
        except discord.Forbidden:
            pass

        embed = interaction.message.embeds[0].copy()
        embed.color = discord.Color.green()
        embed.add_field(
            name="Result",
            value=f"✅ Accepted by {interaction.user.mention}",
            inline=False
        )

        await interaction.message.edit(embed=embed, view=None)

        data = load_applications()
        if str(self.applicant_id) in data:
            data[str(self.applicant_id)]["status"] = "accepted"
            save_applications(data)

        if not interaction.response.is_done():
            await interaction.response.send_message("Application accepted.", ephemeral=True)


class DenyButton(Button):
    def __init__(self, applicant_id):
        super().__init__(
            label="Deny",
            emoji="❌",
            style=discord.ButtonStyle.red
        )
        self.applicant_id = applicant_id

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "This can only be used in a server.",
                ephemeral=True
            )
            return

        member = guild.get_member(self.applicant_id)
        if member is None:
            try:
                member = await guild.fetch_member(self.applicant_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                member = None

        if member:
            try:
                await member.send(
                    embed=discord.Embed(
                        title="❌ Application Denied",
                        description=f"Your application in **{guild.name}** was denied.",
                        color=discord.Color.red()
                    )
                )
            except discord.Forbidden:
                pass

        embed = interaction.message.embeds[0].copy()
        embed.color = discord.Color.red()
        embed.add_field(
            name="Result",
            value=f"❌ Denied by {interaction.user.mention}",
            inline=False
        )

        await interaction.message.edit(embed=embed, view=None)

        data = load_applications()
        if str(self.applicant_id) in data:
            data[str(self.applicant_id)]["status"] = "denied"
            save_applications(data)

        if not interaction.response.is_done():
            await interaction.response.send_message("Application denied.", ephemeral=True)


class ReviewView(View):
    def __init__(self, applicant_id):
        super().__init__(timeout=None)
        self.add_item(AcceptButton(applicant_id))
        self.add_item(DenyButton(applicant_id))


# ================= BOT SETUP ================= #

class MyBot(commands.Bot):
    async def setup_hook(self):
        self.add_view(ApplicationView())
        synced = await self.tree.sync()
        print(f"Synced {len(synced)} slash commands.")


bot = MyBot(command_prefix="!", intents=intents)


# ================= PANEL COMMANDS ================= #

@bot.tree.command(name="application_panel", description="Send the application panel")
@app_commands.checks.has_permissions(administrator=True)
async def application_panel(interaction: discord.Interaction):
    if interaction.channel is None:
        await interaction.response.send_message(
            "This command must be used in a channel.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    await interaction.channel.send(
        embed=requirements_embed(),
        view=ApplicationView()
    )

    await interaction.followup.send("✅ Panel sent.", ephemeral=True)


@bot.tree.command(name="panel", description="Alias for application_panel")
@app_commands.checks.has_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    await application_panel(interaction)


@bot.tree.command(name="enablepanel", description="Enable applications")
@app_commands.checks.has_permissions(administrator=True)
async def enablepanel(interaction: discord.Interaction):
    save_panel(True)
    await interaction.response.send_message(
        embed=discord.Embed(
            title="✅ Panel Enabled",
            description="Applications are now open.",
            color=discord.Color.green()
        ),
        ephemeral=True
    )


@bot.tree.command(name="disablepanel", description="Disable applications")
@app_commands.checks.has_permissions(administrator=True)
async def disablepanel(interaction: discord.Interaction):
    save_panel(False)
    await interaction.response.send_message(
        embed=discord.Embed(
            title="❌ Panel Disabled",
            description="Applications are now closed.",
            color=discord.Color.red()
        ),
        ephemeral=True
    )


# ================= APPLICATION COMMANDS ================= #

@app_commands.describe(user="Applicant to accept")
@bot.tree.command(name="application_accept", description="Accept an application")
@app_commands.checks.has_permissions(administrator=True)
async def application_accept(interaction: discord.Interaction, user: discord.Member):
    if interaction.guild is None:
        await interaction.response.send_message(
            "This command can only be used in a server.",
            ephemeral=True
        )
        return

    for role_id in ACCEPT_ROLES:
        role = interaction.guild.get_role(role_id)
        if role:
            try:
                await user.add_roles(role, reason="Application accepted")
            except discord.Forbidden:
                pass

    data = load_applications()
    if str(user.id) in data:
        data[str(user.id)]["status"] = "accepted"
        save_applications(data)

    try:
        await user.send(
            embed=discord.Embed(
                title="✅ Application Accepted",
                description=f"You have been accepted in **{interaction.guild.name}**.",
                color=discord.Color.green()
            )
        )
    except discord.Forbidden:
        pass

    await interaction.response.send_message(
        embed=discord.Embed(
            title="✅ Accepted",
            description=f"{user.mention} has been accepted.",
            color=discord.Color.green()
        ),
        ephemeral=True
    )


@app_commands.describe(user="Applicant to deny")
@bot.tree.command(name="application_deny", description="Deny an application")
@app_commands.checks.has_permissions(administrator=True)
async def application_deny(interaction: discord.Interaction, user: discord.Member):
    if interaction.guild is None:
        await interaction.response.send_message(
            "This command can only be used in a server.",
            ephemeral=True
        )
        return

    data = load_applications()
    if str(user.id) in data:
        data[str(user.id)]["status"] = "denied"
        save_applications(data)

    try:
        await user.send(
            embed=discord.Embed(
                title="❌ Application Denied",
                description=f"Your application in **{interaction.guild.name}** was denied.",
                color=discord.Color.red()
            )
        )
    except discord.Forbidden:
        pass

    await interaction.response.send_message(
        embed=discord.Embed(
            title="❌ Denied",
            description=f"{user.mention} has been denied.",
            color=discord.Color.red()
        ),
        ephemeral=True
    )


# ================= ERROR HANDLER ================= #

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = "You do not have permission to use this command."
    else:
        msg = f"An error occurred: {error}"

    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


# ================= RUN BOT ================= #

if TOKEN:
    bot.run(TOKEN)
else:
    raise RuntimeError("DISCORD_TOKEN environment variable is not set.")
