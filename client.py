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
        
        # P2P attributes
        self.p2p_connections = {}  # {username: socket}
        self.p2p_server_socket = None
        self.p2p_port = None
        self.p2p_listening = False
        
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
            # Encoder le message JSON en UTF-8
            message_json = json.dumps(message)
            message_bytes = message_json.encode('utf-8')
            
            # Créer l'en-tête de taille (4 octets, int 32 bits, big-endian)
            size_header = struct.pack('>I', len(message_bytes))
            
            # Envoyer l'en-tête puis les données
            self.socket.sendall(size_header + message_bytes)
        except Exception as e:
            print(f"❌ Erreur d'envoi: {e}")
    
    def receive_message(self):
        """Recevoir un message du serveur"""
        try:
            # Lire l'en-tête de taille (4 octets)
            size_header = b''
            while len(size_header) < 4:
                chunk = self.socket.recv(4 - len(size_header))
                if not chunk:
                    return None
                size_header += chunk
            
            # Décoder la taille du message
            message_size = struct.unpack('>I', size_header)[0]
            
            # Lire exactement message_size octets
            message_bytes = b''
            while len(message_bytes) < message_size:
                chunk = self.socket.recv(message_size - len(message_bytes))
                if not chunk:
                    return None
                message_bytes += chunk
            
            # Décoder et parser le JSON
            message_str = message_bytes.decode('utf-8')
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
                
                elif msg_type == "USER_KICKED":
                    username = payload.get("username")
                    print(f"\r\033[K⚠️  {username} a été kické")
                    print(f"[{self.pseudo}] > ", end="", flush=True)
                
                elif msg_type == "KICKED":
                    reason = payload.get("reason", "Vous avez été déconnecté")
                    print(f"\n\n⚠️  {reason}")
                    print("👋 Connexion fermée par le serveur\n")
                    self.listening = False
                    self.running = False
                    break
                
                elif msg_type == "SERVER_BROADCAST":
                    message = payload.get("message", "")
                    timestamp = payload.get("timestamp", "")
                    target = payload.get("target", "")
                    
                    # Afficher le message serveur avec un format spécial
                    print("\n" + "="*60)
                    print("📢 MESSAGE DU SERVEUR 📢")
                    print(f"📅 {timestamp}")
                    print(f"🎯 Destination: {target}")
                    print("-"*60)
                    print(f"💬 {message}")
                    print("="*60 + "\n")
                    
                    if self.current_room:
                        print(f"[{self.pseudo}] > ", end="", flush=True)
                
                elif msg_type == "P2P_CONNECT":
                    peer_username = payload.get("peer_username")
                    peer_ip = payload.get("peer_ip")
                    peer_port = payload.get("peer_port")
                    role = payload.get("role")
                    
                    print(f"\r\033[K🔗 Connexion P2P avec {peer_username}...")
                    
                    # Démarrer la connexion P2P
                    self.initiate_p2p_connection(peer_username, peer_ip, peer_port, role)
                    
                    if self.current_room:
                        print(f"[{self.pseudo}] > ", end="", flush=True)
                
                elif msg_type == "P2P_ERROR":
                    error = payload.get("error")
                    print(f"\r\033[K❌ Erreur P2P: {error}")
                    if self.current_room:
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
    
    def request_p2p(self, target_username):
        """Demander une connexion P2P avec un autre utilisateur"""
        if not self.session_token:
            print("❌ Non connecté!")
            return
        
        print(f"🔗 Demande de connexion P2P avec {target_username}...")
        self.send_message("P2P_REQUEST", {
            "session_token": self.session_token,
            "target_username": target_username
        })
    
    def initiate_p2p_connection(self, peer_username, peer_ip, peer_port, role):
        """Établir une connexion P2P avec un autre client"""
        try:
            if role == "initiator":
                # Le demandeur se connecte au destinataire
                p2p_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                p2p_socket.connect((peer_ip, peer_port))
                self.p2p_connections[peer_username] = p2p_socket
                print(f"✅ Connecté en P2P avec {peer_username}")
                
                # Démarrer l'écoute des messages P2P
                p2p_thread = threading.Thread(
                    target=self.listen_p2p_messages,
                    args=(peer_username, p2p_socket),
                    daemon=True
                )
                p2p_thread.start()
            
            elif role == "receiver":
                # Le destinataire attend la connexion
                print(f"⏳ En attente de connexion P2P de {peer_username}...")
                # Note: Le serveur P2P devrait déjà être en écoute
                # Pour simplifier, on accepte simplement la connexion
        
        except Exception as e:
            print(f"❌ Erreur de connexion P2P: {e}")
    
    def listen_p2p_messages(self, peer_username, p2p_socket):
        """Écouter les messages P2P d'un pair"""
        while self.running:
            try:
                message = self.receive_message_from_socket(p2p_socket)
                if not message:
                    print(f"\r\033[K❌ {peer_username} s'est déconnecté du P2P")
                    break
                
                msg_type = message.get("type")
                payload = message.get("payload", {})
                
                if msg_type == "P2P_MESSAGE":
                    msg_text = payload.get("message")
                    print(f"\r\033[K💬 [P2P] {peer_username}: {msg_text}")
                    if self.current_room:
                        print(f"[{self.pseudo}] > ", end="", flush=True)
                    
            except Exception as e:
                if self.running:
                    print(f"\r\033[K❌ Erreur P2P avec {peer_username}: {e}")
                break
        
        # Nettoyer la connexion
        if peer_username in self.p2p_connections:
            del self.p2p_connections[peer_username]
        try:
            p2p_socket.close()
        except:
            pass
    
    def receive_message_from_socket(self, sock):
        """Recevoir un message d'un socket spécifique"""
        try:
            # Lire l'en-tête de taille (4 octets)
            size_header = b''
            while len(size_header) < 4:
                chunk = sock.recv(4 - len(size_header))
                if not chunk:
                    return None
                size_header += chunk
            
            # Décoder la taille du message
            message_size = struct.unpack('>I', size_header)[0]
            
            # Lire exactement message_size octets
            message_bytes = b''
            while len(message_bytes) < message_size:
                chunk = sock.recv(message_size - len(message_bytes))
                if not chunk:
                    return None
                message_bytes += chunk
            
            # Décoder et parser le JSON
            message_str = message_bytes.decode('utf-8')
            return json.loads(message_str)
        except Exception as e:
            return None
    
    def send_p2p_message(self, peer_username, message):
        """Envoyer un message P2P à un pair"""
        if peer_username not in self.p2p_connections:
            print(f"❌ Pas de connexion P2P avec {peer_username}")
            return
        
        p2p_socket = self.p2p_connections[peer_username]
        
        msg = {
            "type": "P2P_MESSAGE",
            "payload": {
                "message": message
            },
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Encoder le message JSON en UTF-8
            message_json = json.dumps(msg)
            message_bytes = message_json.encode('utf-8')
            
            # Créer l'en-tête de taille (4 octets, int 32 bits, big-endian)
            size_header = struct.pack('>I', len(message_bytes))
            
            # Envoyer l'en-tête puis les données
            p2p_socket.sendall(size_header + message_bytes)
            print(f"✅ Message P2P envoyé à {peer_username}")
        except Exception as e:
            print(f"❌ Erreur d'envoi P2P: {e}")
    
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
                
                # Commandes spéciales
                if message.strip().startswith('/p2p '):
                    # /p2p username : demander connexion P2P
                    target = message.strip()[5:].strip()
                    if target:
                        self.request_p2p(target)
                    continue
                
                if message.strip().startswith('/msg '):
                    # /msg username message : envoyer message P2P
                    parts = message.strip()[5:].split(' ', 1)
                    if len(parts) == 2:
                        target, msg = parts
                        self.send_p2p_message(target, msg)
                    else:
                        print("❌ Usage: /msg username message")
                    continue
                
                if message.strip().lower() == '/help':
                    print("\n📋 Commandes disponibles:")
                    print("  /p2p username    - Demander connexion P2P")
                    print("  /msg username text - Envoyer message P2P")
                    print("  quit             - Quitter la room\n")
                    continue
                
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
        print("6. 🔄 Synchroniser la room")
        print("7. 🚪 Déconnexion")
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
    
    def sync_room(self):
        """Synchroniser la room - Démonstration d'une action avec séquence d'états"""
        if not self.session_token or not self.current_room:
            print("❌ Non connecté à une room!")
            return
        
        print(f"\n🔄 Synchronisation de #{self.current_room_name}...")
        print("Cette action passe par plusieurs états intermédiaires:\n")
        
        # Envoyer la requête de synchronisation
        self.send_message("SYNC_ROOM", {
            "session_token": self.session_token
        })
        
        # Recevoir et traiter les états de la séquence
        state_count = 0
        while state_count < 4:  # 4 états attendus
            response = self.receive_message()
            if not response:
                print("❌ Erreur: Pas de réponse du serveur")
                break
            
            msg_type = response.get("type")
            payload = response.get("payload", {})
            state = payload.get("state", "unknown")
            
            if msg_type == "SYNC_PREPARING":
                print(f"📦 ÉTAT 1/4 : {payload.get('message')}")
                print(f"   └─ State: {state}\n")
                state_count += 1
            
            elif msg_type == "SYNC_READY":
                print(f"✅ ÉTAT 2/4 : {payload.get('message')}")
                print(f"   ├─ State: {state}")
                print(f"   ├─ Fichiers: {payload.get('files_count')}")
                print(f"   └─ Membres: {payload.get('members_count')}\n")
                state_count += 1
            
            elif msg_type == "SYNC_DATA":
                print(f"📊 ÉTAT 3/4 : Réception des données")
                print(f"   ├─ State: {state}")
                print(f"   ├─ Room: {payload.get('room_name')}")
                files = payload.get('files', [])
                members = payload.get('members', [])
                total_size = payload.get('total_files_size', 0)
                
                print(f"   ├─ Fichiers synchronisés: {len(files)}")
                print(f"   ├─ Taille totale: {total_size / (1024*1024):.2f} MB")
                print(f"   └─ Membres actifs: {', '.join(members)}\n")
                state_count += 1
            
            elif msg_type == "SYNC_COMPLETE":
                print(f"🎉 ÉTAT 4/4 : {payload.get('message')}")
                print(f"   ├─ State: {state}")
                print(f"   ├─ Fichiers synchronisés: {payload.get('synced_files')}")
                print(f"   └─ Timestamp: {payload.get('timestamp')}\n")
                state_count += 1
                break
            
            elif msg_type == "ERROR":
                print(f"❌ Erreur: {payload.get('error')}")
                break
        
        if state_count == 4:
            print("✅ Séquence de synchronisation complète!")
            print("   Tous les états intermédiaires ont été traversés avec succès.\n")
        
        input("Appuie sur ENTRÉE pour continuer...")
    
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
                self.sync_room()
            elif choice == "7":
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
