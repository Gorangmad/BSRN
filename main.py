import os
import random
import logging
import threading
import curses
from multiprocessing import Event
import posix_ipc
import time
from datetime import datetime

# Konfigurieren des Loggings für detaillierte Ausgaben
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Funktion zum Löschen des Bildschirms, abhängig vom Betriebssystem
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Funktionen für den Umgang mit POSIX-Nachrichtenwarteschlangen
def create_message_queue(name, max_message_size=1024):
    try:
        mq = posix_ipc.MessageQueue(name, flags=posix_ipc.O_CREAT, mode=0o666, max_message_size=max_message_size)
        return mq
    except Exception as e:
        logging.error(f"Error creating message queue: {e}")
        return None

def send_message(mq, message):
    try:
        mq.send(message.encode())
        logging.debug(f"Message sent successfully: {message}")
    except posix_ipc.BusyError as e:
        logging.error(f"Message queue is full or busy: {e}")
    except posix_ipc.ExistentialError as e:
        logging.error(f"Message queue does not exist: {e}")
    except posix_ipc.PermissionError as e:
        logging.error(f"Permission error while sending message: {e}")
    except Exception as e:
        logging.error(f"Error sending message: {e}")

def receive_message(mq, message_size=1024):
    try:
        message, _ = mq.receive(message_size)
        logging.debug(f"Message received: {message.decode()}")
        return message.decode()
    except Exception as e:
        logging.error(f"Error receiving message: {e}")
        return None

def cleanup_message_queue(mq, name):
    try:
        mq.close()
        mq.unlink()
    except Exception as e:
        logging.error(f"Error cleaning up message queue: {e}")

def wait_for_opponent(mq_name, start_event, init_mq):
    logging.debug("Waiting for opponent to join...")
    try:
        message = receive_message(init_mq)
        if message == 'start':
            logging.debug("Start message received.")
            start_event.set()
            logging.debug("Start event set, opponent has joined.")
    except Exception as e:
        logging.error(f"Error in wait_for_opponent: {e}")

def listen_for_messages(mq, game_won_event):
    while not game_won_event.is_set():
        try:
            message = receive_message(mq)
            if message and "won" in message:
                game_won_event.set()
                logging.debug("Game won message received.")
        except Exception as e:
            logging.error(f"Error in listen_for_messages: {e}")

def start_message_listener(mq_name, game_won_event):
    mq = create_message_queue(mq_name)
    listener_thread = threading.Thread(target=listen_for_messages, args=(mq, game_won_event))
    listener_thread.start()
    return listener_thread

