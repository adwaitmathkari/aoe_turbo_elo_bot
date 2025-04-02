import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import json
import os
import random
from itertools import combinations
import time
from dotenv import load_dotenv
import subprocess
load_dotenv()

################################################## Constants Start #################################################

PLAYER_FILE = "players.json"

################################################## Constants End #################################################
################################################## Game Objects Code Start ###########################################

#TODO eventually use these class (Ratings, Player, Team)
class Rating:
    def __init__(self):
        self.mapToRatingDict = {}

    def get_rating(self, map):
        #this will return the rating specific to the map
        return 1000

class Player:
    def __init__(self, name, rating: Rating):
        self.name = name
        self.rating = rating

    def get_rating(self, map):
        return self.rating.get_rating(map)

class Team:
    #TODO make this list of Players
    def __init__(self, players):
        self.players = players
        pass

    def get_rating(self, map):
        ratings_sum = 0
        for player in players:
            ratings_sum += player.get_rating(map)
        return ratings_sum

class Game:
    #TODO eventually make this def __init__(self, team1: Team, team2: Team):
    def __init__(self, id, team1, team2, map="arabia"):
        self.team1 = team1
        self.team2 = team2
        self.is_complete = False
        self.id = id #random.randint(0,100000000000000)
        self.map = map

    #TODO add code to tell which team won
    def markComplete(self):
        self.is_complete = True

    #TODO move the update rating function here
    def _update_rating(self):
        pass


################################################## Game Objects Code End ###########################################
################################################## Bot Initiation Start ###########################################

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

PLAYER_FILE = "players.json"
#TODO move this list to file
AUTHORIZED_USERS =  ['adwaitmathkari', 'mania4861', 'bajirao2', 'darklordkunal', '2kminus1', 'adityasj3053', 'adityasj.','ajeya7182', '.sidonkar', 'sarthakss', 'shalmal90']
MAX_CHECK = 6

def load_players():
    if os.path.exists(PLAYER_FILE):
        try:
            with open(PLAYER_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (json.JSONDecodeError, ValueError):
            pass
    return {}


def save_players():
    with open(PLAYER_FILE, "w") as f:
        json.dump(players, f, indent=4)
        f.flush()  # Ensure data is written before closing
        os.fsync(f.fileno())  # Force write to disk
        # Call the function after updating the JSON file
        push_to_github()

def push_to_github():
    # Check if the file is empty before pushing
    if os.path.getsize(PLAYER_FILE) == 0:
        print("⚠️ Error: File is empty. Not pushing to GitHub.")
        return  
    
    """Commits and pushes changes to GitHub."""
    repo_url = os.getenv("GITHUB_REPO")  # Get GitHub repo URL from environment variables
    github_token = os.getenv("GITHUB_TOKEN")  # Get GitHub token

    # Configure Git username & email
    subprocess.run(["git", "config", "--global", "user.name", "Onkar"])
    subprocess.run(["git", "config", "--global", "user.email", "sidonkar@gmail.com"])

    # Set up authentication in the repo URL
    auth_repo_url = repo_url.replace("https://", f"https://{github_token}@")

    # Add, commit, and push changes
    subprocess.run(["git", "add", PLAYER_FILE])
    subprocess.run(["git", "commit", "-m", "Updated Player and Match data "+time.strftime("%Y-%m-%d %H:%M:%S")])
    subprocess.run(["git", "push", auth_repo_url, "main"])  # Change "main" to your branch name if different

    print("✅ JSON file pushed to GitHub!")



players = load_players()

#global variables
#ideally we should store them but this isn't needed for our use-case
processed_matches = {}  # Use a dictionary to store match timestamps
game_ids = set()

def print_game_state():
    print("processed matches")
    print(processed_matches)
    print("game_ids")
    print(game_ids)

@bot.event
async def on_ready():
    print(f"✅ Bot is online! Logged in as {bot.user}")
    # bot.add_view(MultiColumnPlayerSelectionView())  # Register persistent view
    # bot.add_view(MatchupSelectionView(bot))  # Register persistent view
    bot.add_view(WinnerSelectionView(bot,bot,bot))  # Register persistent view


@bot.command(name="Admin")
async def show_admin_menu(ctx):
    if (ctx.author.name not in AUTHORIZED_USERS):
        await ctx.send("Admin नाय भाऊ तू!! जास्त टाकली काय आज?")
        return
    await ctx.send("📌 **Admin Menu - Select an action below:**", view=AdminMenuView())

# ✅ Admin Menu View
class AdminMenuView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RegisterButton())
        self.add_item(AllPlayersButton())
        self.add_item(RemovePlayerButton())


