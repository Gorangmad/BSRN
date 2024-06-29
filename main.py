import os
import random
import logging
import threading
import curses
import posix_ipc
import time
import argparse
from datetime import datetime

# Konfiguriere Logging für detaillierte Ausgaben
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Bildschirm löschen
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Erstellen einer Nachrichtenwarteschlange
def create_message_queue(name, max_message_size=1024):
    try:
        mq = posix_ipc.MessageQueue(name, flags=posix_ipc.O_CREAT, mode=0o666, max_message_size=max_message_size)
        return mq
    except Exception as e:
        logging.error(f"Fehler beim Erstellen der Nachrichtenwarteschlange: {e}")
        return None

# Nachricht senden
def send_message(mq, message):
    try:
        mq.send(message.encode())
        logging.debug(f"Nachricht erfolgreich gesendet: {message}")
    except posix_ipc.BusyError as e:
        logging.error(f"Nachrichtenwarteschlange ist voll oder beschäftigt: {e}")
    except posix_ipc.ExistentialError as e:
        logging.error(f"Nachrichtenwarteschlange existiert nicht: {e}")
    except posix_ipc.PermissionError as e:
        logging.error(f"Berechtigungsfehler beim Senden der Nachricht: {e}")
    except Exception as e:
        logging.error(f"Fehler beim Senden der Nachricht: {e}")

# Nachricht empfangen
def receive_message(mq, message_size=1024):
    try:
        message, _ = mq.receive(message_size)
        return message.decode()
    except Exception as e:
        logging.error(f"Fehler beim Empfangen der Nachricht: {e}")
        return None

# Nachrichtenwarteschlange bereinigen
def cleanup_message_queue(mq, name):
    try:
        mq.close()
        mq.unlink()
    except Exception as e:
        logging.error(f"Fehler beim Bereinigen der Nachrichtenwarteschlange: {e}")

# Warten auf den Gegner
def wait_for_opponent(mq_name, start_event, init_mq):
    logging.debug("Warten auf den Beitritt des Gegners...")
    try:
        while True:
            message = receive_message(init_mq)
            if message == 'start':
                logging.debug("Startnachricht erhalten.")
                start_event.set()
                logging.debug("Start-Event gesetzt, Gegner ist beigetreten.")
                break
    except Exception as e:
        logging.error(f"Fehler im wait_for_opponent: {e}")

# Nachrichten abhören
def listen_for_messages(mq, game_won_event, game_aborted_event, player_queues, players, log_file):
    while not game_won_event.is_set() and not game_aborted_event.is_set():
        try:
            message = receive_message(mq)
            if message:
                logging.debug(f"{message}")
                if "won" in message:
                    game_won_event.set()
                elif "aborted" in message:
                    game_aborted_event.set()
                    log_message(log_file, "Abbruch")
                elif "player joined" in message:
                    new_player = message.split(":")[1].strip()
                    if new_player not in players:
                        players.append(new_player)
                        for queue in player_queues:
                            send_message(queue, message)
        except Exception as e:
            logging.error(f"Fehler im listen_for_messages: {e}")

# Starten des Nachrichtendienstes
def start_message_listener(mq_name, game_won_event, game_aborted_event, player_queues, players, log_file):
    mq = create_message_queue(mq_name)
    listener_thread = threading.Thread(target=listen_for_messages, args=(mq, game_won_event, game_aborted_event, player_queues, players, log_file))
    listener_thread.start()
    return listener_thread

# Erstellen einer Bingokarte
def create_bingo_card(height, width, words):
    try:
        if len(words) < height * width - 1:
            print("Nicht genügend Wörter in der Wortdatei.")
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
        logging.error(f"Fehler beim Erstellen der Bingokarte: {e}")
        return None

# Lesen der Bingokarten aus der Rundendatei
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
                print("Höhe oder Breite in der Rundendatei nicht gefunden.")
                return None
            wordfile = None
            for line in lines:
                if line.startswith("Wordfile:"):
                    wordfile = line.split(":", 1)[1].strip()
                    break
            if wordfile is None:
                print("Wortdatei in der Rundendatei nicht gefunden.")
                return None
            with open(wordfile, 'r') as word_file:
                words = [line.strip() for line in word_file.readlines()]
            if len(words) < height * width:
                print("Nicht genügend Wörter in der Wortdatei.")
                return None
            cards = create_bingo_card(height, width, words)
            return cards
    except Exception as e:
        logging.error(f"Fehler beim Lesen der Bingokarten: {e}")
        return None

