import os
import json
import random
import discord

from datetime import datetime
from discord.ext import commands
from conf import Config
from botUtils import utils, jsonUtils, permChecks
from botUtils.enums import DscState


class miscCommands(commands.Cog, name="Funny/Misc Commands"):
    """Funny and miscellaneous commands without other category"""

    def __init__(self, bot):
        self.bot = bot

######
# Simple games
######

    @commands.command(name="dice", brief="Simulates rolling dice.",
                      usage="[NumberOfSides] [NumberOfDices]")
    async def dice(self, ctx, number_of_sides: int = 6, number_of_dice: int = 1):
        """Rolls number_of_dice dices with number_of_sides sides and returns the result"""
        dice = [
            str(random.choice(range(1, number_of_sides + 1)))
            for _ in range(number_of_dice)
        ]
        await ctx.send(', '.join(dice))

######
# DSC
######

    @commands.group(name="dsc", help="Get and manage informations about current DSC",
                    description="Get the informations about the current dsc or manage it. "
                                "Command only works in music channel. "
                                "Manage DSC informations is only permitted for songmasters.")
    @permChecks.in_channel(Config().server_channels['music'])
    async def dsc(self, ctx):
        """DSC base command, return info command if no subcommand given"""
        if ctx.invoked_subcommand is None:
            await self.dsc_get_info(ctx)

    @dsc.command(name="rules", help="Get the link to the DSC rules")
    async def dsc_get_rules(self, ctx):
        """Returns the DSC rules"""
        await ctx.send(f"<{Config().dsc['rule_link']}>")

    @dsc.command(name="info", help="Get informations about current DSC")
    async def dsc_get_info(self, ctx):
        """Returns basic infos about next/current DSC"""
        hostNick = None
        dateOutStr = ""
        if not Config().dsc['host_id']:
            await ctx.send("You must set DSC host!")
        else:
            hostNick = discord.utils.get(ctx.guild.members, id=Config().dsc['host_id']).name

        if Config().dsc['state'] == DscState.Registration:
            if Config().dsc['state_end'] > datetime.now():
                dateOutStr = f" bis {Config().dsc['state_end'].strftime('%d.%m.%Y')}"

            embed = discord.Embed(title=f":clipboard: Anmeldung offen{dateOutStr}!")
            embed.add_field(name="Aktueller Ausrichter", value=hostNick)
            embed.add_field(name="Anmeldung", value=Config().dsc['contestdoc_link'])
            await ctx.send(embed=embed)

        elif Config().dsc['state'] == DscState.Voting:
            if Config().dsc['state_end'] > datetime.now():
                dateOutStr = f" bis {Config().dsc['state_end'].strftime('%d.%m.%Y, %H:%M')} Uhr"

            embed = discord.Embed(title=f":incoming_envelope: Votingphase läuft{dateOutStr}!")
            embed.add_field(name="Votings an", value=hostNick)
            embed.add_field(name="Alle Songs", value=Config().dsc['contestdoc_link'])
            embed.add_field(name="Youtube-Playlist", value=Config().dsc['yt_link'])
            await ctx.send(embed=embed)

        else:
            await ctx.send("Configuration error. Please reset dsc configuration.")
            embed = discord.Embed(title="DSC configuration error")
            embed.add_field(name="Host ID", value=str(Config().dsc['host_id']))
            embed.add_field(name="Host Name", value=hostNick)
            embed.add_field(name="State", value=str(Config().dsc['state']))
            embed.add_field(name="YT Playlist", value=str(Config().dsc['yt_link']))
            embed.add_field(name="State End", value=str(Config().dsc['state_end']))
            await utils.write_debug_channel_embed(self.bot, embed)

    @dsc.group(name="set", help="Set data about current/next DSC", usage="<host|state|stateend|yt>")
    @commands.has_any_role("mod", "songmaster", "botmaster")
    async def dsc_set(self, ctx):
        """Basic set subcommand, does nothing"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Usage: !dsc set <host|state|yt|stateend>")

    @dsc_set.command(name="host", help="Sets the current/next DSC hoster", usage="<user>")
    @commands.has_any_role("mod", "songmaster", "botmaster")
    async def dsc_set_host(self, ctx, user: discord.Member):
        """Sets the current/next DSC host"""
        Config().dsc['host_id'] = user.id
        Config().write_config_file()
        await ctx.send("New hoster set.")

    @dsc_set.command(name="state", help="Sets the current DSC state (Voting/Registration)",
                     usage="<voting|registration>")
    @commands.has_any_role("mod", "songmaster", "botmaster")
    async def dsc_set_state(self, ctx, state):
        """Sets the current DSC state (registration/voting)"""
        if state.lower() == "voting":
            Config().dsc['state'] = DscState.Voting
            await ctx.send("Voting phase set.")
        elif state.lower() == "registration":
            Config().dsc['state'] = DscState.Registration
            await ctx.send("Registration phase set.")
        else:
            await ctx.send("Invalid DSC phase.")
        Config().write_config_file()

    @dsc_set.command(name="yt", help="Sets the Youtube playlist link", usage="<link>")
    @commands.has_any_role("mod", "songmaster", "botmaster")
    async def dsc_set_yt_link(self, ctx, link):
        """Sets the youtube playlist link"""
        link = utils.clear_link(link)
        Config().dsc['yt_link'] = link
        Config().write_config_file()
        await ctx.send("New Youtube playlist link set.")

    @dsc_set.command(name="stateend", help="Sets the registration/voting end date", usage="DD.MM.JJJJ[ HH:MM]",
                     description="Sets the end date and time for registration and voting phase. "
                                 "If no time is given, 23:59 will be used.")
    @commands.has_any_role("mod", "songmaster", "botmaster")
    async def dsc_set_state_end(self, ctx, dateStr, timeStr=None):
        """Sets the end date (and time) of the current DSC state"""
        if not timeStr:
            dateStr += " 23:59"
        Config().dsc['state_end'] = datetime.strptime(dateStr,"%d.%m.%Y %H:%M")
        Config().write_config_file()
        await ctx.send("New state end date set.")


def register(bot):
    bot.add_cog(miscCommands(bot))