class RegisterButton(Button):

    def __init__(self):
        super().__init__(label="Register Player",
                         style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RegisterModal())


class AllPlayersButton(Button):

    def __init__(self):
        super().__init__(label="Show All Players",
                         style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await send_all_players(interaction)


class RemovePlayerButton(Button):

    def __init__(self):
        super().__init__(label="Remove Player",
                         style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "🗑️ Select a player to remove:", view=RemovePlayerView())


class RemovePlayerView(View):

    def __init__(self):
        super().__init__(timeout=60)

        player_list = [(name, players[name]["current_rating"])
                       for name in players.keys()]
        player_list.sort(key=lambda x: x[1], reverse=True)
        self.players = player_list
        self.current_page = 0
        self.players_per_page = 20
        self.total_pages = (len(players) - 1) // self.players_per_page + 1

        self.remove_player_update_buttons()

    def remove_player_update_buttons(self):
        self.clear_items()
        start_idx = self.current_page * self.players_per_page
        end_idx = min(start_idx + self.players_per_page, len(self.players))
        print(f"start_idx: {start_idx}, end_idx: {end_idx}, players:{players}")
        for name, rating in self.players[start_idx:end_idx]:
            self.add_item(RemovePlayerButtonOption(name))
        if self.total_pages > 1:
            # Dynamically add line breaks based on last row count
            last_row_count = (end_idx - start_idx) % 5
            linebreak_count = max(0, 5 -
                                  last_row_count) if last_row_count > 0 else 0
            for _ in range(linebreak_count):
                self.add_item(SpacerButton())
            self.add_item(PrevPageButton(self))
            self.add_item(NextPageButton(self))

    async def update_message(self, interaction: discord.Interaction):
        self.remove_player_update_buttons()
        await interaction.response.edit_message(view=self)


class RemovePlayerButtonOption(Button):

    def __init__(self, player_name):
        super().__init__(label=player_name, style=discord.ButtonStyle.danger)
        self.player_name = player_name

    async def callback(self, interaction: discord.Interaction):
        del players[self.player_name]
        save_players()
        await interaction.response.send_message(
            f"🗑️ Player {self.player_name} has been removed.")


class RegisterModal(Modal, title="Player Registration"):
    name = TextInput(label="Player Name", placeholder="Enter player name")
    base_rating = TextInput(label="Base Rating",
                            placeholder="Enter base rating",
                            style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        name = self.name.value.strip()
        try:
            base_rating = int(self.base_rating.value.strip())
        except ValueError:
            await interaction.response.send_message(
                "⚠️ Invalid rating! Please enter a number.", ephemeral=True)
            return
        if name in players:
            await interaction.response.send_message(
                f"⚠️ Player {name} is already registered!", ephemeral=True)
            return
        players[name] = {
            "base_rating": base_rating,
            "current_rating": base_rating,
            "highest_rating": base_rating,
            "lowest_rating": base_rating,
            "matches_played": 0,
            "wins": 0,
            "losses": 0
        }
        save_players()
        await interaction.response.send_message(
            f"✅ Player {name} registered with base rating {base_rating}!")


async def send_all_players(interaction):
    if not players:
        await interaction.response.send_message("⚠️ No players registered yet!"
                                                )
        return

    MAX_FIELDS = 25  # Discord limit
    embeds = []
    player_items = sorted(players.items(),key=lambda x: x[1]["current_rating"], reverse=True)

    # player_items = list(player_list.keys())  # Convert dict to list
    for i in range(0, len(player_items), MAX_FIELDS):
        embed = discord.Embed(title="**Player Name**  |  🔥 **Live**  |  🚀 **Max** |  💥 **Min**  \n  🏅 **Base**  |  ⚔️ **Matches**  |  🎯 **Win**  | 💀 **Loss**",
                              color=discord.Color.blue())
        for name, data in player_items[
                i:i + MAX_FIELDS]:  # Process only 25 at a time
            base_rating = data.get("base_rating", "N/A")
            current_rating = data.get("current_rating", "N/A")
            max_rating = data.get("highest_rating", "N/A")
            min_rating = data.get("lowest_rating", "N/A")
            matches_played = data.get("matches_played", "N/A")
            wins= data.get("wins", "N/A")
            losses = data.get("losses", "N/A")
            # embed.add_field(
            #     name=name,
            #     value=
            #     f"🏅 Base Rating: {base_rating}\n🔥 Current Rating: {current_rating}\n💥 Min Rating: {min_rating}\n🚀 Max Rating: {max_rating}\n",
            #     inline=False)
            embed.add_field(
                name="\u200b",
                value=f"```"
                f"{name} | 🔥 {current_rating} |"
                f" 🚀 {max_rating} |"
                f" 💥 {min_rating}\n"
                f" 🏅 {base_rating} |"
                f" ⚔️ {matches_played} |"
                f" 🎯 {wins} |"
                f" 💀 {losses}"
                f"```",
                inline=False
            )

        embeds.append(embed)

    await interaction.response.defer()

    # ✅ Use followup to send multiple embeds
    for embed in embeds:
        await interaction.followup.send(embed=embed)

    # embed = discord.Embed(title="📋 **Registered Players**",
    #                       color=discord.Color.blue())
    # for name, data in players.items():
    #     base_rating = data.get("base_rating", "N/A")
    #     current_rating = data.get("current_rating", "N/A")
    #     embed.add_field(
    #         name=name,
    #         value=
    #         f"🏅 Base Rating: {base_rating}\n🔥 Current Rating: {current_rating}",
    #         inline=False)
    # await interaction.response.send_message(embed=embed)

@bot.command(name="result")
async def set_result_manually(ctx, game_id_str):
    if (ctx.author.name not in AUTHORIZED_USERS):
        await ctx.send('Admin नाय भाऊ तू! कोणी दूसरा आहे का बघ..')
        return

    game_id = int(game_id_str)

    if (game_id not in processed_matches):
        await ctx.send('invalid game id!!!!')
        return
    if (processed_matches[game_id].is_complete):
        await ctx.send('match result recorded already!!!')
        return

    game = processed_matches[game_id]
    await ctx.send("**Select the winner!**", view=WinnerSelectionView(game_id, game.team1, game.team2))

@bot.command(name="chala")
async def pick_team(ctx):
    if not players:
        await ctx.send("⚠️ No players registered yet!")
        return
    await ctx.send("👥 **Select up to 8 players for the match:**",
                   view=MultiColumnPlayerSelectionView())


class MultiColumnPlayerSelectionView(View):

    def __init__(self, max_selections=8):
        super().__init__(timeout=None)
        player_list = [(name, players[name]["current_rating"])
                       for name in players.keys()]
        player_list.sort(key=lambda x: x[1], reverse=True)

        self.players = player_list
        self.max_selections = max_selections
        self.selected_players = []
        self.current_page = 0
        self.players_per_page = 20
        self.total_pages = (len(players) - 1) // self.players_per_page + 1

        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        start_idx = self.current_page * self.players_per_page
        end_idx = min(start_idx + self.players_per_page, len(self.players))

        for name, rating in self.players[start_idx:end_idx]:
            style = discord.ButtonStyle.success if name in self.selected_players else discord.ButtonStyle.primary
            self.add_item(PlayerButton(name, rating, self, style))

        if self.total_pages > 1:
            # Dynamically add line breaks based on last row count
            last_row_count = (end_idx - start_idx) % 5
            linebreak_count = max(0, 5 -
                                  last_row_count) if last_row_count > 0 else 0
            for _ in range(linebreak_count):
                self.add_item(SpacerButton())
            self.add_item(PrevPageButton(self))

        self.confirm_button = ConfirmMatchupsButton(self)
        self.confirm_button.label = f"Confirm Selection ({len(self.selected_players)}/8)"
        # self.clear_button = ClearSelectionButton(self)
        self.add_item(self.confirm_button)
        # self.add_item(self.clear_button)
        if (len(self.selected_players) < MAX_CHECK):
            self.confirm_button.disabled = True
        if self.total_pages > 1:
            self.add_item(NextPageButton(self))

    async def update_message(self, interaction: discord.Interaction):
        self.update_buttons()
        await interaction.response.edit_message(view=self)


class PlayerButton(Button):

    def __init__(self, name, rating, parent_view, style):
        super().__init__(label=f"{name} ({rating})", style=style)
        self.name = name
        self.rating = rating
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if self.name in self.parent_view.selected_players:
            self.parent_view.selected_players.remove(self.name)
            self.style = discord.ButtonStyle.primary
        else:
            if len(self.parent_view.selected_players
                   ) < self.parent_view.max_selections:
                self.parent_view.selected_players.append(self.name)
                self.style = discord.ButtonStyle.success

        self.parent_view.confirm_button.label = f"Confirm Selection ({len(self.parent_view.selected_players)}/8)"
        self.parent_view.confirm_button.disabled = len(
            self.parent_view.selected_players) < MAX_CHECK
        await interaction.response.edit_message(view=self.parent_view)


class SpacerButton(discord.ui.Button):

    def __init__(self):
        super().__init__(label="\u200b",
                         style=discord.ButtonStyle.secondary,
                         disabled=True)


class PrevPageButton(discord.ui.Button):

    def __init__(self, parent_view):
        super().__init__(label="Previous", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if self.parent_view.current_page > 0:
            self.parent_view.current_page -= 1
            await self.parent_view.update_message(interaction)


class NextPageButton(discord.ui.Button):

    def __init__(self, parent_view):
        super().__init__(label="Next", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if self.parent_view.current_page < self.parent_view.total_pages - 1:
            self.parent_view.current_page += 1
            await self.parent_view.update_message(interaction)


class ConfirmMatchupsButton(Button):

    def __init__(self, parent_view):
        super().__init__(label="Confirm Selection (0/8)",
                         style=discord.ButtonStyle.success)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if len(self.parent_view.selected_players) < MAX_CHECK:
            await interaction.response.send_message(
                "⚠️ Select at least 6 players to form teams.", ephemeral=True)
            return

        matchups = generate_matchups(self.parent_view.selected_players)
        await interaction.response.send_message(
            embed=create_matchup_embed(matchups),
            view=MatchupSelectionView(matchups))


# class ClearSelectionButton(Button):

#     def __init__(self, parent_view):
#         super().__init__(label="Clear Selection",
#                          style=discord.ButtonStyle.secondary)
#         self.parent_view = parent_view

#     async def callback(self, interaction: discord.Interaction):
#         self.parent_view.selected_players=[]
#         self.parent_view.confirm_button.disabled = True
#         await interaction.response.edit_message(view=self.parent_view)


class MatchupSelectionView(View):

    def __init__(self, matchups):
        super().__init__(timeout=None)
        self.matchups = matchups

        for i, (team1, team2, rating1, rating2, diff) in enumerate(matchups,
                                                                   start=1):
            label = f"Select Matchup {i}"
            self.add_item(MatchupButton(label, team1, team2))


class MatchupButton(Button):

    def __init__(self, label, team1, team2):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.team1 = team1
        self.team2 = team2

    async def callback(self, interaction: discord.Interaction):
        game_id = random.randint(0,100000000000000)
        while game_id in game_ids:
            game_id = random.randint(0,100000000000000)

        game_ids.add(game_id)
        game = Game(game_id, team1=self.team1, team2=self.team2, map="arabia") #TODO pass the map here
        processed_matches[game_id] = game

        await interaction.response.send_message(
            f"✅ **You selected Matchup:**\n"
            f"**Team 1:** {', '.join(self.team1)}\n"
            f"**Team 2:** {', '.join(self.team2)}\n\n"
            f"** Game id:** {game_id}\n\n"
            f"🔽 **Now select the winner!**",
            view=WinnerSelectionView(game_id, self.team1, self.team2)
        )

class WinnerSelectionView(View):
    def __init__(self, game_id, team1, team2):
        super().__init__(timeout=None)
        self.game_id = game_id
        self.team1 = team1
        self.team2 = team2

        self.add_item(WinnerButton("Team 1 Wins", game_id, team1, team2))
        self.add_item(WinnerButton("Team 2 Wins", game_id, team2, team1))

# Track processed matches to prevent duplicate ELO updates

import time  # Ensure time is imported

# Define a cooldown period (in seconds) before allowing the same matchup again
MATCH_COOLDOWN = 20  # 20 seconds


class WinnerButton(Button):
    def __init__(self, label, game_id, winning_team, losing_team):
        super().__init__(label=label, style=discord.ButtonStyle.success)
        self.game_id = game_id
        self.winning_team = winning_team
        self.losing_team = losing_team

    async def callback(self, interaction: discord.Interaction):
        
        user = interaction.user
        if (user.name not in AUTHORIZED_USERS):
            await interaction.response.send_message('Admin नाय भाऊ तू! कोणी दूसरा आहे का बघ..')
            return

        if (self.game_id not in processed_matches):
            await interaction.response.send_message("⚠️ Invalid Game Id. Try again later.",ephemeral=True)
            return

        if (processed_matches[self.game_id].is_complete):
            await interaction.response.send_message(
                "⚠️ ELO ratings have already been updated for this matchup recently! Try again later.",
                ephemeral=True)
            return

        # Update the match time to allow new results
        #processed_matches[
        #    matchup_key] = current_time  # ✅ Now it updates and allows future matches

        # Get total team ratings
        winning_team_rating = sum(players[p]["current_rating"]
                                  for p in self.winning_team)
        losing_team_rating = sum(players[p]["current_rating"]
                                 for p in self.losing_team)
        rating_diff = abs(winning_team_rating - losing_team_rating)

        # Default gains/losses
        base_gain = 6
        base_loss = -6

        if rating_diff >= 100:  # Large difference case
            if winning_team_rating < losing_team_rating:  # Underdog wins
                gain, loss = 8, -8
            else:  # Favorite wins
                gain, loss = 4, -4
        else:
            gain, loss = base_gain, base_loss

        # Update ratings and generate message
        message = "🏆 **Match Result**\n\n"

        embed = discord.Embed(
            title="📊 Match Result",
            description="Here are your match results:",
            color=discord.Color.blue()
        )

        
        

        for player in self.winning_team:
            players[player]["current_rating"] += gain
            players[player]["matches_played"] += 1
            players[player]["wins"] += 1
            players[player]["highest_rating"] = max(players[player]["highest_rating"], players[player]["current_rating"])
            message += f"🎯 **{player}**\t\t+{gain}\t🔥 {players[player]['current_rating']}\t⚔️ {players[player]["matches_played"]}\t🎯 {players[player]["wins"]}\t💀 {players[player]["losses"]}\n"
            # embed.add_field(
            #     name=player,
            #     value=f"```"
            #     f"+ {gain}  | 🔥 {players[player]['current_rating']} |"
            #     f" ⚔️ {players[player]["matches_played"]} |"
            #     f" 🎯 {players[player]["wins"]} |"
            #     f" 💀 {players[player]["losses"]}"
            #     f"```",
            #     inline=False)
        message+="\n"
        for player in self.losing_team:
            players[player]["current_rating"] += loss
            players[player]["matches_played"] += 1
            players[player]["losses"] += 1
            players[player]["lowest_rating"] = min(players[player]["lowest_rating"], players[player]["current_rating"])            
            message += f"💀 **{player}**\t\t{loss}\t🔥 {players[player]['current_rating']}\t⚔️ {players[player]["matches_played"]}\t🎯 {players[player]["wins"]}\t💀 {players[player]["losses"]}\n"
            # embed.add_field(
            #     name=player,
            #     value=f"```"
            #     f"{loss}  | 🔥 {players[player]['current_rating']} |"
            #     f" ⚔️ {players[player]["matches_played"]} |"
            #     f" 🎯 {players[player]["wins"]} |"
            #     f" 💀 {players[player]["losses"]}"
            #     f"```",
            #     inline=False)
        # Save updated ratings
        save_players()
        processed_matches[self.game_id].is_complete = True

        # Send the result message
        await interaction.response.send_message(message)
        # await interaction.response.send_message(embed=embed)


def update_elo_ratings(winning_team, losing_team, k_factor=10):
    rating_changes = {}

    for player in winning_team:
        old_rating = players[player]["current_rating"]
        change = k_factor
        players[player]["current_rating"] += change
        rating_changes[player] = (players[player]["current_rating"], change
                                  )  # Store (new_rating, change)

    for player in losing_team:
        old_rating = players[player]["current_rating"]
        change = -k_factor
        players[player]["current_rating"] += change
        rating_changes[player] = (players[player]["current_rating"], change
                                  )  # Store (new_rating, change)

    return rating_changes


def create_balanced_teams(players):
    num_players = len(players)
    players_data = {p: players[p]["current_rating"] for p in players}
    all_possible_matchups = []

    for combo in combinations(players, num_players // 2):
        team1 = list(combo)
        team2 = [p for p in players if p not in team1]

        rating1 = sum(players_data[p] for p in team1)
        rating2 = sum(players_data[p] for p in team2)
        diff = abs(rating1 - rating2)

        all_possible_matchups.append((team1, team2, rating1, rating2, diff))

    # Sort by rating difference (smallest first)
    all_possible_matchups.sort(key=lambda x: x[4])

    best_matchup = all_possible_matchups[0]  # Least difference
    second_best_matchup = None

    # Find a second-best distinct matchup (ensuring it's not just swapped)
    for matchup in all_possible_matchups[1:]:
        if set(matchup[0]) != set(
                best_matchup[1]):  # Ensure it's a different team split
            second_best_matchup = matchup
            break

    if second_best_matchup is None:  # Fallback if no distinct second matchup is found
        second_best_matchup = all_possible_matchups[1] if len(
            all_possible_matchups) > 1 else best_matchup

    return [best_matchup, second_best_matchup]


def generate_matchups(selected_players):
    selected_players_data = {
        player: players[player]
        for player in selected_players
    }

    if len(selected_players) < 4 or len(selected_players) % 2 != 0:
        return [([], [], 0, 0)]

    matchups = create_balanced_teams(selected_players_data)
    return matchups


def create_matchup_embed(matchups):
    embed = discord.Embed(title="🔀 Matchup Options",
                          description="Choose a balanced team matchup!",
                          color=discord.Color.blue())

    for i, (team1, team2, rating1, rating2, diff) in enumerate(matchups,
                                                               start=1):
        embed.add_field(name=f"Matchup {i}",
                        value=f"```"
                        f"Team 1: {', '.join(team1)} (Rating: {rating1})\n"
                        f"Team 2: {', '.join(team2)} (Rating: {rating2})\n"
                        f"Difference: {diff}"
                        f"```",
                        inline=False)
    return embed


@bot.command(name="show")
async def show_players_menu(ctx):
    await ctx.send("📋 **Player List - Click below to view all players**",
                   view=AllPlayersView())


class AllPlayersView(View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AllPlayersButton())  # Reusing the button from Admin Menu


TOKEN = os.getenv("DISCORD_BOT_TOKEN")
bot.run(TOKEN)
