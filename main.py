import os
import discord
from discord.ext import commands
import asyncio
import difflib
from collections import defaultdict
from datetime import datetime, timedelta

GIF_BANNER = "https://media.discordapp.net/attachments/1479835854435520607/1480074101304463473/standard_7.gif"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix=",",
    intents=intents,
    help_command=None
)

# ================= CONFIG LOGS ================= #

logs_config = {}

# ================= PERMISSÃO MOD ================= #

def is_moderator():
    async def predicate(ctx):
        perms = ctx.author.guild_permissions
        if perms.administrator or perms.manage_messages or perms.manage_guild:
            return True
        await ctx.send("❌ Apenas moderadores podem usar o bot.")
        return False
    return commands.check(predicate)

# ================= ANTI SPAM ================= #

spam_tracker = defaultdict(list)

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    now = datetime.now()
    spam_tracker[message.author.id].append(now)

    spam_tracker[message.author.id] = [
        t for t in spam_tracker[message.author.id]
        if now - t < timedelta(seconds=5)
    ]

    if len(spam_tracker[message.author.id]) > 5:
        try:
            await message.delete()
            await message.channel.send(
                f"{message.author.mention} ⚠️ Pare de spammar.",
                delete_after=3
            )
        except:
            pass

    await bot.process_commands(message)

# ================= READY ================= #

@bot.event
async def on_ready():
    print(f"Bot online {bot.user}")

# ================= HELP ================= #

@bot.command()
@is_moderator()
async def help(ctx):

    embed = discord.Embed(
        title="⚙️ Painel Oficial de Moderação",
        description="Sistema avançado com proteção e controle.",
        color=0x000000
    )

    embed.set_author(
        name=bot.user.name,
        icon_url=bot.user.display_avatar.url
    )

    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_image(url=GIF_BANNER)

    embed.add_field(
        name="🔨 Moderação",
        value=(
            "`,ban @user motivo`\n"
            "`,kick @user motivo`\n"
            "`,mute @user 10m`\n"
            "`,unmute @user`\n"
            "`,clear 10`\n"
            "`,lock`\n"
            "`,unlock`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️ Utilidades",
        value="`,msg texto` → Bot envia mensagem personalizada.",
        inline=False
    )

    embed.add_field(
        name=" Sistema",
        value="Anti-Spam automático ativo.",
        inline=False
    )

    embed.set_footer(
        text="Vitrine Games BR • 2026 | Made by patrocinadobet1",
        icon_url=bot.user.display_avatar.url
    )

    await ctx.send(embed=embed)

# ================= MODERAÇÃO ================= #

@bot.command()
@is_moderator()
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member.mention} foi banido.")

@bot.command()
@is_moderator()
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member.mention} foi expulso.")

@bot.command()
@is_moderator()
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 {amount} mensagens apagadas.")
    await asyncio.sleep(3)
    await msg.delete()

# ================= MUTE ================= #

@bot.command()
@is_moderator()
async def mute(ctx, member: discord.Member, tempo: str):

    try:
        unidade = tempo[-1]
        valor = int(tempo[:-1])
        conversao = {"s":1, "m":60, "h":3600}
        segundos = valor * conversao[unidade]
    except:
        return await ctx.send("⚠️ Use formato correto: 10s, 5m ou 1h")

    role = discord.utils.get(ctx.guild.roles, name="Muted")

    if not role:
        role = await ctx.guild.create_role(name="Muted")

        for channel in ctx.guild.channels:
            await channel.set_permissions(role, send_messages=False, speak=False)

    await member.add_roles(role)
    await ctx.send(f"🔇 {member.mention} mutado por {tempo}")

    await asyncio.sleep(segundos)

    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"🔊 {member.mention} foi desmutado.")

@bot.command()
@is_moderator()
async def unmute(ctx, member: discord.Member):

    role = discord.utils.get(ctx.guild.roles, name="Muted")

    if role and role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"🔊 {member.mention} foi desmutado.")

# ================= LOCK ================= #

@bot.command()
@is_moderator()
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Canal trancado.")

