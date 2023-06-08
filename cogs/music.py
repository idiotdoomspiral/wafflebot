import spotipy
from config import (
    MUSIC_CHANNEL,
    SPOTIPY_CLIENT_ID,
    SPOTIPY_CLIENT_SECRET,
    SPOTIPY_REDIRECT_URI,
    PLAYLIST_URI,
)
import discord
from discord.ext import commands
from discord import app_commands
from loguru import logger


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spotify = spotipy.Spotify(
            auth_manager=spotipy.SpotifyOAuth(
                client_id=SPOTIPY_CLIENT_ID,
                client_secret=SPOTIPY_CLIENT_SECRET,
                redirect_uri=SPOTIPY_REDIRECT_URI,
                scope="playlist-modify-public",
                open_browser=False,
                show_dialog=True,
            )
        )
        self.PLAYLIST_URI = PLAYLIST_URI

    async def check_existing_tracks(self, tracks):
        playlist_tracks = []
        playlist = self.spotify.playlist_tracks(PLAYLIST_URI)["items"]
        for track in playlist:
            playlist_tracks.append(track["track"]["uri"])

        add_tracks = []
        for track in tracks:
            if track not in playlist_tracks:
                add_tracks.append(track)

        return add_tracks

    # @app_commands.command(
    #     name="sync_playlist", description="Syncs the playlist with the channel"
    # )
    # @commands.has_permissions(administrator=True)
    # async def sync_playlist(self, interaction: discord.Interaction):
    #     await interaction.response.defer(thinking=True)
    #     channel = await self.bot.fetch_channel(MUSIC_CHANNEL)
    #     messages = [message async for message in channel.history(limit=None)]
    #     spotify_urls = []
    #     for message in messages:
    #         if "https://open.spotify.com/" in message.content:
    #             if message.content.startswith("https://open.spotify.com/album"):
    #                 album = self.spotify.album(message.content)
    #                 for track in album["tracks"]["items"]:
    #                     spotify_urls.append(track["uri"])
    #             elif message.content.startswith("https://open.spotify.com/track"):
    #                 spotify_urls.append(message.content)

    #     spotify_urls = list(set(spotify_urls))
    #     add_tracks = await self.check_existing_tracks(spotify_urls)
    #     if len(add_tracks) > 0:
    #         logger.info(f"Adding {len(add_tracks)} tracks to playlist.")
    #         await interaction.followup.send(
    #             f"Adding {len(add_tracks)} tracks to playlist."
    #         )
    #         if len(add_tracks) > 100:
    #             logger.info("Too many tracks. Adding 100.")
    #             #    await interaction.followup.send("Too many tracks. Adding 100.")
    #             add_tracks = add_tracks[:100]
    #         await self.spotify.playlist_add_items(PLAYLIST_URI, add_tracks)

    @commands.Cog.listener()
    async def on_message(self, message):
        MUSIC_CHANNEL = await self.bot.fetch_channel(MUSIC_CHANNEL)
        if (
            message.channel.id == MUSIC_CHANNEL.id
            and "https://open.spotify.com/" in message.content
        ):
            try:
                logger.info(f"Got spotify link: {message.content}")
                if message.content.startswith("https://open.spotify.com/album/"):
                    album = self.spotify.album(message.content)
                    track_uris = []

                    for track in album["tracks"]["items"]:
                        track_uris.append(track["uri"])

                    add_tracks = await self.check_existing_tracks(track_uris)

                elif message.content.startswith("https://open.spotify.com/track/"):
                    track = self.spotify.track(message.content)
                    add_tracks = await self.check_existing_tracks([track["uri"]])

                if add_tracks > 0:
                    logger.info(f"Adding {len(add_tracks)} tracks to playlist.")
                    message.add_reaction("🧇")

            except spotipy.exceptions.SpotifyException:
                logger.error("SpotifyException")


async def setup(bot):
    await bot.add_cog(MusicCog(bot))