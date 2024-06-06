import os
import random
import time
import win32pipe
import win32file
import curses

# Function to clear the terminal screen
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Function to create a bingo card
def create_bingo_card(height, width, words):
    try:
        if len(words) < height * width:
            print("Not enough words in the word file.")
            return None
        
        random.shuffle(words)
        card = []
        for _ in range(height):
            row = []
            for _ in range(width):
                row.append(words.pop())
            card.append(row)
        
        return card
    except Exception as e:
        print("Error creating bingo card:", e)
        return None

    
# Function to read bingo cards from the round file
def read_bingo_cards(roundfile):
    try:
        with open(roundfile, 'r') as f:
            lines = f.readlines()
            
            # Extract height and width
            height, width = None, None
            for line in lines:
                if line.startswith("Height:"):
                    height = int(line.split(":", 1)[1].strip())
                elif line.startswith("Width:"):
                    width = int(line.split(":", 1)[1].strip())
            
            if height is None or width is None:
                print("Height or width not found in the round file.")
                return None

            # Extract the name of the word file
            wordfile = None
            for line in lines:
                if line.startswith("Wordfile:"):
                    wordfile = line.split(":", 1)[1].strip()
                    break

            # If wordfile is not found, return None
            if wordfile is None:
                print("Wordfile not found in the round file.")
                return None

            # Read words from the wordfile
            with open(wordfile, 'r') as word_file:
                words = [line.strip() for line in word_file.readlines()]

            # Check if enough words are available
            if len(words) < height * width:
                print("Not enough words in the word file.")
                return None

            # Create bingo cards
            cards = create_bingo_card(height, width, words)
            
            return cards
    except Exception as e:
        print("Error reading bingo cards:", e)
        return None



# Function to display bingo cards in the terminal using curses
def display_bingo_cards(cards):
    try:
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)

        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_MAGENTA, curses.COLOR_BLACK)  # For cursor
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)  # For selected word

        col_width = 15  # Width of each column
        cursor_idx = (0, 0)  # Cursor index to track the current word (row, column)
        selected_indices = set()  # Indices of permanently selected words

        while True:
            stdscr.clear()
            for row, card_row in enumerate(cards):
                for col, word in enumerate(card_row):
                    word_to_display = word[:col_width]
                    padding = " " * (col_width - len(word_to_display))
                    if (row, col) == cursor_idx:
                        stdscr.addstr(f"{word_to_display}{padding}", curses.color_pair(1))
                    elif (row, col) in selected_indices:
                        stdscr.addstr(f"{word_to_display}{padding}", curses.color_pair(2) | curses.A_BOLD)
                    else:
                        stdscr.addstr(f"{word_to_display}{padding}")
                    if col < len(card_row) - 1:
                        stdscr.addstr("  ")

                stdscr.addstr("\n")

            stdscr.refresh()

            # Wait for user input to move cursor or select word
            key = stdscr.getch()
            if key == curses.KEY_UP:
                cursor_idx = (max(cursor_idx[0] - 1, 0), cursor_idx[1])
            elif key == curses.KEY_DOWN:
                cursor_idx = (min(cursor_idx[0] + 1, len(cards) - 1), cursor_idx[1])
            elif key == curses.KEY_RIGHT:
                cursor_idx = (cursor_idx[0], min(cursor_idx[1] + 1, len(cards[0]) - 1))
            elif key == curses.KEY_LEFT:
                cursor_idx = (cursor_idx[0], max(cursor_idx[1] - 1, 0))
            elif key == 10:  # Enter key
                if cursor_idx in selected_indices:
                    selected_indices.remove(cursor_idx)  # Deselect if already selected
                else:
                    selected_indices.add(cursor_idx)
            elif key == 27:  # Esc key
                break

    except Exception as e:
        curses.echo()
        curses.nocbreak()
        stdscr.keypad(False)
        curses.endwin()
        print("Error displaying bingo cards:", e)




# Function to check if there are enough players for the game
def enough_players(roundfile):
    try:
        with open(roundfile, 'r') as f:
            players = [line.strip() for line in f.readlines()]
        
        num_players = sum(1 for player in players if player.startswith("player:"))
        
        return num_players >= 2
    except Exception as e:
        print("Error checking players:", e)
        return False

