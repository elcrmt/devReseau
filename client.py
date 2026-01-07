import socket
import json
import threading
import sys
from datetime import datetime


class FileShareClient:
    def __init__(self, host='localhost', port=5555):
        self.host = host
        self.port = port
        self.socket = None
        self.pseudo = None
        self.session_token = None
        self.current_room = None
        self.current_room_name = None
        self.running = False
        self.listening = False
        
    def connect(self):
        """Se connecter au serveur"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"✅ Connecté au serveur {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return False
    
    def send_message(self, message_type, payload):
        """Envoyer un message au serveur"""
        message = {
            "type": message_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
        try:
            message_json = json.dumps(message) + "\n"
            self.socket.sendall(message_json.encode('utf-8'))
        except Exception as e:
            print(f"❌ Erreur d'envoi: {e}")
    
    def receive_message(self):
        """Recevoir un message du serveur"""
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
            print(f"❌ Erreur de réception: {e}")
            return None
    
    def choose_pseudo(self):
        """Interface de sélection du pseudo"""
        print("\n" + "="*50)
        print("🎯 BIENVENUE SUR LE PARTAGE DE FICHIERS")
        print("="*50)
        
        while True:
            pseudo = input("\n👤 Choisis ton pseudo: ").strip()
            
            if not pseudo:
                print("⚠️  Le pseudo ne peut pas être vide!")
                continue
            
            if len(pseudo) < 3:
                print("⚠️  Le pseudo doit contenir au moins 3 caractères!")
                continue
            
            if len(pseudo) > 20:
                print("⚠️  Le pseudo doit contenir au maximum 20 caractères!")
                continue
            
            if not pseudo.replace("_", "").replace("-", "").isalnum():
                print("⚠️  Le pseudo ne peut contenir que des lettres, chiffres, _ et -")
                continue
            
            self.pseudo = pseudo
            print(f"\n✅ Pseudo défini: {self.pseudo}")
            break
    
    def register(self):
        """S'inscrire avec un pseudo"""
        if not self.pseudo:
            print("❌ Aucun pseudo défini!")
            return False
        
        password = input("🔒 Choisis un mot de passe: ").strip()
        if len(password) < 4:
            print("⚠️  Le mot de passe doit contenir au moins 4 caractères!")
            return False
        
        email = input("📧 Entre ton email: ").strip()
        
        print(f"\n⏳ Inscription en cours pour {self.pseudo}...")
        
        self.send_message("REGISTER", {
            "username": self.pseudo,
            "password": password,
            "email": email
        })
        
        response = self.receive_message()
        if response:
            if response["type"] == "REGISTER_SUCCESS":
                print(f"✅ {response['payload']['message']}")
                return True
            elif response["type"] == "REGISTER_ERROR":
                print(f"❌ Erreur: {response['payload']['error']}")
                return False
        
        return False
    
    def login(self):
        """Se connecter avec le pseudo"""
        if not self.pseudo:
            print("❌ Aucun pseudo défini!")
            return False
        
        password = input("🔒 Entre ton mot de passe: ").strip()
        
        print(f"\n⏳ Connexion en cours pour {self.pseudo}...")
        
        self.send_message("LOGIN", {
            "username": self.pseudo,
            "password": password
        })
        
        response = self.receive_message()
        if response:
            if response["type"] == "LOGIN_SUCCESS":
                self.session_token = response['payload']['session_token']
                print(f"✅ Connecté en tant que {self.pseudo}!")
                return True
            elif response["type"] == "LOGIN_ERROR":
                print(f"❌ Erreur: {response['payload']['error']}")
                return False
        
        return False
    
    def list_rooms(self):
        """Lister les rooms disponibles"""
        if not self.session_token:
            print("❌ Non connecté!")
            return None
        
        self.send_message("LIST_ROOMS", {
            "session_token": self.session_token
        })
        
        response = self.receive_message()
        if response and response["type"] == "ROOMS_LIST":
            return response['payload']['rooms']
        
        return None
    
    def choose_room(self):
        """Interface de sélection de room"""
        print("\n" + "="*50)
        print("🚪 CHOIX DE LA ROOM")
        print("="*50)
        
        rooms = self.list_rooms()
        
        if not rooms:
            print("❌ Aucune room disponible")
            return False
        
        print("\n📋 Rooms disponibles:\n")
        for i, room in enumerate(rooms, 1):
            print(f"{i}. 💬 {room['name']:15} - {room['description']}")
            print(f"   👥 {room['members_count']} membre(s) connecté(s)\n")
        
        while True:
            choice = input("👉 Choisis une room (numéro): ").strip()
            
            if not choice.isdigit():
                print("⚠️  Entre un numéro valide!")
                continue
            
            choice_num = int(choice)
            if choice_num < 1 or choice_num > len(rooms):
                print(f"⚠️  Choisis entre 1 et {len(rooms)}!")
                continue
            
            selected_room = rooms[choice_num - 1]
            return self.join_room(selected_room['id'])
    
    def join_room(self, room_id):
        """Rejoindre une room"""
        if not self.session_token:
            print("❌ Non connecté!")
            return False
        
        print(f"\n⏳ Connexion à la room...")
        
        self.send_message("JOIN_ROOM", {
            "session_token": self.session_token,
            "room_id": room_id
        })
        
        response = self.receive_message()
        if response:
            if response["type"] == "JOIN_SUCCESS":
                self.current_room = response['payload']['room_id']
                self.current_room_name = response['payload']['room_name']
                members = response['payload']['members']
                
                print(f"\n✅ Tu as rejoint #{self.current_room_name}!")
                print(f"👥 Membres: {', '.join(members)}\n")
                print("="*50)
                print("💬 Démarre la conversation! (tape 'quit' pour quitter)")
                print("="*50 + "\n")
                return True
            elif response["type"] == "JOIN_ERROR":
                print(f"❌ Erreur: {response['payload']['error']}")
                return False
        
        return False
    
    def listen_messages(self):
        """Écouter les messages entrants en arrière-plan"""
        while self.listening:
            try:
                response = self.receive_message()
                if not response:
                    break
                
                msg_type = response.get("type")
                payload = response.get("payload", {})
                
                if msg_type == "MESSAGE":
                    username = payload.get("username")
                    message = payload.get("message")
                    print(f"\r\033[K💬 {username}: {message}")
                    print(f"[{self.pseudo}] > ", end="", flush=True)
                
                elif msg_type == "USER_JOINED":
                    username = payload.get("username")
                    print(f"\r\033[K✅ {username} a rejoint la room")
                    print(f"[{self.pseudo}] > ", end="", flush=True)
                
                elif msg_type == "USER_LEFT":
                    username = payload.get("username")
                    print(f"\r\033[K👋 {username} a quitté la room")
                    print(f"[{self.pseudo}] > ", end="", flush=True)
                
            except Exception as e:
                if self.listening:
                    print(f"\n❌ Erreur de réception: {e}")
                break
    
    def send_chat_message(self, message):
        """Envoyer un message dans la room"""
        if not self.session_token or not self.current_room:
            print("❌ Non connecté à une room!")
            return
        
        self.send_message("SEND_MESSAGE", {
            "session_token": self.session_token,
            "message": message
        })
    
    def chat_mode(self):
        """Mode chat interactif"""
        # Démarrer le thread d'écoute
        self.listening = True
        listener_thread = threading.Thread(target=self.listen_messages)
        listener_thread.daemon = True
        listener_thread.start()
        
        # Boucle d'envoi de messages
        while self.running:
            try:
                message = input(f"[{self.pseudo}] > ")
                
                if message.strip().lower() == 'quit':
                    print("\n👋 Retour au menu...")
                    self.listening = False
                    break
                
                if message.strip():
                    self.send_chat_message(message.strip())
            
            except KeyboardInterrupt:
                print("\n\n👋 Retour au menu...")
                self.listening = False
                break
    
    def list_files(self):
        """Lister les fichiers"""
        if not self.session_token:
            print("❌ Non connecté!")
            return
        
        self.send_message("LIST_FILES", {
            "session_token": self.session_token,
            "path": "/"
        })
        
        response = self.receive_message()
        if response and response["type"] == "FILE_LIST":
            files = response['payload']['files']
            if not files:
                print("\n📁 Aucun fichier")
            else:
                print(f"\n📁 Fichiers de {self.pseudo}:")
                print("-" * 50)
                for file in files:
                    icon = "📁" if file['type'] == 'folder' else "📄"
                    size = f"{file['size']} octets" if file['type'] == 'file' else ""
                    print(f"{icon} {file['name']:30} {size}")
    
    def show_menu(self):
        """Afficher le menu principal"""
        print("\n" + "="*50)
        print(f"👤 Connecté: {self.pseudo}")
        if self.current_room:
            print(f"🚪 Room: #{self.current_room_name}")
        print("="*50)
        print("1. 💬 Discuter dans la room")
        print("2. 🚪 Changer de room")
        print("3. 📂 Lister mes fichiers")
        print("4. ⬆️  Uploader un fichier")
        print("5. ⬇️  Télécharger un fichier")
        print("6. 🗑️  Supprimer un fichier")
        print("7. 🔄 Synchroniser")
        print("8. 🚪 Déconnexion")
        print("="*50)
    
    def run(self):
        """Lancer le client"""
        if not self.connect():
            return
        
        # Choix du pseudo
        self.choose_pseudo()
        
        # Menu inscription/connexion
        print("\n" + "="*50)
        print("1. 📝 S'inscrire")
        print("2. 🔑 Se connecter")
        print("="*50)
        
        choice = input("\nChoix: ").strip()
        
        if choice == "1":
            if not self.register():
                self.socket.close()
                return
            # Auto-login après inscription
            print("\n⏳ Connexion automatique...")
            import time
            time.sleep(1)
            
        if not self.session_token:
            if not self.login():
                self.socket.close()
                return
        
        # Choix de la room
        if not self.choose_room():
            self.socket.close()
            return
        
        # Menu principal
        self.running = True
        while self.running:
            self.show_menu()
            choice = input("\nChoix: ").strip()
            
            if choice == "1":
                if self.current_room:
                    self.chat_mode()
                else:
                    print("⚠️  Tu dois rejoindre une room d'abord!")
            elif choice == "2":
                self.choose_room()
            elif choice == "3":
                self.list_files()
            elif choice == "8":
                self.send_message("LOGOUT", {"session_token": self.session_token})
                print(f"\n👋 À bientôt {self.pseudo}!")
                self.running = False
            else:
                print("⚠️  Fonctionnalité en cours de développement...")
        
        self.listening = False
        self.socket.close()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════╗
    ║   PARTAGE DE FICHIERS - CLIENT        ║
    ║   Dropbox Like - Version 0.1          ║
    ╚═══════════════════════════════════════╝
    """)
    
    client = FileShareClient()
    try:
        client.run()
    except KeyboardInterrupt:
        print("\n\n👋 Bye!")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
