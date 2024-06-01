import os
import random

# Funktion zur Erstellung einer Bingokarte
def create_bingo_card(height, width, wordfile):
    with open(wordfile, 'r') as f:
        words = [line.strip() for line in f.readlines()]
    
    if len(words) < height * width:
        print("Nicht genug Wörter im Wortfile.")
        return None
    
    random.shuffle(words)
    card = [words[i:i+width] for i in range(0, height*width, width)]
    
    return card

# Funktion zur Überprüfung, ob beide auf dasselbe Spiel zugreifen können
def check_access(roundfile, player_name):
    if not os.path.exists(roundfile):
        print("Spiel nicht gefunden.")
        return False
    
    with open(roundfile, 'r') as f:
        players = f.readlines()
    
    if player_name + '\n' in players:
        print("Spielername bereits vergeben.")
        return False
    
    return True

# Funktion zum Erstellen eines neuen Spielers
def create_player(roundfile, player_name):
    with open(roundfile, 'a') as f:
        f.write(player_name + '\n')

# Funktion zum Erstellen einer Runden-Datei
def create_round_file(roundfile, height, width, wordfile, max_players):
    card = create_bingo_card(height, width, wordfile)
    if card is None:
        return False
    
    with open(roundfile, 'w') as f:
        f.write(f"{height} {width}\n")
        for row in card:
            f.write(" ".join(row) + '\n')
        f.write(f"{max_players}\n")
    
    return True

# Funktion zum Erstellen eines Spiels
def create_game():
    roundfile = input("Bitte geben Sie den Namen der Runden-Datei ein: ")
    height = int(input("Bitte geben Sie die Höhe der Bingokarten ein: "))
    width = int(input("Bitte geben Sie die Breite der Bingokarten ein: "))
    wordfile = input("Bitte geben Sie den Namen der Word-Datei ein: ")
    max_players = int(input("Bitte geben Sie die maximale Anzahl der Spieler ein: "))
    player_name = input("Bitte geben Sie Ihren Spielernamen ein: ")

    if create_round_file(roundfile, height, width, wordfile, max_players):
        print("Runden-Datei erfolgreich erstellt.")
        create_player(roundfile, player_name)
        print("Spieler erfolgreich erstellt.")
    else:
        print("Fehler beim Erstellen der Runden-Datei.")

# Funktion zum Beitritt zu einem Spiel
def join_game():
    roundfile = input("Bitte geben Sie den Namen der Runden-Datei ein: ")
    player_name = input("Bitte geben Sie Ihren Spielernamen ein: ")

    if not check_access(roundfile, player_name):
        return
    
    create_player(roundfile, player_name)
    print("Spieler erfolgreich erstellt.")

# Hauptfunktion
def main():
    print("Willkommen zum Multiplayer-Bingo!")
    choice = input("Möchten Sie ein Spiel erstellen (1) oder einem Spiel beitreten (2)? ")

    if choice == '1':
        create_game()
    elif choice == '2':
        join_game()
    else:
        print("Ungültige Auswahl.")

if __name__ == "__main__":
    main()
