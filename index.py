import multiprocessing
import time
import random

# Liste von Buzzwords
buzzwords_list = [
    "Blockchain", "Künstliche Intelligenz", "Big Data", "Internet der Dinge",
    "Disruptiv", "Innovativ", "Agil", "Skalierbar", "Synergie", "Paradigmenwechsel"
]

def main():
    print("Willkommen beim Buzzword-Bingo!")
    num_players = int(input("Geben Sie die Anzahl der Spieler ein: "))
    player_processes = []

    # Benutzereingaben sammeln
    player_inputs = []
    for i in range(num_players):
        player_inputs.append(input(f"Spieler {i+1}, drücken Sie Enter, um das Spiel zu starten..."))

    # Spielerprozesse starten
    for i in range(num_players):
        player_process = multiprocessing.Process(target=player, args=(i+1, player_inputs[i]))
        player_processes.append(player_process)
        player_process.start()

    # Auf Beendigung der Spielerprozesse warten
    for player_process in player_processes:
        player_process.join()

def player(player_num, player_input):
    print(f"Spieler {player_num} ist bereit!")
    print(f"Spieler {player_num} startet das Spiel!")
    time.sleep(1)  # Kurze Pause für den Spielaufbau
    player_buzzwords = generate_player_buzzwords()
    print(f"Spieler {player_num}, hier sind Ihre Buzzwords:")
    print(player_buzzwords)
    # Hier könnten weitere Spielaktionen eingefügt werden, z.B. das Überprüfen der Karten auf gewonnene Muster

def generate_player_buzzwords():
    # Jeder Spieler erhält eine zufällige Auswahl von Buzzwords
    num_buzzwords_per_player = 5
    return random.sample(buzzwords_list, num_buzzwords_per_player)

def spiel_starten():
    print("Das Spiel beginnt!")
    # Hier kannst du die Spiellogik implementieren, um das Buzzword-Bingo-Spiel zu starten

# Beispiel für die Verwendung der Funktionen
if __name__ == "__main__":
    buzzwords = buzzwords_list
    print("Verfügbare Buzzwords:", buzzwords)
    main()
