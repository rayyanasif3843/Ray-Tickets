import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button
import os
import json
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")

APPLICATION_CHANNEL_ID = 1523666394963775661

ACCEPT_ROLES = [
    1523667690319773746,
    1523667358655189012
]

QUESTIONS = [
    "Why do you want to be a mod in Brainrot University? (3+ sentences)",
    "How old are you?",
    "Do you have any experience of moderation?",
    "2 members are fighting aggressively, and they are not listening to you. What would you do here?",
    "What will you do if you see two staff members fighting?",
    "Will u get 800 weekly messages in ur first week?",
    "How are u gonna be a better moderator then others? (3+ sentences)",
    "Do u got anything else to say?"
]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

PANEL_FILE = "panel.json"
APPLICATION_FILE = "applications.json"


# ================= FILE FUNCTIONS ================= #

def load_panel():
    if not os.path.exists(PANEL_FILE):
        with open(PANEL_FILE, "w") as f:
            json.dump({"enabled": True}, f)

    with open(PANEL_FILE, "r") as f:
        return json.load(f)


def save_panel(enabled):
    with open(PANEL_FILE, "w") as f:
        json.dump({"enabled": enabled}, f)


def load_applications():
    if not os.path.exists(APPLICATION_FILE):
        with open(APPLICATION_FILE, "w") as f:
            json.dump({}, f)

    with open(APPLICATION_FILE, "r") as f:
        return json.load(f)


def save_applications(data):
    with open(APPLICATION_FILE, "w") as f:
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

    embed.set_author(name="Staff Applications")
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

    await user.send(embed=embed)

    def check(message):
        return (
            message.author.id == user.id and
            isinstance(message.channel, discord.DMChannel)
        )

    try:
        msg = await bot.wait_for(
            "message",
            timeout=600,
            check=check
        )
        return msg.content

    except asyncio.TimeoutError:
        return None


async def run_application(interaction: discord.Interaction):
    answers = []

    for question in QUESTIONS:
        answer = await ask_question(interaction.user, question)

        if answer is None:
            embed = discord.Embed(
                title="❌ Application Cancelled",
                description="You took too long to answer.",
                color=discord.Color.red()
            )
            await interaction.user.send(embed=embed)
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
        application_embed.add_field(
            name=QUESTIONS[index],
            value=answer,
            inline=False
        )

    application_embed.set_footer(text=f"Applicant ID: {interaction.user.id}")

    await channel.send(
        embed=application_embed,
        view=ReviewView(interaction.user.id)
    )

    success_embed = discord.Embed(
        title="✅ Application Submitted",
        description="Your application has been submitted.",
        color=discord.Color.green()
    )

    await interaction.user.send(embed=success_embed)


# ================= DROPDOWN ================= #

class ApplicationSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Staff Application",
                description="Apply for Staff",
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

        if not panel["enabled"]:
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
        if not member:
            await interaction.response.send_message(
                "Applicant not found.",
                ephemeral=True
            )
            return

        for role_id in ACCEPT_ROLES:
            role = guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role)
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

        embed = interaction.message.embeds[0]
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

        await interaction.response.send_message(
            "Application accepted.",
            ephemeral=True
        )


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

        embed = interaction.message.embeds[0]
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

        await interaction.response.send_message(
            "Application denied.",
            ephemeral=True
        )


class ReviewView(View):
    def __init__(self, applicant_id):
        super().__init__(timeout=None)
        self.add_item(AcceptButton(applicant_id))
        self.add_item(DenyButton(applicant_id))


# ================= PANEL COMMANDS ================= #

@bot.tree.command(
    name="panel",
    description="Send application panel"
)
@app_commands.checks.has_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    await interaction.channel.send(
        embed=requirements_embed(),
        view=ApplicationView()
    )
    await interaction.response.send_message(
        "✅ Panel sent.",
        ephemeral=True
    )


@bot.tree.command(
    name="enablepanel",
    description="Enable applications"
)
@app_commands.checks.has_permissions(administrator=True)
async def enablepanel(interaction: discord.Interaction):
    save_panel(True)
    await interaction.response.send_message(
        embed=discord.Embed(
            title="✅ Panel Enabled",
            description="Applications are now open.",
            color=discord.Color.green()
        )
    )


@bot.tree.command(
    name="disablepanel",
    description="Disable applications"
)
@app_commands.checks.has_permissions(administrator=True)
async def disablepanel(interaction: discord.Interaction):
    save_panel(False)
    await interaction.response.send_message(
        embed=discord.Embed(
            title="❌ Panel Disabled",
            description="Applications are now closed.",
            color=discord.Color.red()
        )
    )


# ================= APPLICATION COMMANDS ================= #

@app_commands.describe(user="Applicant to accept")
@bot.tree.command(
    name="accept_application",
    description="Accept an application"
)
@app_commands.checks.has_permissions(administrator=True)
async def accept_application(
    interaction: discord.Interaction,
    user: discord.Member
):
    for role_id in ACCEPT_ROLES:
        role = interaction.guild.get_role(role_id)
        if role:
            await user.add_roles(role)

    data = load_applications()
    if str(user.id) in data:
        data[str(user.id)]["status"] = "accepted"
        save_applications(data)

    try:
        embed = discord.Embed(
            title="✅ Application Accepted",
            description=f"You have been accepted in **{interaction.guild.name}**.",
            color=discord.Color.green()
        )
        await user.send(embed=embed)
    except discord.Forbidden:
        pass

    await interaction.response.send_message(
        embed=discord.Embed(
            title="✅ Accepted",
            description=f"{user.mention} has been accepted.",
            color=discord.Color.green()
        )
    )


@app_commands.describe(user="Applicant to deny")
@bot.tree.command(
    name="deny_application",
    description="Deny an application"
)
@app_commands.checks.has_permissions(administrator=True)
async def deny_application(
    interaction: discord.Interaction,
    user: discord.Member
):
    data = load_applications()
    if str(user.id) in data:
        data[str(user.id)]["status"] = "denied"
        save_applications(data)

    try:
        embed = discord.Embed(
            title="❌ Application Denied",
            description=f"Your application in **{interaction.guild.name}** was denied.",
            color=discord.Color.red()
        )
        await user.send(embed=embed)
    except discord.Forbidden:
        pass

    await interaction.response.send_message(
        embed=discord.Embed(
            title="❌ Denied",
            description=f"{user.mention} has been denied.",
            color=discord.Color.red()
        )
    )


# ================= READY EVENT ================= #

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(e)

    print(f"Logged in as {bot.user}")


# ================= RUN BOT ================= #

if TOKEN:
    bot.run(TOKEN)
else:
    raise RuntimeError("DISCORD_TOKEN environment variable is not set.")