# Lesen der Spieler aus der Rundendatei
def read_players_from_roundfile(roundfile):
    try:
        with open(roundfile, 'r') as f:
            lines = f.readlines()
        players = [line.split(":", 1)[1].strip() for line in lines if line.startswith("player:")]
        return players
    except Exception as e:
        logging.error(f"Fehler beim Lesen der Spieler aus der Rundendatei: {e}")
        return []

# Anzeigen der Bingokarten
def display_bingo_cards(cards, player_name, game_won_event, game_aborted_event, all_player_queues, roundfile):
    log_file = create_log_file(player_name)
    log_message(log_file, "Start des Spiels")
    log_message(log_file, f"Größe des Spielfelds: {len(cards[0])}x{len(cards)}")
    
    players = read_players_from_roundfile(roundfile)
    
    try:
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)

        curses.start_color()
        curses.init_pair(1, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        col_width = 15
        cursor_idx = (0, 0)
        selected_indices = {(len(cards) // 2, len(cards[0]) // 2)} if len(cards) % 2 != 0 else set()

        flicker = False

        def toggle_flicker():
            nonlocal flicker
            flicker = not flicker

        while not game_won_event.is_set() and not game_aborted_event.is_set():
            stdscr.clear()
            stdscr.addstr("Spieler im Spiel:\n", curses.A_BOLD)
            for player in players:
                stdscr.addstr(f"{player}\n")
            stdscr.addstr("\n")

            for row in range(len(cards)):
                for col in range(len(cards[0])):
                    word = cards[row][col]
                    word_to_display = word[:col_width]
                    padding = " " * (col_width - len(word_to_display))
                    if (row, col) == cursor_idx:
                        stdscr.addstr(f"| {word_to_display}{padding} ", curses.color_pair(1))
                    elif (row, col) in selected_indices:
                        stdscr.addstr(f"| {word_to_display}{padding} ", curses.color_pair(2) | curses.A_BOLD)
                    else:
                        stdscr.addstr(f"| {word_to_display}{padding} ")
                stdscr.addstr("|\n")

                if row < len(cards) - 1:
                    stdscr.addstr("+" + ("-" * (col_width + 2) + "+") * len(cards[0]) + "\n")

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
            elif key == 10:  # Enter-Taste zum Auswählen
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
                        logging.debug("Spiel gewonnen, Abbruch der Anzeige.")
                        with open(roundfile, 'a') as f:
                            f.write("finished\n")
                        break
            elif key == 27:  # Esc-Taste
                log_message(log_file, "Abbruch")
                for queue in all_player_queues:
                    send_message(queue, "aborted")
                game_aborted_event.set()
                with open(roundfile, 'a') as f:
                    f.write("finished\n")
                    f.write("Game aborted\n")
                break

        flicker_start_time = time.time()
        while time.time() - flicker_start_time < 3 and not game_aborted_event.is_set():
            stdscr.clear()
            stdscr.addstr("Spieler im Spiel:\n", curses.A_BOLD)
            for player in players:
                stdscr.addstr(f"{player}\n")
            stdscr.addstr("\n")

            for row in range(len(cards)):
                for col in range(len(cards[0])):
                    word = cards[row][col]
                    word_to_display = word[:col_width]
                    padding = " " * (col_width - len(word_to_display))
                    color_pair = 4 if flicker else 5
                    if (row, col) == cursor_idx:
                        stdscr.addstr(f"| {word_to_display}{padding} ", curses.color_pair(color_pair))
                    elif (row, col) in selected_indices:
                        stdscr.addstr(f"| {word_to_display}{padding} ", curses.color_pair(2) | curses.A_BOLD)
                    else:
                        stdscr.addstr(f"| {word_to_display}{padding} ")
                stdscr.addstr("|\n")

                if row < len(cards) - 1:
                    stdscr.addstr("+" + ("-" * (col_width + 2) + "+") * len(cards[0]) + "\n")

            stdscr.refresh()
            time.sleep(0.5)
            toggle_flicker()

    except Exception as e:
        logging.error(f"Fehler beim Anzeigen der Bingokarten: {e}")
    finally:
        curses.echo()
        curses.nocbreak()
        stdscr.keypad(False)
        curses.endwin()
        log_message(log_file, "Ende des Spiels")

# Überprüfen, ob ein Spieler gewonnen hat
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

# Überprüfen des Zugangs zur Runde
def check_access(roundfile, player_name):
    try:
        if not os.path.exists(roundfile):
            print("Spiel nicht gefunden.")
            return False

        with open(roundfile, 'r') as f:
            players = f.readlines()

        if any("finished" in line for line in players):
            print("Spiel ist bereits beendet.")
            return False

        max_players = int([line.split(":")[1].strip() for line in players if line.startswith("Max")][0])
        current_players = sum(1 for line in players if line.startswith("player:"))
        if current_players >= max_players:
            print("Maximale Anzahl an Spielern erreicht.")
            return False
        
        if any(f"player:{player_name}" == line.strip() for line in players):
            return False  # Spielername bereits vergeben

        return True
    except Exception as e:
        logging.error(f"Fehler bei der Überprüfung des Zugangs: {e}")
        return False

# Spieler erstellen
def create_player(roundfile, player_name):
    try:
        with open(roundfile, 'a') as f:
            f.write("player:" + player_name + '\n')
        print("Spieler erfolgreich erstellt.")
    except Exception as e:
        logging.error(f"Fehler beim Erstellen des Spielers: {e}")

# Rundendatei erstellen
def create_round_file(roundfile, height, width, wordfile, max_players):
    try:
        with open(roundfile, 'w') as f:
            f.write(f"Max: {max_players}\n")
            f.write(f"Height: {height}\n")
            f.write(f"Width: {width}\n")
            f.write(f"Wordfile: {wordfile}\n")
        print("Rundendatei erfolgreich erstellt.")
        return True
    except Exception as e:
        logging.error(f"Fehler beim Erstellen der Rundendatei: {e}")
        return False

# Protokolldatei erstellen
def create_log_file(player_name):
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    log_folder = os.path.join(os.getcwd(), 'logfiles')
    os.makedirs(log_folder, exist_ok=True)
    log_filename = f"{current_time}-bingo-{player_name}.txt"
    log_filepath = os.path.join(log_folder, log_filename)
    return log_filepath

# Nachricht in die Protokolldatei schreiben
def log_message(log_filepath, message):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_filepath, 'a') as log_file:
        log_file.write(f"{current_time} {message}\n")

# Benutzerinput erhalten
def get_input(prompt, input_type=str, valid_range=None, valid_options=None):
    while True:
        try:
            user_input = input_type(input(prompt).strip())
            if valid_range and user_input not in valid_range:
                raise ValueError(f"Eingabe muss im Bereich liegen: {valid_range}")
            if valid_options and user_input not in valid_options:
                raise ValueError(f"Eingabe muss eine der folgenden Optionen sein: {valid_options}")
            return user_input
        except ValueError as e:
            print(e)

# Argumente parsen
def parse_arguments():
    parser = argparse.ArgumentParser(description="Multiplayer Bingo Spiel")
    parser.add_argument('action', type=str, choices=['create', 'join'], help='Aktion: Spiel erstellen oder beitreten')
    parser.add_argument('roundfile', type=str, help='Name der Rundendatei')
    parser.add_argument('player_name', type=str, help='Name des Spielers')
    parser.add_argument('-x', '--xaxis', type=int, help='Anzahl der Spalten der Bingokarte (erforderlich zum Erstellen)', required=False)
    parser.add_argument('-y', '--yaxis', type=int, help='Anzahl der Zeilen der Bingokarte (erforderlich zum Erstellen)', required=False)
    parser.add_argument('-w', '--wordfile', type=str, help='Pfad zur Wortdatei (erforderlich zum Erstellen)', required=False)
    parser.add_argument('-m', '--max_players', type=int, help='Maximale Anzahl an Spielern (erforderlich zum Erstellen)', required=False)
    return parser.parse_args()

# Hauptfunktion
def main():
    init_mq_name = "/init_queue"
    init_mq = create_message_queue(init_mq_name, max_message_size=1024)
    global game_won_event
    game_won_event = threading.Event()
    global game_aborted_event
    game_aborted_event = threading.Event()

    args = parse_arguments()

    try:
        print("Willkommen zu Multiplayer Bingo!")

        if args.action == 'create':
            if not all([args.xaxis, args.yaxis, args.wordfile, args.max_players]):
                print("Zum Erstellen eines Spiels sind die Argumente --xaxis, --yaxis, --wordfile und --max_players erforderlich.")
                return

            while True:
                if os.path.exists(args.roundfile):
                    print("Eine Rundendatei mit diesem Namen existiert bereits. Bitte wähle einen anderen Namen.")
                    args.roundfile = get_input("Name der Rundendatei: ")
                else:
                    break

            height = args.yaxis
            width = args.xaxis
            wordfile = args.wordfile
            max_players = args.max_players
            player_name = args.player_name
            roundfile = args.roundfile

            while True:
                while not os.path.exists(wordfile):
                    print(f"Datei nicht gefunden: {wordfile}.")
                    choice = get_input("Möchtest du den Dateipfad erneut eingeben (ja) oder die Standard-Buzzwords-Datei verwenden (nein)? ", str, valid_options={"ja", "nein"})
                    if choice == "ja":
                        wordfile = get_input("Bitte gib den Pfad zu deiner Wortdatei ein: ")
                    else:
                        wordfile = "buzzwords"  # Ersetze dies durch den Pfad zu deiner Standard-Wortdatei
                        break

                with open(wordfile, 'r') as word_file:
                    words = [line.strip() for line in word_file.readlines()]

                if len(words) < height * width:
                    print(f"Nicht genügend Wörter in der Wortdatei.")
                    width = get_input("Anzahl der Spalten der Bingokarte: ", int)
                    height = get_input("Anzahl der Zeilen der Bingokarte: ", int)
                else:
                    break


            if create_round_file(roundfile, height, width, wordfile, max_players):
  
                create_player(roundfile, player_name)
                mq_name = "/mq_" + player_name
                create_message_queue(mq_name)
                print("Warten auf einen anderen Spieler zum Beitreten...")
                start_event = threading.Event()
                wait_thread = threading.Thread(target=wait_for_opponent, args=(mq_name, start_event, init_mq))
                wait_thread.start()
                start_event.wait()
                wait_thread.join()
                print("Ein anderer Spieler ist dem Spiel beigetreten.")
                cards = read_bingo_cards(roundfile)
                if cards:
                    with open(roundfile, 'r') as f:
                        player_queues = [line.split(":")[1].strip() for line in f if line.startswith("player:")]
                    all_player_queues = [create_message_queue(f"/mq_{name}") for name in player_queues]
                    start_message_listener(mq_name, game_won_event, game_aborted_event, all_player_queues, player_queues, create_log_file(player_name))
                    display_bingo_cards(cards, player_name, game_won_event, game_aborted_event, all_player_queues, roundfile)

        elif args.action == 'join':
            roundfile = args.roundfile
            player_name = args.player_name

            while not roundfile or not os.path.exists(roundfile):
                print("Rundendatei nicht gefunden.")
                roundfile = get_input("Bitte gib den Pfad zur Rundendatei ein: ")

            while not check_access(roundfile, player_name):
                print("Spielername bereits vergeben.")
                player_name = get_input("Bitte gib einen anderen Spielernamen ein: ")

            mq_name = "/mq_" + player_name
            create_message_queue(mq_name)
            create_player(roundfile, player_name)
            send_message(posix_ipc.MessageQueue(init_mq_name), 'start')
            with open(roundfile, 'r') as f:
                player_queues = [line.split(":")[1].strip() for line in f if line.startswith("player:")]
            for queue_name in player_queues:
                send_message(create_message_queue(f"/mq_{queue_name}"), f"player joined: {player_name}")
            cards = read_bingo_cards(roundfile)
            if cards:
                all_player_queues = [create_message_queue(f"/mq_{name}") for name in player_queues]
                start_message_listener(mq_name, game_won_event, game_aborted_event, all_player_queues, player_queues, create_log_file(player_name))
                display_bingo_cards(cards, player_name, game_won_event, game_aborted_event, all_player_queues, roundfile)
        else:
            print("Ungültige Aktion.")
            return
    except Exception as e:
        logging.error(f"Fehler in der Hauptfunktion: {e}")
    finally:
        pass

if __name__ == "__main__":
    main()
