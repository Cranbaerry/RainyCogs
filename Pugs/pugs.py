import aiohttp
import asyncio
import discord
import gspread_asyncio
from aiohttp.web_exceptions import HTTPError
from redbot.core import commands
from redbot.core.data_manager import cog_data_path
from google.oauth2.service_account import Credentials

class Pugs(commands.Cog):
    """My custom cog test 2"""

    def __init__(self, bot):
        self.bot = bot
        self.path = str(cog_data_path(self)).replace("\\", "/")
        self.credentials = self.path + '/My First Project-162dbc0aa595.json'

        # Create an AsyncioGspreadClientManager object which
        # will give us access to the Spreadsheet API.
        self.agcm = gspread_asyncio.AsyncioGspreadClientManager(self.get_creds)

    # First, set up a callback function that fetches our credentials off the disk.
    # gspread_asyncio needs this to re-authenticate when credentials expire.
    def get_creds(self):
        # To obtain a service account JSON file, follow these steps:
        # https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account
        creds = Credentials.from_service_account_file(self.credentials)
        scoped = creds.with_scopes([
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ])
        return scoped

    def parseRole(self, role):
        return {
            # -1: Invalid role name
            #  0: No input is given

            'tank': 1,
            'dps': 2,
            'damage': 2,
            'healer': 3,
            'support': 3,
        }.get(role.lower(), -1) if role is not None else 0

    def getRoleName(self, type):
        return {
            0: 'Tidak ada',
            1: 'Tank',
            2: 'DPS',
            3: 'Support'
        }.get(type, None)

    @commands.command()
    async def daftar(self, ctx, battletag, primaryRole, secondaryRole = None):
        """
            Command untuk registrasi PUG Overwatch Indonesia

            `battletag` **Case-sensitive**, perkatikan kapitalizasi huruf
            `primaryRole` Role utama yang mau dimainkan **(wajib di-isi)**
            `secondaryRole` Role lain (kosongkan jika tidak ada)

             [role options: **Tank**, **DPS**, **Support**]
        """
        primaryRoleType = self.parseRole(primaryRole)
        secondaryRoleType = self.parseRole(secondaryRole)

        if primaryRoleType == -1 or secondaryRoleType == -1:
            embed = discord.Embed(color=0xEE2222, title="Invalid role for %s" % battletag)
            embed.description = "Role yang tersedia: **Tank**, **DPS**, **Support**"
            embed.add_field(name='Primary role', value=str(self.getRoleName(primaryRoleType)), inline=True)
            embed.add_field(name='Secondary role', value=str(self.getRoleName(secondaryRoleType)), inline=True)
            embed.set_author(name='Pick-Up Games Registration', icon_url='https://i.imgur.com/kgrkybF.png')
            await ctx.send(content=ctx.message.author.mention, embed=embed)
            return

        url = 'https://ow-api.com/v1/stats/pc/us/%s/profile' % (battletag.replace("#", "-"))
        hdr = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)' }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=hdr) as resp:
                data = await resp.json()

        try:
            if resp.status == 404:
                embed = discord.Embed(color=0xEE2222, title="Profile **%s** tidak dapat ditemukan" % battletag)
                embed.description = "Coba periksa kapitalisasi huruf dan coba lagi."
                embed.set_author(name='Pick-Up Games Registration', icon_url='https://i.imgur.com/kgrkybF.png')
                await ctx.send(content=ctx.message.author.mention, embed=embed)
                return

            if data['private']:
                embed = discord.Embed(color=0xEE2222, title="Additional data is required")
                embed.description = "Dikarenakan profile kamu private, kami tidak bisa mengakses data SR kamu dari situs Blizzard. Balas chat ini dengan **link screenshot** career profile account kamu agar bisa diproses.\n\nUpload screenshotnya bisa dilakukan dengan [imgur.com](https://discordapp.com), [imgbb.com](https://imgbb.com), atau situs hosting gambar lainnya.\n\nKamu mempunyai waktu **2 menit** untuk membalas pesan ini."
                embed.set_author(name='Pick-Up Games Registration', icon_url='https://i.imgur.com/kgrkybF.png')
                embed.set_footer(text='Gambar 1.0: contoh screenshot')
                embed.set_image(url='https://i.imgur.com/Im8NpgX.png')

                message = await ctx.send("%s Cek DM untuk instruksi lebih lanjut." % ctx.message.author.mention)
                await ctx.author.send(embed=embed)
                try:
                    response = await ctx.bot.wait_for(
                        "message", check=lambda m: m.author == ctx.message.author, timeout=120
                    )
                except asyncio.TimeoutError:
                    await ctx.author.send("Your response has timed out, please try again.")
                    return None

                await message.delete()

            report_line = [ctx.message.created_at.strftime("%d/%m/%Y %H:%M:%S"),  str(ctx.author), battletag, self.getRoleName(primaryRoleType), self.getRoleName(secondaryRoleType), response.content if data['private'] else ''.join("{}: {}, ".format(i['role'].capitalize(), i['level']) for i in data['ratings'])[:-2]]

            # Always authorize first.
            # If you have a long-running program call authorize() repeatedly.
            agc = await self.agcm.authorize()
            sheet = await agc.open_by_url("https://docs.google.com/spreadsheets/d/1PaegW6jKcLcyEMOtsNQR1SXoabgf46U37Jh_CkfxeMU/edit")
            worksheet = await sheet.get_worksheet(0)
            await worksheet.append_row(report_line, value_input_option='USER_ENTERED')

            embed = discord.Embed(color=0xEE2222, title=battletag, timestamp=ctx.message.created_at, url='https://playoverwatch.com/en-us/career/pc/%s/'% (battletag.replace("#", "-")))
            embed.description="Telah berhasil terdaftar."
            embed.add_field(name='Skill Ratings', value='*Private*' if data['private'] else ''.join("{}: **{}**\n".format(i['role'].capitalize(), i['level']) for i in data['ratings']))
            embed.add_field(name='Roles', value='Primary: **%s**\nSecondary: **%s**' % (self.getRoleName(primaryRoleType), self.getRoleName(secondaryRoleType)))
            embed.set_thumbnail(url=data['icon'])
            embed.set_author(name='Pick-Up Games Registration', icon_url='https://i.imgur.com/kgrkybF.png')
            await ctx.send(content=ctx.message.author.mention, embed=embed)
        except Exception as err:
            await ctx.send(content='Terjadi kesalahan. Mohon contact admin.')