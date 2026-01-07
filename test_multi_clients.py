"""
Script de test pour vérifier la gestion multi-clients du serveur
Lance plusieurs clients en parallèle pour tester la connexion simultanée
"""

import socket
import json
import threading
import time
from datetime import datetime


class TestClient:
    def __init__(self, client_id, host='localhost', port=5555):
        self.client_id = client_id
        self.host = host
        self.port = port
        self.socket = None
        self.pseudo = f"TestUser{client_id}"
        self.session_token = None
        
    def connect(self):
        """Se connecter au serveur"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"[Client {self.client_id}] ✅ Connecté au serveur")
            return True
        except Exception as e:
            print(f"[Client {self.client_id}] ❌ Erreur: {e}")
            return False
    
    def send_message(self, message_type, payload):
        """Envoyer un message"""
        message = {
            "type": message_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
        try:
            message_json = json.dumps(message) + "\n"
            self.socket.sendall(message_json.encode('utf-8'))
        except Exception as e:
            print(f"[Client {self.client_id}] ❌ Erreur d'envoi: {e}")
    
    def receive_message(self):
        """Recevoir un message"""
        try:
            buffer = ""
            while True:
                chunk = self.socket.recv(1024).decode('utf-8')
                if not chunk:
                    return None
                buffer += chunk
                if "\n" in buffer:
                    message_str, buffer = buffer.split("\n", 1)
                    return json.loads(message_str)
        except Exception as e:
            print(f"[Client {self.client_id}] ❌ Erreur de réception: {e}")
            return None
    
    def register_and_login(self):
        """S'inscrire et se connecter"""
        # Inscription
        print(f"[Client {self.client_id}] 📝 Inscription de {self.pseudo}...")
        self.send_message("REGISTER", {
            "username": self.pseudo,
            "password": "test123",
            "email": f"{self.pseudo}@test.com"
        })
        
        response = self.receive_message()
        if response and response["type"] == "REGISTER_SUCCESS":
            print(f"[Client {self.client_id}] ✅ Inscription réussie")
        else:
            print(f"[Client {self.client_id}] ⚠️ {response.get('payload', {}).get('error', 'Erreur')}")
        
        # Attendre un peu
        time.sleep(0.5)
        
        # Connexion
        print(f"[Client {self.client_id}] 🔑 Connexion de {self.pseudo}...")
        self.send_message("LOGIN", {
            "username": self.pseudo,
            "password": "test123"
        })
        
        response = self.receive_message()
        if response and response["type"] == "LOGIN_SUCCESS":
            self.session_token = response['payload']['session_token']
            print(f"[Client {self.client_id}] ✅ Connecté avec le token {self.session_token[:8]}...")
            return True
        else:
            print(f"[Client {self.client_id}] ❌ Échec de connexion")
            return False
    
    def join_room(self, room_id="general"):
        """Rejoindre une room"""
        print(f"[Client {self.client_id}] 🚪 Rejoindre la room {room_id}...")
        self.send_message("JOIN_ROOM", {
            "session_token": self.session_token,
            "room_id": room_id
        })
        
        response = self.receive_message()
        if response and response["type"] == "JOIN_SUCCESS":
            print(f"[Client {self.client_id}] ✅ Room rejointe: {response['payload']['room_name']}")
            return True
        return False
    
    def send_chat_message(self, message):
        """Envoyer un message dans la room"""
        print(f"[Client {self.client_id}] 💬 Envoi: '{message}'")
        self.send_message("SEND_MESSAGE", {
            "session_token": self.session_token,
            "message": message
        })
    
    def ping(self):
        """Envoyer un ping au serveur"""
        self.send_message("PING", {})
        response = self.receive_message()
        if response and response["type"] == "PONG":
            print(f"[Client {self.client_id}] 🏓 PONG reçu")
            return True
        return False
    
    def disconnect(self):
        """Se déconnecter"""
        if self.session_token:
            self.send_message("LOGOUT", {"session_token": self.session_token})
        if self.socket:
            self.socket.close()
        print(f"[Client {self.client_id}] 👋 Déconnecté")


def test_client(client_id, delay=0):
    """Fonction pour tester un client"""
    time.sleep(delay)  # Délai avant de démarrer
    
    client = TestClient(client_id)
    
    if not client.connect():
        return
    
    if not client.register_and_login():
        return
    
    time.sleep(1)
    
    if not client.join_room("general"):
        return
    
    time.sleep(1)
    
    # Envoyer quelques messages
    client.send_chat_message(f"Hello from client {client_id}!")
    time.sleep(2)
    
    client.send_chat_message(f"Client {client_id} reporting in 🚀")
    time.sleep(2)
    
    # Tester le ping
    client.ping()
    time.sleep(1)
    
    client.disconnect()


def main():
    print("""
    ╔═══════════════════════════════════════════╗
    ║   TEST MULTI-CLIENTS                      ║
    ║   Vérification de la gestion simultanée   ║
    ╚═══════════════════════════════════════════╝
    """)
    
    num_clients = int(input("Nombre de clients à lancer (recommandé: 3-5): ") or "3")
    
    print(f"\n🚀 Lancement de {num_clients} clients simultanés...\n")
    
    threads = []
    for i in range(1, num_clients + 1):
        # Lancer chaque client avec un petit délai échelonné
        thread = threading.Thread(target=test_client, args=(i, i * 0.5))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    # Attendre que tous les threads se terminent
    for thread in threads:
        thread.join()
    
    print("\n✅ Test terminé! Tous les clients ont été gérés simultanément.")
    print("👉 Vérifiez les logs du serveur pour voir la gestion multi-threads en action.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Test interrompu")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
