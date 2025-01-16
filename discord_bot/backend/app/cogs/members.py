import discord
from discord.ext import commands
import logging
import asyncio
import traceback

from app import models
from app.database import get_db

logger = logging.getLogger(__name__)

class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        print("Members cog initialized")  # Debug print
        
    '''@discord.slash_command(name="member_cog_test", description="Test if the members cog is working")
    async def test_members_cog(self, ctx):
        print("Test command received in Members cog")
        await ctx.respond("Members cog is working!", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        """Test event to verify the cog is loaded"""
        print("Members cog is ready!")
        logger.info("Members cog is ready!")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Test event to verify basic event handling"""
        if message.author == self.bot.user:
            return
        print(f"Message received in Members cog: {message.content[:20]}...")
        logger.info(f"Message received in Members cog from {message.author.name}")'''

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """
        Event handler for when a new member joins the server.
        Checks if they have any of the integration roles and assigns the unverified role if needed.
        """
        print(f"Member joined event triggered for: {member.name} (ID: {member.id})")  # Debug print
        logger.info(f"Member joined: {member.name} (ID: {member.id})")
        
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

def setup(bot):
    print("Setting up Members cog...")  # Debug print
    bot.add_cog(Members(bot))
    print("Members cog setup complete!")  # Debug print