def create_bingo_card(height, width, words):
    try:
        if len(words) < height * width - 1:  # subtract 1 for the Joker
            print("Not enough words in the word file.")
            return None

        random.shuffle(words)
        card = []
        for i in range(height):
            row = []
            for j in range(width):
                if (height % 2 != 0 and width % 2 != 0) and (i == height // 2 and j == width // 2):
                    row.append("JOKER")
                else:
                    row.append(words.pop())
            card.append(row)

        return card
    except Exception as e:
        logging.error(f"Error creating bingo card: {e}")
        return None

def read_bingo_cards(roundfile):
    try:
        with open(roundfile, 'r') as f:
            lines = f.readlines()
            height, width = None, None
            for line in lines:
                if line.startswith("Height:"):
                    height = int(line.split(":", 1)[1].strip())
                elif line.startswith("Width:"):
                    width = int(line.split(":", 1)[1].strip())

            if height is None or width is None:
                print("Height or width not found in the round file.")
                return None

            wordfile = None
            for line in lines:
                if line.startswith("Wordfile:"):
                    wordfile = line.split(":", 1)[1].strip()
                    break

            if wordfile is None:
                print("Wordfile not found in the round file.")
                return None

            with open(wordfile, 'r') as word_file:
                words = [line.strip() for line in word_file.readlines()]

            if len(words) < height * width:
                print("Not enough words in the word file.")
                return None

            cards = create_bingo_card(height, width, words)

            return cards
    except Exception as e:
        logging.error(f"Error reading bingo cards: {e}")
        return None

def display_bingo_cards(cards, mq_name, player_name, game_won_event, all_player_queues):
    log_file = create_log_file(player_name)
    log_message(log_file, "Start des Spiels")
    log_message(log_file, f"Größe des Spielfelds: {len(cards[0])}x{len(cards)}")
    
    try:
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)

        curses.start_color()
        curses.init_pair(1, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

        col_width = 15
        cursor_idx = (0, 0)
        selected_indices = {(len(cards) // 2, len(cards[0]) // 2)} if len(cards) % 2 != 0 else set()  # include Joker if odd-sized card

        while not game_won_event.is_set():
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
            key = stdscr.getch()
            if key == curses.KEY_UP:
                cursor_idx = (max(cursor_idx[0] - 1, 0), cursor_idx[1])
            elif key == curses.KEY_DOWN:
                cursor_idx = (min(cursor_idx[0] + 1, len(cards) - 1), cursor_idx[1])
            elif key == curses.KEY_RIGHT:
                cursor_idx = (cursor_idx[0], min(cursor_idx[1] + 1, len(cards[0]) - 1))
            elif key == curses.KEY_LEFT:
                cursor_idx = (cursor_idx[0], max(cursor_idx[1] - 1, 0))
            elif key == 10:  # Enter key to select
                if cursor_idx in selected_indices:
                    selected_indices.remove(cursor_idx)
                else:
                    selected_indices.add(cursor_idx)
                    log_message(log_file, f"{cards[cursor_idx[0]][cursor_idx[1]]} ({cursor_idx[0]}/{cursor_idx[1]})")
                if check_win(cards, selected_indices):
                    if not game_won_event.is_set():
                        for queue in all_player_queues:
                            send_message(queue, f"{player_name} won")
                        game_won_event.set()
                        log_message(log_file, "Sieg")
                        logging.debug("Game won, breaking display loop.")
                        break
            elif key == 27:  # Esc key
                log_message(log_file, "Abbruch")
                break

    except Exception as e:
        logging.error(f"Error displaying bingo cards: {e}")
    finally:
        curses.echo()
        curses.nocbreak()
        stdscr.keypad(False)
        curses.endwin()
        log_message(log_file, "Ende des Spiels")

def check_win(cards, selected_indices):
    n = len(cards)
    for row in range(n):
        if all((row, col) in selected_indices for col in range(n)):
            return True
    for col in range(n):
        if all((row, col) in selected_indices for row in range(n)):
            return True
    if all((i, i) in selected_indices for i in range(n)):
        return True
    if all((i, n - 1 - i) in selected_indices for i in range(n)):
        return True
    return False

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
        logging.error(f"Error checking access: {e}")
        return False

def create_player(roundfile, player_name):
    try:
        with open(roundfile, 'a') as f:
            f.write("player:" + player_name + '\n')
        print("Player created successfully.")
    except Exception as e:
        logging.error(f"Error creating player: {e}")

def create_round_file(roundfile, height, width, wordfile, max_players):
    try:
        with open(roundfile, 'w') as f:
            f.write(f"Max: {max_players}\n")
            f.write(f"Height: {height}\n")
            f.write(f"Width: {width}\n")
            f.write(f"Wordfile: {wordfile}\n")
        print("Round file created successfully.")
        return True
    except Exception as e:
        logging.error(f"Error creating round file: {e}")
        return False

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
            mq_name = "/mq_" + player_name
            create_message_queue(mq_name)
            return roundfile, mq_name, player_name
        else:
            print("Error creating the round file.")
            return None, None, None
    except Exception as e:
        logging.error(f"Error creating game: {e}")
        return None, None, None

def join_game(init_mq_name):
    try:
        roundfile = input("Please enter the name of the round file: ")
        player_name = input("Please enter your player name: ")

        if not os.path.exists(roundfile):
            print("Game not found.")
            return None, None, None

        if not check_access(roundfile, player_name):
            return None, None, None

        mq_name = "/mq_" + player_name
        create_message_queue(mq_name)
        create_player(roundfile, player_name)
        
        # Signal readiness
        send_message(posix_ipc.MessageQueue(init_mq_name), 'start')
        
        return roundfile, mq_name, player_name
    except Exception as e:
        logging.error(f"Error joining game: {e}")
        return None, None, None

def create_log_file(player_name):
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    log_folder = os.path.join(os.getcwd(), 'logfiles')
    os.makedirs(log_folder, exist_ok=True)  # Avoid error if directory already exists
    log_filename = f"{current_time}-bingo-{player_name}.txt"
    log_filepath = os.path.join(log_folder, log_filename)
    return log_filepath

def log_message(log_filepath, message):
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    with open(log_filepath, 'a') as log_file:
        log_file.write(f"{current_time} {message}\n")

def main():
    init_mq_name = "/init_queue"  # Common initialization queue
    init_mq = create_message_queue(init_mq_name, max_message_size=1024)  # Create it here for global usage
    global game_won_event
    game_won_event = threading.Event()

    try:
        print("Welcome to Multiplayer Bingo!")
        choice = input("Would you like to create a game (1) or join a game (2)? ")

        if choice == '1':
            roundfile, mq_name, player_name = create_game()
            if roundfile:
                print("Waiting for another player to join...")
                start_event = Event()
                wait_thread = threading.Thread(target=wait_for_opponent, args=(mq_name, start_event, init_mq))
                wait_thread.start()
                start_event.wait()
                wait_thread.join()
                print("Another player has joined the game.")
                cards = read_bingo_cards(roundfile)
                if cards:
                    with open(roundfile, 'r') as f:
                        player_queues = [line.split(":")[1].strip() for line in f if line.startswith("player:")]
                    all_player_queues = [create_message_queue(f"/mq_{name}") for name in player_queues]
                    start_message_listener(mq_name, game_won_event)
                    display_bingo_cards(cards, init_mq_name, player_name, game_won_event, all_player_queues)
                    

        elif choice == '2':
            roundfile, mq_name, player_name = join_game(init_mq_name)
            if roundfile:
                cards = read_bingo_cards(roundfile)
                if cards:
                    with open(roundfile, 'r') as f:
                        player_queues = [line.split(":")[1].strip() for line in f if line.startswith("player:")]
                    all_player_queues = [create_message_queue(f"/mq_{name}") for name in player_queues]
                    start_message_listener(mq_name, game_won_event)
                    display_bingo_cards(cards, mq_name, player_name, game_won_event, all_player_queues) 
        else:
            print("Invalid choice.")
            return

        if roundfile is None:
            return
    except Exception as e:
        logging.error(f"Error in main function: {e}")
    finally:
        pass


if _name_ == "_main_":
    main()

if name == "main":
    main()
