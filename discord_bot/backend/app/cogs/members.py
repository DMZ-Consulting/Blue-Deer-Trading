# type: ignore[type-arg]

import discord
from discord.ext import commands
import logging
import asyncio
import traceback
import os
from app import models
from app.database import get_db
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# TODO: UPDATE THIS

BOT_IDS_TO_SKIP = [
    1284994761211772928, # Blue deer bot
    1079897436631351326, # Diesel test bot
    400416456191377419, # My ID
]

if os.getenv("LOCAL_TEST"):
    TARGET_ROLE_ID = 1329256955092668477
    THREAD_CREATION_CHANNEL_ID = 1372291911171440701 # TODO: UPDATE THIS

    NEEDED_ROLES_TO_ADD_TO_THREAD = ["Full Access", "BD-Verified"]

    USERS_TO_ADD_TO_THREADS = [
        1285713259697012786
    ]

    MESSAGE_INTERVAL = 20
    UPDATE_INTERVAL = 25
else:
    TARGET_ROLE_ID = 1288241189618978917
    THREAD_CREATION_CHANNEL_ID = 1372359899412955156 # TODO: UPDATE THIS

    NEEDED_ROLES_TO_ADD_TO_THREAD = ["Full Access", "BD-Verified"]

    USERS_TO_ADD_TO_THREADS = [
        1044367510671204523,
        300001482194026508
    ]

    MESSAGE_INTERVAL = 3600
    UPDATE_INTERVAL = 3600 * 23

