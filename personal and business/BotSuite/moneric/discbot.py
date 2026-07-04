import sys
import os
import signal  # Add signal import

# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import discord
from datetime import datetime
from discord.ext import commands
from discord import ui  # Add UI import for modals and views
from moneric.moneroqr import generate_payment_uri  # Import the QR code generator function
import io
import qrcode  # Add this import to generate QR codes
from PIL import Image, ImageDraw, ImageFont  # Add Image import

# Create log.txt file
with open('c:\\Users\\jacob\\Desktop\\murp\\log.txt', 'w') as log_file:
    log_file.write('Log file created.\n')

# Use only Bot, not Client
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Add members intent to access guild members

# Bot definition with command prefix "/"
bot = commands.Bot(command_prefix='/', intents=intents)

# Command to respond with a greeting
@bot.command(name='commands', description='Display list of bot commands.')
async def commands(ctx):
    help_message = (
        "```\n"
        "+-----------------------------+\n"
        "|       Bot Commands          |\n"
        "+-----------------------------+\n"
        "| /commands | Display this menu|\n"
        "| /hello    | Greet the bot    |\n"
        "| /transact | Generate QR code |\n"
        "+-----------------------------+\n"
        "```"
    )
    await ctx.send(help_message)

# Transaction Modal for GUI input (without recipient field)
class TransactionModal(ui.Modal, title='Monero Transaction Details'):
    def __init__(self, recipient_user):
        super().__init__()
        self.recipient_user = recipient_user

    amount_xmr = ui.TextInput(
        label='Amount (XMR)',
        placeholder='Enter amount in XMR (e.g., 1.23) - Leave blank if using USD',
        required=False,
        max_length=20
    )

    amount_usd = ui.TextInput(
        label='Amount (USD)',
        placeholder='Enter amount in USD (e.g., 150.00) - Leave blank if using XMR',
        required=False,
        max_length=20
    )

    address = ui.TextInput(
        label='Monero Address',
        placeholder='Enter the Monero wallet address',
        required=True,
        max_length=200,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate that either XMR or USD amount is provided
            xmr_amount = self.amount_xmr.value.strip()
            usd_amount = self.amount_usd.value.strip()
            
            if not xmr_amount and not usd_amount:
                await interaction.response.send_message("❌ Please enter either an XMR amount or USD amount.", ephemeral=True)
                return
            
            if xmr_amount and usd_amount:
                await interaction.response.send_message("❌ Please enter only one amount type (XMR or USD), not both.", ephemeral=True)
                return

            # Calculate final XMR amount
            if xmr_amount:
                final_xmr_amount = float(xmr_amount)
                amount_display = f"{final_xmr_amount} XMR"
            else:
                # Convert USD to XMR (using approximate rate - in production, fetch from API)
                usd_to_xmr_rate = 0.0065  # Example rate: 1 USD ≈ 0.0065 XMR
                final_xmr_amount = float(usd_amount) * usd_to_xmr_rate
                amount_display = f"{usd_amount} USD (≈{final_xmr_amount:.6f} XMR)"

            # Generate the payment URI
            payment_uri = generate_payment_uri(self.address.value, final_xmr_amount)

            # Generate the QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(payment_uri)
            qr.make(fit=True)
            qr_code_image = qr.make_image(fill_color="black", back_color="white")

            # Convert the QR code image to a Discord file
            with io.BytesIO() as image_binary:
                qr_code_image.save(image_binary, 'PNG')
                image_binary.seek(0)
                discord_file = discord.File(fp=image_binary, filename='qr_code.png')

            # Create embed with custom image if it exists
            embed = discord.Embed(
                title="💰 Monero Payment Request",
                description=f"You have received a payment request for **{amount_display}**",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Amount", value=amount_display, inline=True)
            embed.add_field(name="From Wallet", value=f"`{self.address.value}`", inline=False)
            
            image_path = os.path.join(os.path.dirname(__file__), 'images.jpg')
            if os.path.exists(image_path):
                # Attach the custom image to the embed
                custom_image = discord.File(image_path, filename='payment_header.jpg')
                embed.set_image(url="attachment://payment_header.jpg")
                # Send embed with custom image first
                await self.recipient_user.send(embed=embed, file=custom_image)
            else:
                # Send embed without custom image first
                await self.recipient_user.send(embed=embed)
            
            # Send QR code and payment URI as text for manual entry
            await self.recipient_user.send("📱 **Scan QR Code to Pay:**", file=discord_file)
            await self.recipient_user.send(f"**💳 Or copy this payment URI to your wallet:**")
            await self.recipient_user.send(f"\n{payment_uri}")

            # Create success embed
            embed = discord.Embed(
                title="✅ Transaction QR Code Generated",
                description=f"QR code has been sent to {self.recipient_user.mention}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Amount", value=amount_display, inline=True)
            embed.add_field(name="Recipient", value=self.recipient_user.mention, inline=True)
            embed.add_field(name="XMR Amount", value=f"{final_xmr_amount:.6f} XMR", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except ValueError as e:
            await interaction.response.send_message("❌ Invalid amount format. Please enter a valid number.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

# User Selection View
class UserSelectionView(ui.View):
    def __init__(self, guild):
        super().__init__(timeout=300)
        self.guild = guild

    @ui.select(
        placeholder="Choose a recipient...",
        options=[],  # Will be populated dynamically
        custom_id="user_select"
    )
    async def select_user(self, interaction: discord.Interaction, select: ui.Select):
        selected_user_id = int(select.values[0])
        selected_user = self.guild.get_member(selected_user_id)
        
        if selected_user:
            # Open the transaction modal with the selected user
            modal = TransactionModal(selected_user)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("❌ Selected user not found.", ephemeral=True)

    async def populate_user_options(self):
        try:
            # Ensure we have guild members loaded
            if self.guild.chunked is False:
                await self.guild.chunk(cache=True)
            
            # Get guild members (exclude bots and limit to first 25)
            members = [member for member in self.guild.members if not member.bot and member.id != bot.user.id][:25]
            
            print(f"Found {len(members)} members in guild {self.guild.name}")  # Debug log
            
            options = []
            for member in members:
                display_name = member.display_name if len(member.display_name) <= 100 else member.display_name[:97] + "..."
                options.append(
                    discord.SelectOption(
                        label=display_name,
                        value=str(member.id),
                        description=f"@{member.name}",
                        emoji="👤"
                    )
                )
            
            if options:
                self.children[0].options = options
            else:
                # Fallback if no members found
                self.children[0].options = [
                    discord.SelectOption(
                        label="No eligible members found",
                        value="0",
                        description="No non-bot server members available"
                    )
                ]
                
        except Exception as e:
            print(f"Error populating user options: {e}")  # Debug log
            # Fallback option
            self.children[0].options = [
                discord.SelectOption(
                    label="Error loading members",
                    value="0",
                    description="Unable to load server members"
                )
            ]

# Transaction View with button
class TransactionView(ui.View):
    def __init__(self, guild):
        super().__init__(timeout=300)
        self.guild = guild

    @ui.button(label='💰 Create Transaction', style=discord.ButtonStyle.primary, emoji='🔗')
    async def create_transaction(self, interaction: discord.Interaction, button: ui.Button):
        user_view = UserSelectionView(self.guild)
        await user_view.populate_user_options()
        
        embed = discord.Embed(
            title="👥 Select Recipient",
            description="Choose a server member to send the transaction QR code to:",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=user_view, ephemeral=True)

# Command to generate a QR code for a transaction
@bot.command(name='transact', description='Generate a QR code for a transaction.')
async def transact(ctx):
    # Check if command is used in a guild
    if ctx.guild is None:
        await ctx.send("❌ This command can only be used in a server, not in DMs.")
        return
    
    embed = discord.Embed(
        title="💰 Monero Transaction Generator",
        description="Click the button below to create a new transaction QR code",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.add_field(
        name="Instructions", 
        value="• Select a recipient from the server members\n• Enter the amount in XMR OR USD (not both)\n• Provide the recipient's Monero address", 
        inline=False
    )
    embed.add_field(
        name="Exchange Rate",
        value="*USD amounts are converted using approximate rates*",
        inline=False
    )
    
    view = TransactionView(ctx.guild)
    await ctx.send(embed=embed, view=view)

# Example usage of generate_payment_uri
address = "your_monero_address"
amount = 1.23
payment_id = "optional_payment_id"
uri = generate_payment_uri(address, amount, payment_id)
print(uri)

# Log all messages (optional, if you want to log them)
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'Message from [ {message.author} ]: "{message.content}" [ {message.channel}] [{timestamp}]')

    # Log to file
    with open('c:\\Users\\jacob\\Desktop\\murp\\log.txt', 'a') as log_file:
        log_file.write(f'Message from [ {message.author} ]: "{message.content}" [ {message.channel}] [{timestamp}]\n')

    # Ensure that commands are still processed
    await bot.process_commands(message)

# Function to handle graceful shutdown
def shutdown_handler(signum, frame):
    print("Shutting down the bot...")
    bot.loop.stop()

# Register the shutdown handler for SIGINT and SIGTERM
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# Run the bot
try:
    bot.run('MTM1MDM1NDc0OTQ1OTAwNTU1Mg.GR28BF.jjb-Ft_m7scpwhfjZsM97leFgfwaKdQMVmqHrE')  # Replace with your actual token
except Exception as e:
    print(f"An error occurred while running the bot: {e}")
finally:
    print("Bot has been stopped.")
