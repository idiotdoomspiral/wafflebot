import asyncio
import time
import os
import discord
from discord import app_commands
from discord.ext import commands
from rich import print
from rich.console import Console
import httpx
from bs4 import BeautifulSoup as bs
import config
import helpers.embed
from helpers.utils import eval_pick
import strings.urls as Urls
import helpers.yar as yar

class DebridCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alldebrid = bot.debrid
        self.console = Console()

    @commands.command(
        name="deletetorrents",
        description="Delete x amount of old torrents.",
        brief="Delete x amount of old torrents.",
    )
    async def deletetorrents(self, ctx, *, num: int):
        async with httpx.AsyncClient() as resp:
            r = await resp.get(Urls.DEBRID_STATUS_READY)
            r = r.json()["data"]["magnets"]

        print(f"{len(r)} torrents cached.")
        mag_slice = []
        for torrent in r:
            mag_slice.append(torrent)
        mag_slice = mag_slice[-num:]
        ids = []
        for torrent in r:
            if torrent in mag_slice:
                ids.append(r[torrent]["id"])
        for i in ids:
            await self.alldebrid.delete_magnet(i)
            time.sleep(0.1)
        print(f"{num} old torrents deleted.")
        await ctx.reply(f"{num} old torrents deleted.")

    @commands.command(
        name="ready",
        description="Returns the number of cached torrents.",
        brief="Returns the number of cached torrents.",
    )
    async def ready(self, ctx):
        r = await self.alldebrid.get_all_magnet_status()
        print(f"{len(r)} cached torrents.")
        await ctx.send(f"{len(r)} torrents.\nThe limit is 1000.")

    @app_commands.command(
        name="magnet",
        description="Upload a magnet directly.",
    )
    async def mag(self, interaction: discord.Interaction, magnet: str):
        if magnet.startswith("magnet"):
            await interaction.response.defer(thinking=True)
            mag = await self.alldebrid.upload_magnets(magnet)
            print(f"Adding magnet for {mag[1]}")
            if mag[2]:
                embed = helpers.embed.download_ready(interaction.user, mag[1])
                print(f"{mag[1]} is ready.")
                dl_channel = await self.bot.fetch_channel(config.DL_CHANNEL)
                await dl_channel.send(embed=embed)
                await interaction.followup.send("Download ready and waiting!")
            else:
                data = [mag[0], "magnet", interaction.user.id, "magnet"]
                await DB().add_to_queue(data)
                print(f"{mag[1]} is not ready. Adding to queue.")
                await interaction.followup.send("It aint ready. Try !stat.")
        else:
            print(f"Invalid link recv'd: {magnet}")
            await interaction.response.send_message("Not a valid magnet link.")

    @commands.command(
        name="stat",
        description="Returns status of active torrents.",
        brief="Returns status of active torrents.",
    )
    async def stat(self, ctx):
        allstatus = []
        with open("queue.txt", "r") as f:
            queue = f.readlines()
        queue = [i.strip().split(",") for i in queue]
        for magnet in queue:
            magnet_status = self.alldebrid.get_magnet_status(magnet[0])
            allstatus.append({"filename":magnet_status["data"]["magnets"]["filename"], "size":magnet_status["data"]["magnets"]["size"], "seeders":magnet_status["data"]["magnets"]["seeders"], "speed":magnet_status["data"]["magnets"]["downloadSpeed"], "downloaded":magnet_status["data"]["magnets"]["downloaded"]})
        if len(allstatus) <= 0:
            await ctx.send("No active downloads.")
        else:
            try:
                embed = helpers.embed.debrid_status(allstatus)
                await ctx.reply(embed=embed, mention_author=False)
            except Exception as ex:
                print(f"Error Occurred: {ex}")
                await ctx.reply("Error occurred. Try again later.")

    @app_commands.command(
        name="m3u",
        description="generate playlist of debrid links for easy streaming in vlc",
    )
    async def m3u_gen(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        print("Generating M3U")
        exclude_files = ["txt", "../"]
        files = []
        async with httpx.AsyncClient() as resp:
            r = await resp.get(url)
        m3u_name = f"{url.split('/')[-2]}.m3u"
        # m3u_name = m3u_name
        soup = bs(r, "html.parser")
        for tag in soup.find_all("a"):
            if (
                tag.get("href")[-3:] in exclude_files
                or tag.get("href") in exclude_files
            ):
                continue

            files.append(f"{url}{tag.get('href')}\n")

        print(f"M3U List: {files}")
        print(f"File name: {m3u_name}")
        with open(f"tmp/{m3u_name}", "a") as f:
            for file in files:
                f.write(file)
        await interaction.followup.send(file=discord.File(f"tmp/{m3u_name}"))
        os.remove(f"tmp/{m3u_name}")
        print("Sent and removed M3U.")

    @commands.command(name="search", description="Search for torrents", brief="Search for torrents")
    async def search(self, ctx, *, query: str): # type: ignore
        try:
            results = yar.scrape_btsearch(query)

            if 'error' in results:
                await ctx.send(f"Error: {results['error']}")
                return
            
            embed = helpers.embed.torrent_results(results)
                
            e = await ctx.reply(embed=embed)

            def check(m):
                return m.author == ctx.author and m.content.startswith(
                    ("!pick", "!Pick", "!search")
                )

            try:
                not_ready = 0
                msg = await self.bot.wait_for("message", check=check, timeout=60)
                if not msg.content.startswith(("!pick", "!Pick")):
                    # await ctx.invoke(self.search, input=msg.content[8:])
                    await e.add_reaction("❌")
                elif msg.content.startswith("!pick"):
                    pick = eval_pick(msg.content.replace("!pick", "").strip())
                    pick = int(msg.content[6:]) - 1
                    if pick > 10:
                        await ctx.send("WRONG")
                    elif pick < 0:
                        await e.add_reaction("❌")
                    else:
                        dl_channel = await self.bot.fetch_channel(config.DL_CHANNEL)
                        magnet_link = list(results)[pick]["magnet_link"]
                        mag = self.alldebrid.upload_magnets(magnet_link)
                        if mag['data']['magnets'][0]['ready']:
                            embed = helpers.embed.download_ready(ctx.author.id, mag['data']['magnets'][0]['name'])
                            await dl_channel.send(embed=embed)
                        else:
                            with open("queue.txt", "a") as f:
                                f.write(f"{mag['data']['magnets'][0]['id']}, {ctx.author.id}\n")
                            not_ready += 1
                    if not_ready == 0:
                        await ctx.reply(
                            f"Sent download to <#{config.DL_CHANNEL}>",
                            mention_author=False,
                        )
                    else:
                        await ctx.reply(
                            f"Not ready. Added to queue.",
                            mention_author=False,
                        )
            except asyncio.TimeoutError:
                # await ctx.send("TOO SLOW", mention_author=False)
                # add reaction to previously sent em_result embed
                await e.add_reaction("❌")
                # await ctx.send("something broke lol")
            except Exception as e:
                self.console.print_exception(show_locals=True)
                await ctx.reply(f"EXCEPTION!\n {type(e).__name__}")

        except Exception as e:
            error_embed = discord.Embed(
                title="An error occurred",
                description=f"TRY AGAIN\n```python\n{str(e)}```",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed) # type: ignore   

async def setup(bot):
    await bot.add_cog(DebridCog(bot))