class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.thread_reminder_task = self.bot.loop.create_task(self.thread_reminder_loop())

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """
        Event handler for when a member's roles are updated.
        Checks if they were granted trader roles and adds BD-Unverified if needed.
        Also removes verification roles if all trader roles are removed.
        """

        logging_cog = self.bot.get_cog('LoggingCog')
        #await logging_cog.log_to_channel(after.guild, f"Member {after.name} (ID: {after.id}) roles updated.\n Before: {before.roles}\n After: {after.roles}")
        # Skip if roles didn't change
        if set(before.roles) == set(after.roles):
            return
            
        # Skip if not in Blue Deer server
        #if after.guild.id != 1055255055474905139:  # Blue Deer Server
        #    return
            
        # Define the trader role names
        trader_role_names = ["Full Access", "Day Trader", "Swing Trader", "Long Term Trader"]
        
        # Check if roles were added
        added_roles = set(after.roles) - set(before.roles)
        if added_roles:
            # Check if any trader roles were added
            trader_roles_added = [role for role in added_roles if role.name in trader_role_names]
            
            if trader_roles_added:
                # Check if they have the BD-Verified role
                has_verified = any(role.name == "BD-Verified" for role in after.roles)
                
                # If they don't have the verified role, add the unverified role
                if not has_verified:
                    # Find the BD-Unverified role
                    unverified_role = discord.utils.get(after.guild.roles, name="BD-Unverified")
                    if unverified_role and unverified_role not in after.roles:
                        try:
                            await after.add_roles(unverified_role, reason="Trader role granted without verification")
                            logger.info(f"Added BD-Unverified role to {after.name} (ID: {after.id}) after being granted trader role")
                        except Exception as e:
                            logger.error(f"Error adding BD-Unverified role to {after.name}: {str(e)}")
                            logger.error(traceback.format_exc())
        
        # Check if roles were removed
        removed_roles = set(before.roles) - set(after.roles)
        if removed_roles:
            # Check if any trader roles were removed
            trader_roles_removed = [role for role in removed_roles if role.name in trader_role_names]
            
            if trader_roles_removed:
                # Check if user had trader roles before and now has none
                had_trader_roles = any(role.name in trader_role_names for role in before.roles)
                has_trader_roles_now = any(role.name in trader_role_names for role in after.roles)
                
                if had_trader_roles and not has_trader_roles_now:
                    # User lost all trader roles, remove verification roles
                    roles_to_remove = []
                    
                    # Find BD-Verified and BD-Unverified roles
                    verified_role = discord.utils.get(after.guild.roles, name="BD-Verified")
                    unverified_role = discord.utils.get(after.guild.roles, name="BD-Unverified")
                    
                    if verified_role and verified_role in after.roles:
                        roles_to_remove.append(verified_role)
                    
                    if unverified_role and unverified_role in after.roles:
                        roles_to_remove.append(unverified_role)
                    
                    if roles_to_remove:
                        try:
                            await after.remove_roles(*roles_to_remove, reason="All trader roles removed")
                            logger.info(f"Removed verification roles from {after.name} (ID: {after.id}) after losing all trader roles")
                        except Exception as e:
                            logger.error(f"Error removing verification roles from {after.name}: {str(e)}")
                            logger.error(traceback.format_exc())

        """
        Event listener that triggers when a member's profile is updated (including roles).
        Creates a private thread for the user if they gain a specific role.
        """
        print(f"Member {after.name} (ID: {after.id}) roles updated.\n Before: {before.roles}\n After: {after.roles}")
        # Check if the member gained the target role
        # We check if the target role was NOT in the 'before' roles but IS in the 'after' roles
        target_role = after.guild.get_role(TARGET_ROLE_ID)
        if target_role is None:
            try:
                target_role = after.guild.get_role(TARGET_ROLE_ID_TEST)
            except Exception as e:
                logger.error(f"Error: Target role with ID {TARGET_ROLE_ID} not found in guild {after.guild.name}: {e}")
                return # Exit the function if the role doesn't exist

        # Check if user already has a thread
        existing_thread = None
        for thread in channel.threads:
            if after in thread.members:
                existing_thread = thread
                break

        # Check if the user already had the target role
        had_target_role = False
        for role in before.roles:
            if role.id == TARGET_ROLE_ID or role.id == TARGET_ROLE_ID_TEST:
                had_target_role = True
                break

        if had_target_role:
            logger.info(f"Member {after.name} (ID: {after.id}) already had the target role.")
            return

        # Check if the role change actually includes gaining the target role
        gained_target_role = False
        for role in after.roles:
            if role.id == TARGET_ROLE_ID or role.id == TARGET_ROLE_ID_TEST and role not in before.roles:
                gained_target_role = True
                break

        if not gained_target_role:
            logger.info(f"Member {after.name} (ID: {after.id}) did not gain the target role.")
            return

        if gained_target_role:
            # User gained the target role

            # Find the channel where threads should be created
            channel = self.bot.get_channel(THREAD_CREATION_CHANNEL_ID)
            if not channel:
                logger.error(f"Error: Could not find thread creation channel with ID {THREAD_CREATION_CHANNEL_ID} in guild {after.guild.name}.")
                return # Exit the function if the channel doesn't exist

            # Ensure the channel is a text channel where threads can be created
            if not isinstance(channel, discord.TextChannel):
                logger.error(f"Error: Channel {channel.name} (ID: {THREAD_CREATION_CHANNEL_ID}) is not a text channel.")
                return

            # Define the thread name
            thread_name = f"Welcome {after.display_name}!"

            # Check if the user already has a thread
            existing_thread = None
            for thread in channel.threads:
                if after in thread.members:
                    existing_thread = thread
                    break

            if existing_thread:
                logger.info(f"User {after.name} (ID: {after.id}) already has a thread. Skipping thread creation.")
                return

            try:
                # Create a private thread for the user
                # Bot needs 'Create Private Threads' permission in the channel.
                thread = await channel.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.private_thread,
                    reason="Creating thread upon role assignment"
                )

                # Add the user to the thread
                await thread.add_user(after)
                for user_id in USERS_TO_ADD_TO_THREADS:
                    user = after.guild.get_member(user_id)
                    if user:
                        await thread.add_user(user)

                # Send a welcome message in the thread
                await thread.send(f"""Hello {after.mention}!\n
Use this space to ask questions, share insights, or post daily reflections. Justin will pop in with answers at least once a week, and I (Jake) am here to help with anything in between.\n
We're committed to reshaping the way you approach the markets so you can reach—and exceed—your goals.\n
To kick things off, start reflecting on your trading day as soon as possible ideally right at the close so its fresh in your mind use this as a Journal be CONSISTENT! The most important thing isn't the trading it's how you feel when your trading- reflect on your thinking/feelings throughout the session.\n
We are going to give you our time and effort all we ask if you help us help more people! All we ask if your benefiting here and seeing the value add\n
Post your wins, share your successes in here \n
We are going to help you achieve your goals we are already so grateful you took the leap of faith and joined our service we would be even more grateful you can help us achieve our goals""")

                print(f"Created welcome thread for {after.name} in channel {channel.name}.")

            except discord.Forbidden:
                # If the bot lacks permissions to create the thread
                logger.error(f"Bot lacks permissions to create private threads in channel {channel.name} for user {after.name}.")
            except Exception as e:
                # Catch any other potential errors during thread creation
                print(f"Failed to create thread for {after.name} in channel {channel.name}: {e}")
                print(traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """
        Event handler for when a new member joins the server.
        Checks if they have any of the integration roles and assigns the unverified role if needed.
        """
        print(f"Member joined event triggered for: {member.name} (ID: {member.id})")  # Debug print
        logger.info(f"Member joined: {member.name} (ID: {member.id})")

        #await self.dm_member(member)
        
        if member.guild.id != 1055255055474905139:  # Blue Deer Server
            return

        # Wait for potential role changes with timeout
        max_attempts = 6  # Maximum number of attempts
        attempt_delay = 5  # Seconds between attempts
        
        for attempt in range(max_attempts):
            # Fetch the latest member data to get current roles
            try:
                updated_member = await member.guild.fetch_member(member.id)
                if len(updated_member.roles) > 1:  # More than just @everyone role
                    logger.info(f"Roles detected for {member.name} after {attempt * attempt_delay} seconds")
                    break
                if attempt < max_attempts - 1:  # Don't sleep on the last attempt
                    await asyncio.sleep(attempt_delay)
            except discord.NotFound:
                logger.warning(f"Member {member.name} left before role check could complete")
                return
            except Exception as e:
                logger.error(f"Error fetching member data: {str(e)}")
                break

        '''
        db = next(get_db())
        try:
            # Check conditional role grants for this member
            print(f"Checking conditional role grants for {member.name} (ID: {member.id})")
            conditional_grants = db.query(models.ConditionalRoleGrant).filter_by(guild_id=str(member.guild.id)).all()
            for grant in conditional_grants:
                try:
                    condition_role_ids = [role.role_id for role in grant.condition_roles]
                    grant_role = member.guild.get_role(int(grant.grant_role_id))
                    exclude_role = member.guild.get_role(int(grant.exclude_role_id)) if grant.exclude_role_id else None
                    
                    # Use updated_member to check roles
                    if any(str(role.id) in condition_role_ids for role in updated_member.roles) and (not exclude_role or exclude_role not in updated_member.roles):
                        try:
                            await updated_member.add_roles(grant_role, reason="Meets conditional role grant requirements from integration")
                            #await log_action(member.guild, f"Added role {grant_role.name} to new member {member.name} (ID: {member.id}) due to meeting conditional role grant requirements")
                            logger.info(f"Successfully added role {grant_role.name} to member {member.name}")
                        except discord.HTTPException as e:
                            if e.status == 429:  # Rate limit error
                                retry_after = e.retry_after
                                logger.warning(f"Rate limited while adding role. Waiting {retry_after} seconds.")
                                await asyncio.sleep(retry_after)
                                # Try again after waiting
                                await updated_member.add_roles(grant_role, reason="Meets conditional role grant requirements from integration (retry)")
                            else:
                                raise
                except Exception as e:
                    logger.error(f"Error processing grant {grant.id} for member {member.name}: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error in on_member_join for {member.name}: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            db.close()

        # Send welcome message if system channel exists
        channel = member.guild.system_channel
        if channel is not None:
            await channel.send(f'Welcome {member.mention}.')
        '''

    @commands.slash_command(name="create_staff_threads", description="Creates 1-on-1 threads for each member with specified staff.")
    async def create_staff_threads(
        self,
        ctx: discord.ApplicationContext, # Use ApplicationContext for slash commands
        staff_mentions: discord.Option(str, "Mention staff members to include in each thread (e.g., @Staff1 @Staff2)", required=False)
    ):
        """
        Slash command to create a private thread for every member in the server,
        including the command invoker and any mentioned staff members.
        """
        # Ensure the command is used in a guild text channel
        if not isinstance(ctx.channel, discord.TextChannel):
            return await ctx.respond("This command can only be used in a server text channel.", ephemeral=True) # ephemeral=True makes the response only visible to the user

        await ctx.defer(ephemeral=True) # Acknowledge the command to prevent timeout, response is ephemeral

        # Parse mentioned staff members from the string input
        staff_members_to_add = [ctx.author] # Always include the command invoker (assuming they are staff)
        if staff_mentions:
            # Split the string by spaces and process each potential mention
            for mention_str in staff_mentions.split():
                try:
                    # Extract user ID from mention string (handles different mention formats)
                    user_id = int(mention_str.strip('<>@!'))
                    member = ctx.guild.get_member(user_id)
                    if member and member not in staff_members_to_add:
                        staff_members_to_add.append(member)
                    elif not member:
                        await ctx.followup.send(f"Warning: Could not find member for mention: {mention_str}", ephemeral=True)
                except ValueError:
                    await ctx.followup.send(f"Warning: Invalid member mention format: {mention_str}", ephemeral=True)

        print(f"Staff members to add: {staff_members_to_add}")

        successful_threads = 0
        failed_members = []

        # Iterate through all members in the guild
        # Note: This might be a long operation for very large servers.
        for member in ctx.guild.members:
            if member.bot or member == ctx.author: # Skip bots and the command invoker (they are added as staff)
                continue

            # Member must have the "Full Access" role to be added to the thread and the "BD-Verified" role to be added to the thread
            add_member_to_thread = True
            role_names = [role.name for role in member.roles]
            for role in NEEDED_ROLES_TO_ADD_TO_THREAD:
                if role not in role_names:
                    print(f"Member {member.name} does not have the required role {role} to be added to the thread.")
                    add_member_to_thread = False
                    break

            if not add_member_to_thread:
                print(f"Member {member.name} does not have the required roles to be added to the thread.")
                continue

            # Define the thread name
            thread_name = f"Chat with {member.display_name}" # Use display_name for clarity

            # List of members to add to this specific thread (the member + all specified staff)
            members_for_this_thread = [member] + staff_members_to_add
            print(f"Members for this thread: {members_for_this_thread}")

            try:
                # Create a private thread
                # Private threads require the server to be boosted to Level 2 or higher
                # and the bot needs 'Create Private Threads' permission in the channel.
                thread = await ctx.channel.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.private_thread,
                    reason=f"1-on-1 staff chat initiated by {ctx.author.name}",
                )

                # Add all required members to the thread
                for user_to_add in members_for_this_thread:
                    try:
                        await thread.add_user(user_to_add)
                        await asyncio.sleep(1)
                    except Exception as add_user_error:
                        print(f"Could not add user {user_to_add.name} to thread {thread.name}: {add_user_error}")
                        # Continue trying to add other users, but log the error

                # Send a welcome message in the thread
                mentions = " ".join([user.mention for user in members_for_this_thread])
                await thread.send(f"""Hello {member.mention}!\n
Use this space to ask questions, share insights, or post daily reflections. Justin will pop in with answers at least once a week, and I (Jake) am here to help with anything in between.\n
We're committed to reshaping the way you approach the markets so you can reach—and exceed—your goals.\n
To kick things off, start reflecting on your trading day as soon as possible ideally right at the close so its fresh in your mind use this as a Journal be CONSISTENT! The most important thing isn't the trading it's how you feel when your trading- reflect on your thinking/feelings throughout the session.\n
We are going to give you our time and effort all we ask if you help us help more people! All we ask if your benefiting here and seeing the value add\n
Post your wins, share your successes in here \n
We are going to help you achieve your goals we are already so grateful you took the leap of faith and joined our service we would be even more grateful you can help us achieve our goals""")

                successful_threads += 1

            except discord.Forbidden:
                # If the bot lacks permissions for a specific member or the channel
                failed_members.append(f"{member.name} (Forbidden)")
                print(f"Failed to create thread for {member.name}: Bot lacks permissions.")
                # Consider breaking here if it's a channel permission issue to avoid repeated failures
                break # Exit the loop if permissions are the issue for the channel
            except Exception as e:
                # Catch any other potential errors during thread creation
                failed_members.append(f"{member.name} ({type(e).__name__})")
                print(f"Failed to create thread for {member.name}: {e}")
                # Consider breaking here if errors are frequent to avoid rate limits
                # break # Uncomment this line if you want to stop after the first failure
            await asyncio.sleep(5)
        
        print(f"Successfully created {successful_threads} threads.")
        # Send a final summary response
        summary_message = f"Attempted to create threads for {len(ctx.guild.members) - ctx.guild.member_count + successful_threads} members.\n" # Basic member count minus bots plus successful threads
        if successful_threads > 0:
            summary_message += f"Successfully created {successful_threads} threads.\n"
        if failed_members:
            summary_message += f"Failed to create threads for the following members: {', '.join(failed_members)}\n"
            summary_message += "Please check bot permissions and server boosting level for private threads."

        await ctx.followup.send(summary_message, ephemeral=True)

    @commands.slash_command(name="create_thread_for_member", description="Creates a private thread for a specific member.")
    async def create_thread_for_member(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Option(discord.Member, "The member to create a thread for.")
    ):
        """
        Slash command to create a private thread for a specific member.
        """
        # Ensure the command is used in a guild
        if not ctx.guild:
            return await ctx.respond("This command can only be used in a server.", ephemeral=True)
        
        # Ensure the bot has the necessary permissions in the target channel
        bot_member = ctx.guild.get_member(self.bot.user.id)
        if not bot_member or not ctx.channel.permissions_for(bot_member).manage_threads:
            return await ctx.respond(f"I need the 'Manage Threads' permission in the channel '{ctx.channel.name}' to delete threads.", ephemeral=True)
        
        await ctx.defer(ephemeral=True) # Acknowledge the command

        # Define the thread name
        thread_name = f"Chat with {member.display_name}" # Use display_name for clarity
        successful_threads = 0

        try:
            # Create a private thread
            thread = await ctx.channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                reason=f"1-on-1 staff chat initiated by {ctx.author.name}",
            )

            # Add the member to the thread
            await thread.add_user(member)

            # Send a welcome message in the thread
            await thread.send(f"""Hello {member.mention}!\n
Use this space to ask questions, share insights, or post daily reflections. Justin will pop in with answers at least once a week, and I (Jake) am here to help with anything in between.\n
We're committed to reshaping the way you approach the markets so you can reach—and exceed—your goals.\n
To kick things off, start reflecting on your trading day as soon as possible ideally right at the close so its fresh in your mind use this as a Journal be CONSISTENT! The most important thing isn't the trading it's how you feel when your trading- reflect on your thinking/feelings throughout the session.\n
We are going to give you our time and effort all we ask if you help us help more people! All we ask if your benefiting here and seeing the value add\n
Post your wins, share your successes in here \n
We are going to help you achieve your goals we are already so grateful you took the leap of faith and joined our service we would be even more grateful you can help us achieve our goals""")

            successful_threads += 1

            await ctx.followup.send(f"Successfully created thread for {member.name}. {thread.mention}", ephemeral=True)

        except discord.Forbidden:
            await ctx.followup.send(f"I lack the permissions to create threads in channel '{ctx.channel.name}'.", ephemeral=True)
        except Exception as e:
            await ctx.followup.send(f"An unexpected error occurred while trying to create a thread: {e}", ephemeral=True)
            print(traceback.format_exc())

    @commands.slash_command(name="delete_all_threads", description="Deletes all active and archived threads in a channel.")
    async def delete_all_threads(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "The channel to delete threads from.")
    ):
        """
        Slash command to delete all active and archived threads within a specified channel.
        Requires 'Manage Threads' permission for the bot.
        """
        # Ensure the command is used in a guild
        if not ctx.guild:
            return await ctx.respond("This command can only be used in a server.", ephemeral=True)

        # Ensure the bot has the necessary permissions in the target channel
        bot_member = ctx.guild.get_member(self.bot.user.id)
        if not bot_member or not channel.permissions_for(bot_member).manage_threads:
            return await ctx.respond(f"I need the 'Manage Threads' permission in the channel '{channel.name}' to delete threads.", ephemeral=True)

        await ctx.defer(ephemeral=True) # Acknowledge the command

        deleted_count = 0
        failed_to_delete = []

        try:
            # Fetch active threads
            active_threads = channel.threads
            for thread in active_threads:
                try:
                    await thread.delete()
                    deleted_count += 1
                except Exception as e:
                    failed_to_delete.append(f"{thread.name} (Active): {e}")
                    print(f"Failed to delete active thread {thread.name}: {e}")

            # Fetch archived threads (public and private)
            # Note: Fetching archived threads might require iterating through pages for many threads
            async for thread in channel.archived_threads():
                try:
                    await thread.delete()
                    deleted_count += 1
                except Exception as e:
                    failed_to_delete.append(f"{thread.name} (Archived): {e}")
                    print(f"Failed to delete archived thread {thread.name}: {e}")

            async for thread in channel.archived_threads(private=True):
                try:
                    await thread.delete()
                    deleted_count += 1
                except Exception as e:
                    failed_to_delete.append(f"{thread.name} (Archived Private): {e}")
                    print(f"Failed to delete archived private thread {thread.name}: {e}")


        except discord.Forbidden:
            await ctx.followup.send(f"I lack the permissions to fetch or delete threads in channel '{channel.name}'. Make sure I have 'Manage Threads'.", ephemeral=True)
            return
        except Exception as e:
            await ctx.followup.send(f"An unexpected error occurred while trying to delete threads: {e}", ephemeral=True)
            print(f"Unexpected error during thread deletion: {e}")
            print(traceback.format_exc())
            return


        # Send a summary of the deletion process
        summary_message = f"Attempted to delete threads in channel '{channel.name}'.\n"
        summary_message += f"Successfully deleted {deleted_count} threads.\n"
        if failed_to_delete:
            summary_message += f"Failed to delete the following threads:\n" + "\n".join(failed_to_delete)
            summary_message += "\nPlease check bot permissions and Discord's rate limits if many failed."

        await ctx.followup.send(summary_message, ephemeral=True)

    async def dm_member(self, member):
        await member.send("""## Welcome to the Blue Deer Trading Discord server! \n
        ## Please watch the [Discord Instruction Video](https://drive.google.com/file/d/1fmbMA2F6gFMWPZk1VfwQQl_VNaQGqsuj/view?usp=sharing) to get started. \n
        ### To get started, please verify your account by accepting the Terms & Conditions :arrow_right: https://discord.com/channels/1055255055474905139/1156641139143749632. \n
        ### After you have accepted the Terms & Conditions, You will gain access to the rest of the server. Please read the entirety of the Service Introduction :arrow_right: https://discord.com/channels/1055255055474905139/1146740935821111356. \n
        ### Please make sure to watch both instructional videos to acclimate yourself to the server. \n
        ### \- BlueDeer""")

    async def thread_reminder_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                channel = self.bot.get_channel(THREAD_CREATION_CHANNEL_ID)
                if not channel or not isinstance(channel, discord.TextChannel):
                    logger.error(f"Could not find thread creation channel with ID {THREAD_CREATION_CHANNEL_ID} or it is not a text channel.")
                else:
                    now = discord.utils.utcnow()
                    for thread in channel.threads:
                        # Skip archived threads
                        if thread.archived:
                            continue
                        # Fetch the last message in the thread
                        last_message = None
                        try:
                            async for msg in thread.history(limit=1, oldest_first=False):
                                last_message = msg
                                break
                        except Exception as e:
                            logger.error(f"Error fetching last message for thread {thread.name}: {e}")
                            continue
                        if last_message:
                            delta = now - last_message.created_at
                            if delta.total_seconds() < UPDATE_INTERVAL:
                                continue  # Less than 23 hours since last message
                        # Find the user to tag (the thread owner)
                        thread_owner = None
                        try:
                            await thread.fetch_members()
                            for member in thread.members:
                                if member.id not in USERS_TO_ADD_TO_THREADS and member.id not in BOT_IDS_TO_SKIP:
                                    thread_owner = member
                                    break
                        except Exception as e:
                            logger.error(f"Error fetching members for thread {thread.name}: {e}")
                        if thread_owner:
                            try:
                                thread_owner_obj = self.bot.get_user(thread_owner.id)
                                await thread.send(f"""Hey {thread_owner_obj.mention}, how was your trading today? Take this time to reflect on today's session.\n
Explain how you felt in certain trades and risk (even if it seems unrelated to trading it's important to be aware)\n
You can do this on your own but if you want feedback please reply here in as much or as little detail as you would like.""")
                                logger.info(f"Sent reminder in thread {thread.name} for user {thread_owner_obj.name}.")
                            except Exception as e:
                                logger.error(f"Error sending reminder in thread {thread.name}: {e}")
                        else:
                            logger.warning(f"Could not determine thread owner for thread {thread.name}.")
            except Exception as e:
                logger.error(f"Error in thread_reminder_loop: {e}")
            await asyncio.sleep(MESSAGE_INTERVAL)  # Wait 1 hour before next check

def setup(bot):
    print("Setting up Members cog...")  # Debug print
    bot.add_cog(Members(bot))
    print("Members cog setup complete!")  # Debug print