# Function to check if a player has access to the game
def check_access(roundfile, player_name):
    try:
        if not os.path.exists(roundfile):
            print("Game not found.")
            return False
        
        with open(roundfile, 'r') as f:
            players = f.readlines()
        
        if player_name + '\n' in players:
            print("Player name already taken.")
            return False
        
        return True
    except Exception as e:
        print("Error checking access:", e)
        return False

# Function to create a new player
def create_player(roundfile, player_name):
    try:
        with open(roundfile, 'a') as f:
            f.write("player:" + player_name + '\n')
        print("Player created successfully.")
    except Exception as e:
        print("Error creating player:", e)

def create_round_file(roundfile, height, width, wordfile, max_players):
    try:
        
        with open(roundfile, 'w') as f:
            f.write(f"Max: {max_players}\n")  # Write max players
            f.write(f"Height: {height}\n")  # Write height and width
            f.write(f"Width: {width}\n")  # Write height and width
            f.write(f"Wordfile: {wordfile}\n")
        print("Round file created successfully.")
        return True
    except Exception as e:
        print("Error creating round file:", e)
        return False


# Function to create a new game
def create_game():
    try:
        roundfile = input("Please enter the name of the round file: ")
        player_name = input("Please enter your player name: ")

        height = int(input("Please enter the height of the bingo cards: "))
        width = int(input("Please enter the width of the bingo cards: "))
        wordfile = input("Please enter the name of the word file: ")
        max_players = int(input("Please enter the maximum number of players: "))

        if create_round_file(roundfile, height, width, wordfile, max_players):
            create_player(roundfile, player_name)
            return roundfile, r'\\.\pipe\bingo_pipe'
        else:
            print("Error creating the round file.")
            return None, None
    except Exception as e:
        print("Error creating game:", e)
        return None, None

# Function to join an existing game
def join_game():
    try:
        roundfile = input("Please enter the name of the round file: ")
        player_name = input("Please enter your player name: ")

        if not os.path.exists(roundfile):
            print("Game not found.")
            return None, None

        if not check_access(roundfile, player_name):
            return None, None

        # Return the pipe name as well
        return roundfile, r'\\.\pipe\bingo_pipe'
    except Exception as e:
        print("Error joining game:", e)
        return None, None

# Function to check if the second player has joined using named pipe
def check_second_player_joined(pipe):
    try:
        print(pipe)
        win32pipe.ConnectNamedPipe(pipe, None)
        return True
    except Exception as e:
        print("Error connecting to named pipe:", e)
        return False


# Main function
def main():
    try:
        print("Welcome to Multiplayer Bingo!")
        choice = input("Would you like to create a game (1) or join a game (2)? ")

        pipe = None

        if choice == '1':
            roundfile, pipe_name = create_game()
            pipe = win32pipe.CreateNamedPipe(
                pipe_name,
                win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_WAIT,
                win32pipe.PIPE_UNLIMITED_INSTANCES,
                65536, 65536,
                0,
                None
            )
        elif choice == '2':
            roundfile, pipe_name = join_game()
            if pipe_name:
                pipe = win32file.CreateFile(
                    pipe_name,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
                # Display bingo cards for both players after they join the game
                cards = read_bingo_cards(roundfile)
                if cards:
                    display_bingo_cards(cards)
                # Since the second player joins, it doesn't need to check for the second player again
                return
        else:
            print("Invalid choice.")
            return

        if roundfile is None:
            return

        # Check if both players have joined the game
        while True:
            print("Waiting for another player...")
            if check_second_player_joined(pipe):
                print("Another player has joined the game.")
                # Display bingo cards for both players after they join the game
                cards = read_bingo_cards(roundfile)
                if cards:
                    display_bingo_cards(cards)
                break
            else:
                print("Unable to connect to another player. Retrying...")
                time.sleep(2)
    except Exception as e:
        print("Error in main function:", e)

if _name_ == "_main_":
    main()
