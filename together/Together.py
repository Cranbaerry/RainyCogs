import logging
import discord
import websockets
import asyncio
from discordTogether import DiscordTogether
from redbot.core import commands

class Together(commands.Cog):
    # init method or constructor
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.log = logging.getLogger("red")
        self.togetherControl = DiscordTogether(self.bot)
        self.log.info("[together] Initialized")

    @commands.guild_only()
    @commands.group()
    async def together(self: commands.Cog, ctx: commands.Context) -> None:
        """
        Together commands
        """
        pass

    @together.command(aliases=["<youtube>"])
    @commands.guild_only()
    async def yt(self, ctx):
        """Generate an invite link to watch YouTube together"""
        if ctx.author.voice.channel:
            link = await self.togetherControl.create_link(ctx.author.voice.channel.id, 'youtube')
            await ctx.send(f"{ctx.message.author.mention} Click the blue link!\n{link}")
        else:
            await ctx.send(f"{ctx.message.author.mention} You have to be in a voice channel that is accessible to the bot.")

    @together.command()
    @commands.guild_only()
    async def poker(self, ctx):
        """Generate an invite link to play Poker together"""
        if ctx.author.voice.channel:
            link = await self.togetherControl.create_link(ctx.author.voice.channel.id, 'poker')
            await ctx.send(f"{ctx.message.author.mention} Click the blue link!\n{link}")
        else:
            await ctx.send(f"{ctx.message.author.mention} You have to be in a voice channel that is accessible to the bot.")

    @together.command()
    @commands.guild_only()
    async def betrayal(self, ctx):
        """Generate an invite link to play Betrayal together"""
        if ctx.author.voice.channel:
            link = await self.togetherControl.create_link(ctx.author.voice.channel.id, 'betrayal')
            await ctx.send(f"{ctx.message.author.mention} Click the blue link!\n{link}")
        else:
            await ctx.send(f"{ctx.message.author.mention} You have to be in a voice channel that is accessible to the bot.")

    @together.command()
    @commands.guild_only()
    async def fishing(self, ctx):
        """Generate an invite link to play Fishing together"""
        if ctx.author.voice.channel:
            link = await self.togetherControl.create_link(ctx.author.voice.channel.id, 'fishing')
            await ctx.send(f"{ctx.message.author.mention} Click the blue link!\n{link}")
        else:
            await ctx.send(f"{ctx.message.author.mention} You have to be in a voice channel that is accessible to the bot.")

    @together.command()
    @commands.guild_only()
    async def chess(self, ctx):
        """Generate an invite link to play Chess together"""
        if ctx.author.voice.channel:
            link = await self.togetherControl.create_link(ctx.author.voice.channel.id, 'chess')
            await ctx.send(f"{ctx.message.author.mention} Click the blue link!\n{link}")
        else:
            await ctx.send(f"{ctx.message.author.mention} You have to be in a voice channel that is accessible to the bot.")