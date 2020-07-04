import platform
import discord
from discord.ext import commands
from datetime import datetime, timedelta

from conf import Config
from botutils import utils, permChecks, enums
from Geckarbot import BasePlugin
from subsystems.ignoring import IgnoreEditResult
from subsystems.blacklist import Blacklist
from subsystems.greylist import Greylist
from subsystems.cmddisable import CommandDisable


class Plugin(BasePlugin, name="Bot Management Commands"):
    """Commands for moderation"""

    def __init__(self, bot):
        super().__init__(bot)
        self.can_reload = True
        bot.register(self)

        # self.bl = Blacklist(self)
        # self.gl = Greylist(self)
        # self.cd = CommandDisable(self)
        # bot.coredata['blacklist'] = self.bl
        # bot.coredata['greylist'] = self.gl
        # bot.coredata['disabled_cmds'] = self.cd

    def default_config(self):
        return {
            'blacklist': [],
            'greylist': {},
            'disabled_cmds': [],
            'about_data': {
                'repo_link': "https://github.com/gobo7793/Geckarbot/",
                'bot_info_link': "",
                'privacy_notes_link': "",
                'privacy_notes_lang': "",
                'profile_pic_creator': ""}
        }

    ######
    # Misc commands
    ######

    @commands.command(name="reload", help="Reloads the configuration.", usage="[plugin_name]",
                      description="Reloads the configuration from the given plugin."
                                  "If no plugin given, all plugin configs will be reloaded.")
    @commands.has_any_role(Config().ADMIN_ROLE_ID, Config().BOTMASTER_ROLE_ID)
    async def reload(self, ctx, plugin_name=None):
        """Reloads the config of the given plugin or all if none is given"""
        await utils.log_to_admin_channel(ctx)
        if plugin_name is None:
            Config().load_all()
            send_msg = "Configuration of all plugins reloaded."
        else:
            send_msg = f"No plugin {plugin_name} found."
            for plugin in Config().plugins:
                if plugin.name == plugin_name and plugin.instance.can_reload:
                    Config().load(plugin.instance)
                    send_msg = f"Configuration of plugin {plugin_name} reloaded."

        if ctx.channel.id != Config().DEBUG_CHAN_ID:
            await ctx.send(send_msg)
        await utils.write_debug_channel(self.bot, send_msg)

    @commands.command(name="plugins", help="List all plugins.")
    async def plugins(self, ctx):
        """Returns registered plugins"""
        plugin_list = "\n - ".join([plugin.module_name for plugin in Config().plugins])
        plugin_count = len(Config().plugins)
        await ctx.send(f"Loaded {plugin_count} plugins:\n - {plugin_list}")

    @commands.command(name="about", help="Prints the credits")
    async def about(self, ctx):

        about_msg = "Geckarbot {} on {}, licensed under GNU GPL v3.0. Hosted with ❤ on {} {} {}.\n".format(
            Config().VERSION, self.bot.guild.name, platform.system(), platform.release(), platform.version())

        if Config().get(self)['about_data']['bot_info_link']:
            about_msg += "For general bot information on this server see <{}>.\n".format(
                Config().get(self)['about_data']['bot_info_link'])
        about_msg += "Github Repository for additional information and participation: <{}>.\n".format(
            Config().get(self)['about_data']['repo_link'])
        if Config().get(self)['about_data']['privacy_notes_link']:
            lang = ""
            if Config().get(self)['about_data']['privacy_notes_lang']:
                lang = " ({})".format(Config().get(self)['about_data']['privacy_notes_lang'])
            about_msg += "Privacy notes: <{}>{}.\n".format(Config().get(self)['about_data']['privacy_notes_link'], lang)

        about_msg += "Main developers: Fluggs, Gobo77, Lubadubs."
        if Config().get(self)['about_data']['profile_pic_creator']:
            about_msg += " Profile picture by {}.".format(Config().get(self)['about_data']['profile_pic_creator'])

        about_msg += "\nSpecial thanks to all contributors!"

        await ctx.send(about_msg)

    ######
    # Ignoring subsystem
    ######

    @commands.group(name="disable", invoke_without_command=True, help="Blocks user or command usage.",
                    usage="<command> [user] [#m|#h|#d|DD.MM.YYYY|HH:MM|DD.MM.YYYY HH:MM|DD.MM. HH:MM]",
                    description="Adds a command to users ignore list to disable any interactions between the user and "
                                "the command.\n"
                                "The time can be a fixed date and/or time or a duration after that the "
                                "command will be auto-removed from the ignore list. The duration unit must be set "
                                "with trailing m for minutes, h for hours or d for days. If no date/duration is "
                                "given, the user can't interact with that command forever.\n"
                                "Users can disable command interactions for themselves only, but Admins also for "
                                "other users.")
    async def disable(self, ctx, command, *args):
        user = ctx.author
        date_args = args
        if len(args) > 0:
            try:
                user = commands.UserConverter().convert(ctx, args[0])
                date_args = args[1:]
            except (commands.CommandError, IndexError):
                date_args = args

        if user != ctx.author and not permChecks.check_full_access(ctx.author):
            raise commands.MissingAnyRole(*Config().FULL_ACCESS_ROLES)

        until = utils.analyze_time_input(date_args)

        result = self.bot.ignoring.add_user_command(user, command, until)
        if result == IgnoreEditResult.Success:
            await ctx.message.add_reaction(Config().CMDSUCCESS)
        elif result == IgnoreEditResult.Already_in_list:
            await ctx.message.add_reaction(Config().CMDERROR)
            await ctx.send("Interactions with command {} are already blocked for {}."
                           .format(command, utils.get_best_username(user)))
        elif result == IgnoreEditResult.Until_in_past:
            await ctx.message.add_reaction(Config().CMDERROR)
            await ctx.send("Sorry, I don't have a time machine.")
        await utils.log_to_admin_channel(ctx)

    @disable.command(name="user", help="Block any interaction between user and bot.",
                     usage="<user> [#m|#h|#d|DD.MM.YYYY|HH:MM|DD.MM.YYYY HH:MM|DD.MM. HH:MM]",
                     description="Adds a user to bot's ignore list to block any interaction between the user and the "
                                 "bot.\n "
                                 "The time can be a fixed date and/or time or a duration after that the user will be "
                                 "auto-removed from the ignore list. The duration unit must be set with trailing m "
                                 "for minutes, h for hours or d for days. If no date/duration is given, the user will "
                                 "be blocked forever.")
    @commands.has_any_role(*Config().FULL_ACCESS_ROLES)
    async def disable_user(self, ctx, user: discord.User, *args):
        until = utils.analyze_time_input(*args)

        result = self.bot.ignoring.add_user(user, until)
        if result == IgnoreEditResult.Success:
            await ctx.message.add_reaction(Config().CMDSUCCESS)
        elif result == IgnoreEditResult.Already_in_list:
            await ctx.message.add_reaction(Config().CMDERROR)
            await ctx.send("{} already blocked.".format(utils.get_best_username(user)))
        elif result == IgnoreEditResult.Until_in_past:
            await ctx.message.add_reaction(Config().CMDERROR)
            await ctx.send("Sorry, I don't have a time machine.")
        await utils.log_to_admin_channel(ctx)

    @disable.command(name="cmd", help="Disables a command in current channel.",
                     usage="<command> [#m|#h|#d|DD.MM.YYYY|HH:MM|DD.MM.YYYY HH:MM|DD.MM. HH:MM]",
                     description="Adds a command to bot's ignore list to disable it in current channel. The command "
                                 "name must be the full qualified name of the command without command prefix. If a "
                                 "subcommand should be disabled, the command name must be inside quotation marks like "
                                 "\"disable cmd\".\n"
                                 "The time can be a fixed date and/or time or a duration after that the command will "
                                 "be auto-removed from the ignore list. The duration unit must be set with trailing m "
                                 "for minutes, h for hours or d for days. If no date/duration is given, the command "
                                 "will be disabled forever.")
    @commands.has_any_role(*Config().FULL_ACCESS_ROLES)
    async def disable_cmd(self, ctx, command, *args):
        until = utils.analyze_time_input(*args)

        result = self.bot.ignoring.add_command(command, ctx.channel, until)
        if result == IgnoreEditResult.Success:
            await ctx.message.add_reaction(Config().CMDSUCCESS)
        elif result == IgnoreEditResult.Already_in_list:
            await ctx.message.add_reaction(Config().CMDERROR)
            await ctx.send("Command {} already blocked in this channel".format(command))
        elif result == IgnoreEditResult.Until_in_past:
            await ctx.message.add_reaction(Config().CMDERROR)
            await ctx.send("Sorry, I don't have a time machine.")
        await utils.log_to_admin_channel(ctx)

    @commands.group(name="enable", invoke_without_command=True, help="Unblocks user or command usage.",
                    description="Removes a command from users ignore list to enable any interactions between the user "
                                "and the command.\n"
                                "Users can enable command interactions for themselves only, but Admins also for "
                                "other users.")
    async def enable(self, ctx, command, user: discord.User = None):
        if user is None:
            user = ctx.author

        if user != ctx.author and not permChecks.check_full_access(ctx.author):
            raise commands.MissingAnyRole(*Config().FULL_ACCESS_ROLES)

        result = self.bot.ignoring.remove_user_command(user, command)
        if result == IgnoreEditResult.Success:
            await ctx.message.add_reaction(Config().CMDSUCCESS)
        elif result == IgnoreEditResult.Not_in_list:
            await ctx.send("Interactions with command {} are not blocked for {}."
                           .format(command, utils.get_best_username(user)))
        await utils.log_to_admin_channel(ctx)

    @enable.command(name="user", help="Unblock user to enable interactions between user and bot.",
                    description="Removes a user from bot's ignore list to enable any interaction between the user and "
                                "the bot.")
    @commands.has_any_role(*Config().FULL_ACCESS_ROLES)
    async def enable_user(self, ctx, user: discord.User):
        result = self.bot.ignoring.remove_user(user)
        if result == IgnoreEditResult.Success:
            await ctx.message.add_reaction(Config().CMDSUCCESS)
        elif result == IgnoreEditResult.Not_in_list:
            await ctx.send("{} is not blocked.".format(utils.get_best_username(user)))
        await utils.log_to_admin_channel(ctx)

    @enable.command(name="cmd", help="Enables a command in current channel.",
                    description="Removes a command from bot's ignore list to enable it in current channel. The command "
                                "name must be the full qualified name of the command without command prefix. If a "
                                "subcommand should be enabled, the command name must be inside quotation marks like "
                                "\"enable cmd\".")
    @commands.has_any_role(*Config().FULL_ACCESS_ROLES)
    async def enable_cmd(self, ctx, command):
        result = self.bot.ignoring.remove_command(command, ctx.channel)
        if result == IgnoreEditResult.Success:
            await ctx.message.add_reaction(Config().CMDSUCCESS)
        elif result == IgnoreEditResult.Not_in_list:
            await ctx.send("Command {} is not blocked in this channel".format(command))
        await utils.log_to_admin_channel(ctx)

    ######
    # Blacklist
    ######

    # @commands.group(name="blacklist", help="Manage the blacklist",
    #                 usage="<list|add|del>",
    #                 description="Add, removes or list users on the bot blacklist. "
    #                             "Users on the blacklist can't use any features of the bot. "
    #                             "Adding and removing users only permitted for mods.")
    # async def blacklist(self, ctx):
    #     if ctx.invoked_subcommand is None:
    #         await ctx.send_help(self.blacklist)
    #
    # @blacklist.command(name="list", help="Lists all users on the blacklist")
    # async def blacklist_list(self, ctx):
    #     """Returns the current blacklist user list"""
    #     res = self.bl.get_blacklist_names()
    #     if not res:
    #         await ctx.send("Blacklist is empty.")
    #     else:
    #         await ctx.send(f"Users on Blacklist: {res}")
    #
    # @blacklist.command(name="add", help="Add an user to the blacklist", usage="<user>")
    # @commands.has_any_role(Config().ADMIN_ROLE_ID, Config().BOTMASTER_ROLE_ID)
    # async def blacklist_add(self, ctx, user: discord.Member):
    #     """Adds the given user to the blacklist"""
    #     await utils.log_to_admin_channel(ctx)
    #     res = self.bl.add_user(user)
    #     if res:
    #         await ctx.send(f"User {user.name} added to blacklist.")
    #     else:
    #         await ctx.send(f"User {user.name} already on blacklist.")
    #
    # @blacklist.command(name="del", help="Remove an user from the blacklist", usage="<user>")
    # @commands.has_any_role(Config().ADMIN_ROLE_ID, Config().BOTMASTER_ROLE_ID)
    # async def blacklist_del(self, ctx, user: discord.Member):
    #     """Removes the given user from blacklist"""
    #     await utils.log_to_admin_channel(ctx)
    #     res = self.bl.del_user(user)
    #     if res:
    #         await ctx.send(f"User {user.name} removed from blacklist.")
    #     else:
    #         await ctx.send(f"User {user.name} not on blacklist.")

    ######
    # Greylist
    ######

    # @commands.group(name="greylist", help="Manage the greylist",
    #                 usage="<list|add|del>",
    #                 description="Add, removes or list users and their games on the greylist. "
    #                             "Users on the greylist can't play the listed bot games. "
    #                             "Users can add and remove games for theirselfes, "
    #                             "but for other users only by mods.")
    # async def greylist(self, ctx):
    #     if ctx.invoked_subcommand is None:
    #         await ctx.send_help(self.greylist)
    #
    # @greylist.command(name="list", help="Lists all users on the greylist")
    # async def greylist_list(self, ctx):
    #     """Returns the current blacklist user list"""
    #     userlist = ""
    #     for userid in Config().get(self).get('greylist', {}):
    #         username = self.bot.get_user(userid).name
    #         games = str(enums.GreylistGames(Config().get(self)['greylist'].get(userid, 0)))
    #
    #         # convert game names here
    #         list_begin = games.find(".")
    #         game_list = games[list_begin + 1:].replace("|", ", ").replace("_", " ")
    #         userlist += f"- {username}: {game_list}\n"
    #
    #     if not userlist:
    #         await ctx.send("Greylist is empty.")
    #     else:
    #         userlist = userlist[:-1]
    #         await ctx.send(f"**Users on Greylist:**\n{userlist}")
    #
    # @greylist.command(name="add", help="Add a bot game to greylist.", usage="[user] [game]",
    #                   description="Adds a bot game to the greylist. "
    #                               "Users can only add a game to their own greylist, "
    #                               "but mods also for other users. "
    #                               "If no game is given, all games will be added.")
    # async def greylist_add(self, ctx, user_game=None, game=None):
    #     """Adds a bot game to the greylist.
    #     Users can only add a game to their own greylist,
    #     but mods also for other users.
    #     If no game is given, all games will be added."""
    #     await utils.log_to_admin_channel(ctx)
    #
    #     user = ctx.author
    #     converter = commands.UserConverter()
    #     member = None
    #     try:
    #         # Note: If member is bot itself, ClientUser type will returned
    #         member = await converter.convert(ctx, user_game)
    #     except commands.CommandError:
    #         pass
    #     if isinstance(member, discord.User):
    #         user = member
    #         if member is ctx.author:
    #             member = None
    #     else:
    #         game = user_game
    #
    #     is_mod = permChecks.check_full_access(ctx.author)
    #     if isinstance(member, discord.User) and not is_mod:
    #         raise commands.MissingAnyRole([Config().ADMIN_ROLE_ID, Config().BOTMASTER_ROLE_ID])
    #
    #     game_enum = getattr(enums.GreylistGames, str(game), enums.GreylistGames.ALL)
    #     res = self.gl.add(user, game_enum)
    #     if res is True:
    #         await ctx.send("User added on greylist.")
    #     else:
    #         await ctx.send("User's greylist updated.")
    #
    # @greylist.command(name="del", help="Remove a bot game from greylist.", usage="[user] [game]",
    #                   description="Removes a bot game to the greylist. "
    #                               "Users can only removes a game to their own greylist, "
    #                               "but mods also for other users. "
    #                               "If no game is given, all games will be removed.")
    # async def greylist_del(self, ctx, user_game=None, game=None):
    #     """"Removes a bot game to the greylist.
    #     Users can only removes a game to their own greylist,
    #     but mods also for other users.
    #     If no game is given, all games will be removed."""
    #     await utils.log_to_admin_channel(ctx)
    #
    #     user = ctx.author
    #     converter = commands.UserConverter()
    #     member = None
    #     try:
    #         # Note: If member is bot itself, ClientUser type will returned
    #         member = await converter.convert(ctx, user_game)
    #     except commands.CommandError:
    #         pass
    #     if isinstance(member, discord.User):
    #         user = member
    #         if member is ctx.author:
    #             member = None
    #     else:
    #         game = user_game
    #
    #     is_mod = permChecks.check_full_access(ctx.author)
    #     if isinstance(member, discord.User) and not is_mod:
    #         raise commands.MissingAnyRole([Config().ADMIN_ROLE_ID, Config().BOTMASTER_ROLE_ID])
    #
    #     game_enum = getattr(enums.GreylistGames, str(game), enums.GreylistGames.ALL)
    #     res = self.gl.remove(user, game_enum)
    #     if res is None:
    #         await ctx.send("User not on greylist.")
    #     elif res is True:
    #         await ctx.send("User removed from greylist.")
    #     else:
    #         await ctx.send("User's greylist updated.")

    ######
    # Commands Disable/Enable
    ######

    # @commands.command(name="dislist", help="List disabled commands")
    # async def list_disabled_cmd(self, ctx):
    #     self.cd.check_expired()
    #
    #     if not Config().get(self)['disabled_cmds']:
    #         await ctx.send("No commands disabled.")
    #     else:
    #         msg_full = "Disabled commands:"
    #         for t in Config().get(self)['disabled_cmds']:
    #             channel = self.bot.get_channel(t[1]).mention
    #             if t[2] < datetime.datetime.max:
    #                 until_msg = f"until {t[2].strftime('%d.%m.%Y, %H:%M')}"
    #             else:
    #                 until_msg = "permanently"
    #             cmd_line = f"\n - `!{t[0]}` in {channel}, {until_msg}."
    #             msg_full += cmd_line
    #
    #         await ctx.send(msg_full)
    #
    # @commands.command(name="disable", help="Disables a command", usage="<command> <hours>",
    #                   description="Disables the given command in the channel in which the disable cmd was used. If a "
    #                               "positive amount of hours is given, the command will be automated reenabled after "
    #                               "that time.")
    # @commands.has_any_role(Config().ADMIN_ROLE_ID, Config().BOTMASTER_ROLE_ID)
    # async def disable_cmd(self, ctx, cmd, hours: int = 0):
    #     await utils.log_to_admin_channel(ctx)
    #     result = self.cd.disable(cmd, ctx.channel, hours)
    #
    #     until_msg = ""
    #     if hours > 0:
    #         exp_time = datetime.datetime.now() + datetime.timedelta(hours=hours)
    #         until_msg = f" until {exp_time.strftime('%d.%m.%Y, %H:%M')}"
    #
    #     if result:
    #         await ctx.send(f"Command '{cmd}' disabled in this channel{until_msg}.")
    #     else:
    #         await ctx.send(f"Command '{cmd}' is already disabled in this channel.")
    #
    # @commands.command(name="enable", help="Enables a command", usage="<command>",
    #                   description="Enables the given command in the channel in which the enable cmd was used.")
    # @commands.has_any_role(Config().ADMIN_ROLE_ID, Config().BOTMASTER_ROLE_ID)
    # async def enable_cmd(self, ctx, cmd):
    #     await utils.log_to_admin_channel(ctx)
    #     result = self.cd.enable(cmd, ctx.channel)
    #
    #     if result is True:
    #         await ctx.send(f"Command '{cmd}' is now enabled in this channel.")
    #     else:
    #         await ctx.send("Command '{cmd}' was not disabled in this channel.")
