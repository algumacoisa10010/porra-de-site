import os
import discord
from discord.ext import commands
import asyncio
import difflib
from collections import defaultdict
from datetime import datetime, timedelta

# ================= CONFIG ================= #

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

# Armazenamento simples em memória (para produção, salvar em JSON/DB)
logs_config = {}  # { guild_id: { "channel": int, "color": int, "modal_data": {titulo, descricao, gif, tipo} } }

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
    print(f"Bot online como {bot.user}")

# ================= HELP ================= #

@bot.command()
@is_moderator()
async def help(ctx):
    embed = discord.Embed(
        title="⚙️ Painel Oficial de Moderação",
        description="Sistema de moderação, embeds, logs e voz.",
        color=0x000000
    )

    embed.set_author(name=bot.user.name, icon_url=bot.user.display_avatar.url)
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
        value=(
            "`,msg texto`\n"
            "`,setupembed`\n"
            "`,setuplogs`\n"
            "`,testlog`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎧 Voz",
        value="`,call` (entra no seu canal)\n`,call ID`\n`,desconect`",
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

# ================= SETUP EMBED ================= #

class EmbedModal(discord.ui.Modal, title="Criar Embed"):
    titulo = discord.ui.TextInput(label="Título")
    descricao = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph)
    banner = discord.ui.TextInput(label="URL do Banner")

    def __init__(self, cor):
        super().__init__()
        self.cor = cor

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=self.titulo.value,
            description=self.descricao.value,
            color=self.cor
        )
        embed.set_image(url=self.banner.value)

        await interaction.response.send_message("✅ Embed criada!", ephemeral=True)
        await interaction.channel.send(embed=embed)

class CorSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Preto", emoji="⚫", value="preto"),
            discord.SelectOption(label="Azul", emoji="🔵", value="azul"),
            discord.SelectOption(label="Verde", emoji="🟢", value="verde"),
            discord.SelectOption(label="Vermelho", emoji="🔴", value="vermelho"),
            discord.SelectOption(label="Roxo", emoji="🟣", value="roxo")
        ]
        super().__init__(placeholder="Escolha a cor da embed", options=options)

    async def callback(self, interaction: discord.Interaction):
        cores = {
            "preto": 0x000000,
            "azul": discord.Color.blue(),
            "verde": discord.Color.green(),
            "vermelho": discord.Color.red(),
            "roxo": discord.Color.purple()
        }
        await interaction.response.send_modal(EmbedModal(cores[self.values[0]]))

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(CorSelect())

@bot.command()
@is_moderator()
async def setupembed(ctx):
    embed = discord.Embed(
        title="🛠 Criador de Embed",
        description="Selecione a cor da embed.",
        color=0x000000
    )
    await ctx.send(embed=embed, view=SetupView())

# ================= SETUP LOGS ================= #

class LogsModal(discord.ui.Modal, title="Configurar Logs"):
    titulo = discord.ui.TextInput(label="Título")
    descricao = discord.ui.TextInput(
        label="Descrição (use {user})",
        style=discord.TextStyle.paragraph
    )
    gif = discord.ui.TextInput(label="URL do GIF")
    canal = discord.ui.TextInput(label="ID do canal")
    tipo = discord.ui.TextInput(label="Tipo: entrada ou saida")

    def __init__(self, cor):
        super().__init__()
        self.cor = cor

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id

        try:
            canal_id = int(self.canal.value)
        except:
            return await interaction.response.send_message("❌ ID inválido.", ephemeral=True)

        logs_config[guild_id] = {
            "channel": canal_id,
            "color": self.cor,
            "modal_data": {
                "titulo": self.titulo.value,
                "descricao": self.descricao.value,
                "gif": self.gif.value,
                "tipo": self.tipo.value.lower()
            }
        }

        await interaction.response.send_message("✅ Logs configurados!", ephemeral=True)

class LogsColorSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Preto", value="preto", emoji="⚫"),
            discord.SelectOption(label="Azul", value="azul", emoji="🔵"),
            discord.SelectOption(label="Verde", value="verde", emoji="🟢"),
            discord.SelectOption(label="Vermelho", value="vermelho", emoji="🔴"),
            discord.SelectOption(label="Roxo", value="roxo", emoji="🟣"),
        ]
        super().__init__(placeholder="Escolha a cor da embed", options=options)

    async def callback(self, interaction: discord.Interaction):
        cores = {
            "preto": 0x000000,
            "azul": discord.Color.blue(),
            "verde": discord.Color.green(),
            "vermelho": discord.Color.red(),
            "roxo": discord.Color.purple()
        }
        await interaction.response.send_modal(LogsModal(cores[self.values[0]]))

class LogsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(LogsColorSelect())

@bot.command()
@is_moderator()
async def setuplogs(ctx):
    embed = discord.Embed(
        title="⚙️ Configuração de Logs",
        description="Escolha a cor e depois preencha o formulário.\nUse `{user}` na descrição.",
        color=0x000000
    )
    await ctx.send(embed=embed, view=LogsView())

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

# ================= VOZ ================= #

@bot.command()
@is_moderator()
async def call(ctx, canal_id: int = None):

    # pegar canal
    if canal_id:
        canal = bot.get_channel(canal_id)

        if canal is None or not isinstance(canal, discord.VoiceChannel):
            return await ctx.send("❌ Canal de voz não encontrado.")

    else:
        if ctx.author.voice is None:
            return await ctx.send("❌ Você precisa estar em um canal de voz.")

        canal = ctx.author.voice.channel

    try:

        # se já estiver conectado
        if ctx.voice_client:

            # se já estiver no mesmo canal
            if ctx.voice_client.channel.id == canal.id:
                return await ctx.send(f"✅ Já estou conectado em **{canal.name}**")

            # mover para outro canal
            await ctx.voice_client.move_to(canal)
            await ctx.send(f"🔁 Movido para **{canal.name}**")

        else:
            # conectar
            await canal.connect(timeout=60, reconnect=True)
            await ctx.send(f"🎧 Conectado em **{canal.name}**")

    except Exception as e:
        await ctx.send(f"❌ Erro ao conectar:\n```{e}```")


@bot.command()
@is_moderator()
async def desconect(ctx):

    if ctx.voice_client:

        try:
            await ctx.voice_client.disconnect()
            await ctx.send("👋 Desconectado do canal de voz.")

        except Exception as e:
            await ctx.send(f"❌ Erro ao sair:\n```{e}```")

    else:
        await ctx.send("❌ Não estou em nenhum canal de voz.")

# ================= ERROS ================= #

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        comandos = [c.name for c in bot.commands]
        sugestao = difflib.get_close_matches(ctx.invoked_with, comandos, n=1, cutoff=0.5)
        if sugestao:
            await ctx.send(f"Você quis dizer `,{sugestao[0]}` ❓")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Argumento faltando.")

    if isinstance(error, commands.BadArgument):
        await ctx.send("⚠️ Argumento inválido.")

# ================= START ================= #

token = os.getenv("TOKEN")

if not token:
    print("TOKEN NÃO ENCONTRADO")
else:
    print("TOKEN OK")

bot.run(token)

