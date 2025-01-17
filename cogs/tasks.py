from discord.ext import tasks, commands
import httpx
import helpers.embed
import config
import json
from rich.console import Console

class TasksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alldebrid = bot.debrid
        self.debrid_check.start()
        self.console = Console()

    @tasks.loop(seconds=30)
    async def debrid_check(self):
        # await self.twitch_check()

        with open("queue.txt", "r") as f:
            queue = f.readlines()
        queue = [i.strip().split(",") for i in queue]
        print(queue)
        if len(queue) > 0:
           for dl_id, user_id in queue:
                try:
                    async with httpx.AsyncClient() as resp:
                        # Make a request to get the status of the magnet download
                        status = self.alldebrid.get_magnet_status(dl_id)
                except Exception as e:
                    print(f"Error getting status for magnet ID {dl_id}: {e}")
                    self.console.print_exception(show_locals=True)
                    with open("queue.txt", "w") as f:
                            for i in queue:
                                if i[0] != dl_id:  # Write back only the entries that don't match the current dl_id
                                    f.write(f"{i[0]},{i[1]}\n")
                    continue  # Skip to the next item in the queue if there's an error
                
                # Process the status response
                try:
                    # Check if there's an error or if the download status code is greater than 4 (finished or failed)
                    if (
                        status["status"] != "success" 
                        or status["data"]["magnets"]["statusCode"] > 4
                    ):
                        # Rewrite the queue without the completed or errored magnet ID
                        with open("queue.txt", "w") as f:
                            for i in queue:
                                if i[0] != dl_id:  # Write back only the entries that don't match the current dl_id
                                    f.write(f"{i[0]},{i[1]}\n")
                        print(f"Magnet ID {dl_id} removed from the queue.")
                    elif "Ready" in status["data"]["magnets"]["status"]:
                        with open("queue.txt", "w") as f:
                            for i in queue:
                                if i[0] != dl_id:  # Write back only the entries that don't match the current dl_id
                                    f.write(f"{i[0]},{i[1]}\n")
                        print(f"Magnet ID {dl_id} removed from the queue.")
                        filename = status["data"]["magnets"]["filename"]
                        embed = helpers.embed.download_ready(user_id, filename)
                        print(f"Removed: {dl_id}")
                        dl_channel = await self.bot.fetch_channel(config.DL_CHANNEL)
                        await dl_channel.send(embed=embed)
                except KeyError as e:
                    print(f"Missing expected key in response for magnet ID {dl_id}: {e}")
                    self.console.print_exception(show_locals=True)
                    continue  # Skip to the next item if there's an issue with the response
                    
                except Exception as e:
                    self.console.print_exception(show_locals=True)
                    pass

async def setup(bot):
    await bot.add_cog(TasksCog(bot))