@bot.command()
@is_moderator()
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Canal destrancado.")

# ================= MSG ================= #

@bot.command()
@is_moderator()
async def msg(ctx, *, texto):
    await ctx.message.delete()
    await ctx.send(texto)

# ================= SETUP LOGS ================= #

@bot.command()
@is_moderator()
async def setuplogs(ctx, canal: discord.TextChannel, tipo: str):

    if tipo not in ["entrada", "saida"]:
        return await ctx.send("Use: `,setuplogs #canal entrada` ou `,setuplogs #canal saida`")

    logs_config[ctx.guild.id] = {
        "channel": canal.id,
        "color": 0x000000,
        "modal_data": {
            "titulo": "📢 Log do Servidor",
            "descricao": "{user} entrou no servidor!",
            "gif": GIF_BANNER,
            "tipo": tipo
        }
    }

    await ctx.send(f"✅ Logs configurados em {canal.mention} para **{tipo}**.")

# ================= EVENTOS LOG ================= #

@bot.event
async def on_member_join(member):

    if member.guild.id not in logs_config:
        return

    cfg = logs_config[member.guild.id]

    if cfg["modal_data"]["tipo"] != "entrada":
        return

    canal = member.guild.get_channel(cfg["channel"])

    desc = cfg["modal_data"]["descricao"].replace("{user}", member.mention)

    embed = discord.Embed(
        title=cfg["modal_data"]["titulo"],
        description=desc,
        color=cfg["color"],
        timestamp=datetime.utcnow()
    )

    embed.set_author(name=str(member), icon_url=member.display_avatar.url)
    embed.set_image(url=cfg["modal_data"]["gif"])

    await canal.send(embed=embed)

@bot.event
async def on_member_remove(member):

    if member.guild.id not in logs_config:
        return

    cfg = logs_config[member.guild.id]

    if cfg["modal_data"]["tipo"] != "saida":
        return

    canal = member.guild.get_channel(cfg["channel"])

    desc = cfg["modal_data"]["descricao"].replace("{user}", member.mention)

    embed = discord.Embed(
        title=cfg["modal_data"]["titulo"],
        description=desc,
        color=cfg["color"],
        timestamp=datetime.utcnow()
    )

    embed.set_author(name=str(member), icon_url=member.display_avatar.url)
    embed.set_image(url=cfg["modal_data"]["gif"])

    await canal.send(embed=embed)

# ================= TESTLOG ================= #

@bot.command()
@is_moderator()
async def testlog(ctx):

    if ctx.guild.id not in logs_config:
        return await ctx.send("❌ Use `,setuplogs` primeiro.")

    cfg = logs_config[ctx.guild.id]
    canal = ctx.guild.get_channel(cfg["channel"])

    desc = cfg["modal_data"]["descricao"].replace("{user}", ctx.author.mention)

    embed = discord.Embed(
        title=cfg["modal_data"]["titulo"],
        description=desc,
        color=cfg["color"],
        timestamp=datetime.utcnow()
    )

    embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
    embed.set_image(url=cfg["modal_data"]["gif"])

    await canal.send(embed=embed)
    await ctx.send("✅ Log de teste enviado.")

# ================= CALL ================= #

voice_channel_247 = None

@bot.command()
@is_moderator()
async def call(ctx):

    if not ctx.author.voice:
        return await ctx.send("❌ Entre em um canal de voz primeiro.")

    canal = ctx.author.voice.channel

    try:

        if ctx.voice_client:
            await ctx.voice_client.move_to(canal)
        else:
            await canal.connect()

        await ctx.send(f"🎧 Conectado em **{canal.name}**")

    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

# ================= DESCONECT ================= #

@bot.command()
@is_moderator()
async def desconect(ctx):

    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Saí do canal de voz.")
    else:
        await ctx.send("❌ Não estou em nenhum canal.")

# ================= START ================= #

token = os.getenv("TOKEN")

if not token:
    print("TOKEN NÃO ENCONTRADO")
else:
    print("TOKEN OK")

bot.run(token)
