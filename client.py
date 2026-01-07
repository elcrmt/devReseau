import socket
import json
import threading
import sys
import os
import struct
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
                
                elif msg_type == "FILE_SHARED":
                    filename = payload.get("filename")
                    uploader = payload.get("uploader")
                    size = payload.get("size")
                    size_mb = size / (1024 * 1024)
                    print(f"\r\033[K📎 {uploader} a partagé '{filename}' ({size_mb:.2f} MB)")
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
        print("3. � Fichiers de la room")
        print("4. ⬆️  Partager un fichier dans la room")
        print("5. ⬇️  Télécharger un fichier de la room")
        print("6. 🚪 Déconnexion")
        print("="*50)
    
    def list_room_files(self):
        """Lister les fichiers partagés dans la room"""
        if not self.session_token or not self.current_room:
            print("❌ Non connecté à une room!")
            return
        
        self.send_message("LIST_ROOM_FILES", {
            "session_token": self.session_token
        })
        
        response = self.receive_message()
        if response and response["type"] == "ROOM_FILES_LIST":
            files = response['payload']['files']
            if not files:
                print(f"\n📁 Aucun fichier dans #{self.current_room_name}")
            else:
                print(f"\n📁 Fichiers partagés dans #{self.current_room_name}:")
                print("-" * 70)
                for file in files:
                    size_mb = file['size'] / (1024 * 1024)
                    print(f"📄 {file['filename']:30} | {size_mb:>6.2f} MB | par {file['uploader']}")
                print("-" * 70)
    
    def upload_file(self):
        """Uploader un fichier dans la room"""
        if not self.session_token or not self.current_room:
            print("❌ Non connecté à une room!")
            return
        
        file_path = input("\n📁 Chemin du fichier à partager: ").strip()
        
        if not os.path.exists(file_path):
            print("❌ Fichier introuvable!")
            return
        
        if not os.path.isfile(file_path):
            print("❌ Ce n'est pas un fichier!")
            return
        
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        if file_size > 100 * 1024 * 1024:
            print("❌ Fichier trop volumineux! (max 100 MB)")
            return
        
        size_mb = file_size / (1024 * 1024)
        print(f"\n⏳ Envoi de '{filename}' ({size_mb:.2f} MB)...")
        
        # Envoyer la requête d'upload
        self.send_message("UPLOAD_FILE", {
            "session_token": self.session_token,
            "filename": filename,
            "size": file_size
        })
        
        # Attendre confirmation
        response = self.receive_message()
        if not response or response["type"] != "UPLOAD_READY":
            print("❌ Le serveur n'est pas prêt à recevoir")
            return
        
        # Envoyer le fichier par chunks
        try:
            with open(file_path, 'rb') as f:
                sent = 0
                while sent < file_size:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    
                    # Envoyer la taille du chunk (8 octets)
                    chunk_size = struct.pack('!Q', len(chunk))
                    self.socket.sendall(chunk_size)
                    
                    # Envoyer le chunk
                    self.socket.sendall(chunk)
                    sent += len(chunk)
                    
                    # Afficher progression
                    progress = (sent / file_size) * 100
                    print(f"\r⏳ Progression: {progress:.1f}%", end="", flush=True)
            
            print("\n⏳ Attente de confirmation...")
            
            # Attendre confirmation finale
            response = self.receive_message()
            if response and response["type"] == "UPLOAD_COMPLETE":
                print(f"✅ Fichier '{filename}' partagé dans la room!")
            else:
                print("❌ Erreur lors de l'upload")
        
        except Exception as e:
            print(f"\n❌ Erreur d'upload: {e}")
    
    def download_file(self):
        """Télécharger un fichier de la room"""
        if not self.session_token or not self.current_room:
            print("❌ Non connecté à une room!")
            return
        
        filename = input("\n📥 Nom du fichier à télécharger: ").strip()
        
        if not filename:
            print("❌ Nom de fichier invalide!")
            return
        
        print(f"\n⏳ Téléchargement de '{filename}'...")
        
        # Envoyer la requête de download
        self.send_message("DOWNLOAD_FILE", {
            "session_token": self.session_token,
            "filename": filename
        })
        
        # Attendre confirmation
        response = self.receive_message()
        if not response or response["type"] != "DOWNLOAD_READY":
            if response and response["type"] == "ERROR":
                print(f"❌ Erreur: {response['payload']['error']}")
            else:
                print("❌ Fichier introuvable")
            return
        
        file_size = response['payload']['size']
        download_path = f"downloads_{filename}"
        
        # Créer le dossier downloads s'il n'existe pas
        os.makedirs("downloads", exist_ok=True)
        download_path = os.path.join("downloads", filename)
        
        # Recevoir le fichier par chunks
        try:
            received = 0
            with open(download_path, 'wb') as f:
                while received < file_size:
                    # Lire la taille du chunk (8 octets)
                    chunk_size_data = self.socket.recv(8)
                    if not chunk_size_data or len(chunk_size_data) < 8:
                        break
                    
                    chunk_size = struct.unpack('!Q', chunk_size_data)[0]
                    
                    # Lire le chunk
                    chunk_data = b''
                    while len(chunk_data) < chunk_size:
                        remaining = chunk_size - len(chunk_data)
                        data = self.socket.recv(min(8192, remaining))
                        if not data:
                            break
                        chunk_data += data
                    
                    f.write(chunk_data)
                    received += len(chunk_data)
                    
                    # Afficher progression
                    progress = (received / file_size) * 100
                    print(f"\r⏳ Progression: {progress:.1f}%", end="", flush=True)
            
            if received == file_size:
                print(f"\n✅ Fichier téléchargé: {download_path}")
            else:
                print(f"\n❌ Téléchargement incomplet ({received}/{file_size} octets)")
                os.remove(download_path)
        
        except Exception as e:
            print(f"\n❌ Erreur de téléchargement: {e}")
            if os.path.exists(download_path):
                os.remove(download_path)
    
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
                self.list_room_files()
            elif choice == "4":
                self.upload_file()
            elif choice == "5":
                self.download_file()
            elif choice == "6":
                self.send_message("LOGOUT", {"session_token": self.session_token})
                print(f"\n👋 À bientôt {self.pseudo}!")
                self.running = False
            else:
                print("⚠️  Choix invalide!")
        
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
