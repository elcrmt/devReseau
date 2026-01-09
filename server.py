import socket
import json
import threading
import hashlib
import uuid
import os
import struct
import flet as ft
import asyncio
from datetime import datetime


class FileShareServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.socket = None
        self.clients = {}  # {socket: {"pseudo": "", "session_token": "", "room": ""}}
        self.users = {}  # {username: {"password": hash, "email": "", "user_id": ""}}
        self.sessions = {}  # {token: username}
        self.running = False
        self.clients_lock = threading.Lock()  # Lock pour accès thread-safe aux clients
        
        # Stockage des fichiers par room
        self.files_by_room = {}  # {room_id: [{"filename": "", "uploader": "", "size": 0, "path": ""}]}
        self.upload_dir = "uploads"
        
        # Créer le dossier uploads s'il n'existe pas
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
        
        # Rooms en dur
        self.rooms = {
            "general": {
                "name": "Général",
                "description": "Discussions générales et partage de fichiers",
                "members": []
            },
            "projets": {
                "name": "Projets",
                "description": "Espace dédié aux projets collaboratifs",
                "members": []
            },
            "tech": {
                "name": "Tech",
                "description": "Discussions techniques et code",
                "members": []
            },
            "random": {
                "name": "Random",
                "description": "Pour tout le reste!",
                "members": []
            }
        }
        
        # Initialiser la liste de fichiers pour chaque room
        for room_id in self.rooms.keys():
            self.files_by_room[room_id] = []
            room_dir = os.path.join(self.upload_dir, room_id)
            if not os.path.exists(room_dir):
                os.makedirs(room_dir)
        
    def start(self):
        """Démarrer le serveur"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            
            print(f"✅ Serveur démarré sur {self.host}:{self.port}")
            print("⏳ En attente de connexions...\n")
            print("💡 Le serveur utilise un thread par client pour gérer les connexions simultanées\n")
            
            while self.running:
                try:
                    client_socket, address = self.socket.accept()
                    
                    with self.clients_lock:
                        num_clients = len(self.clients)
                    
                    print(f"🔌 Nouvelle connexion: {address} (Total: {num_clients + 1} client(s))")
                    
                    # Créer un thread pour gérer le client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        name=f"Client-{address[0]}:{address[1]}"
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"❌ Erreur d'acceptation: {e}")
        
        except Exception as e:
            print(f"❌ Erreur de démarrage: {e}")
        finally:
            if self.socket:
                self.socket.close()
    
    def send_message(self, client_socket, message_type, payload):
        """Envoyer un message à un client"""
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
            client_socket.sendall(size_header + message_bytes)
        except Exception as e:
            print(f"❌ Erreur d'envoi: {e}")
    
    def receive_message(self, client_socket):
        """Recevoir un message d'un client"""
        try:
            # Lire l'en-tête de taille (4 octets)
            size_header = b''
            while len(size_header) < 4:
                chunk = client_socket.recv(4 - len(size_header))
                if not chunk:
                    return None
                size_header += chunk
            
            # Décoder la taille du message
            message_size = struct.unpack('>I', size_header)[0]
            
            # Lire exactement message_size octets
            message_bytes = b''
            while len(message_bytes) < message_size:
                chunk = client_socket.recv(message_size - len(message_bytes))
                if not chunk:
                    return None
                message_bytes += chunk
            
            # Décoder et parser le JSON
            message_str = message_bytes.decode('utf-8')
            return json.loads(message_str)
        except Exception as e:
            print(f"❌ Erreur de réception: {e}")
            return None
    
    def hash_password(self, password):
        """Hasher un mot de passe"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def handle_register(self, client_socket, payload):
        """Gérer l'inscription d'un utilisateur"""
        username = payload.get("username")
        password = payload.get("password")
        email = payload.get("email")
        
        print(f"📝 Tentative d'inscription: {username}")
        
        # Vérifications
        if not username or not password:
            self.send_message(client_socket, "REGISTER_ERROR", {
                "error": "Nom d'utilisateur et mot de passe requis",
                "code": "INVALID_DATA"
            })
            return
        
        if username in self.users:
            self.send_message(client_socket, "REGISTER_ERROR", {
                "error": "Ce pseudo est déjà pris!",
                "code": "USERNAME_EXISTS"
            })
            print(f"⚠️  Inscription refusée: pseudo {username} déjà existant")
            return
        
        # Créer l'utilisateur
        user_id = str(uuid.uuid4())
        self.users[username] = {
            "password": self.hash_password(password),
            "email": email,
            "user_id": user_id
        }
        
        self.send_message(client_socket, "REGISTER_SUCCESS", {
            "user_id": user_id,
            "message": f"Compte créé avec succès pour {username}!"
        })
        
        print(f"✅ Inscription réussie: {username} ({user_id})")
    
    def handle_login(self, client_socket, payload):
        """Gérer la connexion d'un utilisateur"""
        username = payload.get("username")
        password = payload.get("password")
        
        print(f"🔑 Tentative de connexion: {username}")
        
        # Vérifications
        if username not in self.users:
            self.send_message(client_socket, "LOGIN_ERROR", {
                "error": "Utilisateur introuvable",
                "code": "USER_NOT_FOUND"
            })
            print(f"⚠️  Connexion refusée: utilisateur {username} introuvable")
            return
        
        if self.users[username]["password"] != self.hash_password(password):
            self.send_message(client_socket, "LOGIN_ERROR", {
                "error": "Mot de passe incorrect",
                "code": "INVALID_CREDENTIALS"
            })
            print(f"⚠️  Connexion refusée: mot de passe incorrect pour {username}")
            return
        
        # Créer une session
        session_token = str(uuid.uuid4())
        self.sessions[session_token] = username
        
        # Enregistrer le client de façon thread-safe
        with self.clients_lock:
            existing = self.clients.get(client_socket, {})
            existing["pseudo"] = username
            existing["session_token"] = session_token
            self.clients[client_socket] = existing
        
        self.send_message(client_socket, "LOGIN_SUCCESS", {
            "user_id": self.users[username]["user_id"],
            "session_token": session_token,
            "username": username
        })
        
        print(f"✅ Connexion réussie: {username} (Thread: {threading.current_thread().name})")
    
    def handle_list_files(self, client_socket, payload):
        """Gérer la demande de liste de fichiers"""
        session_token = payload.get("session_token")
        path = payload.get("path", "/")
        
        if session_token not in self.sessions:
            self.send_message(client_socket, "ERROR", {
                "error": "Session invalide",
                "code": "INVALID_SESSION"
            })
            return
        
        username = self.sessions[session_token]
        print(f"📂 {username} demande la liste des fichiers: {path}")
        
        # Pour l'instant, retourner une liste vide (fichiers à implémenter)
        self.send_message(client_socket, "FILE_LIST", {
            "path": path,
            "files": []
        })
    
    def handle_logout(self, client_socket, payload):
        """Gérer la déconnexion"""
        session_token = payload.get("session_token")
        
        if session_token in self.sessions:
            username = self.sessions[session_token]
            
            # Retirer de la room si présent
            if client_socket in self.clients and "room" in self.clients[client_socket]:
                room_id = self.clients[client_socket]["room"]
                if room_id and room_id in self.rooms:
                    if username in self.rooms[room_id]["members"]:
                        self.rooms[room_id]["members"].remove(username)
                        print(f"👋 {username} a quitté la room {room_id}")
            
            del self.sessions[session_token]
            print(f"🚪 Déconnexion: {username}")
    
    def handle_list_rooms(self, client_socket, payload):
        """Gérer la demande de liste des rooms"""
        session_token = payload.get("session_token")
        
        if session_token not in self.sessions:
            self.send_message(client_socket, "ERROR", {
                "error": "Session invalide",
                "code": "INVALID_SESSION"
            })
            return
        
        username = self.sessions[session_token]
        print(f"📋 {username} demande la liste des rooms")
        
        # Formater la liste des rooms
        rooms_list = []
        for room_id, room_data in self.rooms.items():
            rooms_list.append({
                "id": room_id,
                "name": room_data["name"],
                "description": room_data["description"],
                "members_count": len(room_data["members"])
            })
        
        self.send_message(client_socket, "ROOMS_LIST", {
            "rooms": rooms_list
        })
    
    def handle_join_room(self, client_socket, payload):
        """Gérer la demande de rejoindre une room"""
        session_token = payload.get("session_token")
        room_id = payload.get("room_id")
        
        if session_token not in self.sessions:
            self.send_message(client_socket, "ERROR", {
                "error": "Session invalide",
                "code": "INVALID_SESSION"
            })
            return
        
        username = self.sessions[session_token]
        
        if room_id not in self.rooms:
            self.send_message(client_socket, "JOIN_ERROR", {
                "error": "Room introuvable",
                "code": "ROOM_NOT_FOUND"
            })
            return
        
        # Retirer de l'ancienne room si présent
        if client_socket in self.clients and "room" in self.clients[client_socket]:
            old_room = self.clients[client_socket]["room"]
            if old_room and old_room in self.rooms:
                if username in self.rooms[old_room]["members"]:
                    self.rooms[old_room]["members"].remove(username)
        
        # Ajouter à la nouvelle room
        if username not in self.rooms[room_id]["members"]:
            self.rooms[room_id]["members"].append(username)
        
        self.clients[client_socket]["room"] = room_id
        
        self.send_message(client_socket, "JOIN_SUCCESS", {
            "room_id": room_id,
            "room_name": self.rooms[room_id]["name"],
            "members": self.rooms[room_id]["members"]
        })
        
        print(f"🚪 {username} a rejoint la room {room_id}")
        
        # Notifier les autres membres de la room
        self.broadcast_to_room(room_id, "USER_JOINED", {
            "username": username,
            "room_id": room_id
        }, exclude_socket=client_socket)
    
    def handle_send_message(self, client_socket, payload):
        """Gérer l'envoi d'un message dans une room"""
        session_token = payload.get("session_token")
        message_text = payload.get("message")
        
        if session_token not in self.sessions:
            self.send_message(client_socket, "ERROR", {
                "error": "Session invalide",
                "code": "INVALID_SESSION"
            })
            return
        
        username = self.sessions[session_token]
        
        if client_socket not in self.clients or "room" not in self.clients[client_socket]:
            self.send_message(client_socket, "ERROR", {
                "error": "Vous devez rejoindre une room d'abord",
                "code": "NOT_IN_ROOM"
            })
            return
        
        room_id = self.clients[client_socket]["room"]
        
        if not room_id or room_id not in self.rooms:
            self.send_message(client_socket, "ERROR", {
                "error": "Room invalide",
                "code": "INVALID_ROOM"
            })
            return
        
        print(f"💬 [{room_id}] {username}: {message_text}")
        
        # Diffuser le message à tous les membres de la room
        self.broadcast_to_room(room_id, "MESSAGE", {
            "username": username,
            "message": message_text,
            "room_id": room_id,
            "timestamp": datetime.now().isoformat()
        })
    
    def broadcast_to_room(self, room_id, message_type, payload, exclude_socket=None):
        """Envoyer un message à tous les membres d'une room"""
        if room_id not in self.rooms:
            return
        
        members = self.rooms[room_id]["members"]
        
        for client_socket, client_data in self.clients.items():
            if client_data.get("room") == room_id:
                if exclude_socket is None or client_socket != exclude_socket:
                    self.send_message(client_socket, message_type, payload)
    
    def handle_p2p_request(self, client_socket, payload):
        """Gérer une demande de connexion P2P entre deux clients"""
        session_token = payload.get("session_token")
        target_username = payload.get("target_username")
        
        if session_token not in self.sessions:
            self.send_message(client_socket, "ERROR", {
                "error": "Session invalide",
                "code": "INVALID_SESSION"
            })
            return
        
        requester_username = self.sessions[session_token]
        
        # Trouver le socket et l'adresse du demandeur
        requester_address = None
        with self.clients_lock:
            if client_socket in self.clients:
                requester_address = self.clients[client_socket].get("address")
        
        if not requester_address:
            self.send_message(client_socket, "P2P_ERROR", {
                "error": "Impossible de récupérer votre adresse"
            })
            return
        
        # Trouver le socket et l'adresse de la cible
        target_socket = None
        target_address = None
        
        with self.clients_lock:
            for sock, client_info in self.clients.items():
                if client_info.get("pseudo") == target_username:
                    target_socket = sock
                    target_address = client_info.get("address")
                    break
        
        if not target_socket or not target_address:
            self.send_message(client_socket, "P2P_ERROR", {
                "error": f"Utilisateur {target_username} introuvable"
            })
            return
        
        # Envoyer les informations de connexion aux deux clients
        # Au demandeur
        self.send_message(client_socket, "P2P_CONNECT", {
            "peer_username": target_username,
            "peer_ip": target_address[0],
            "peer_port": target_address[1],
            "role": "initiator"
        })
        
        # À la cible
        self.send_message(target_socket, "P2P_CONNECT", {
            "peer_username": requester_username,
            "peer_ip": requester_address[0],
            "peer_port": requester_address[1],
            "role": "receiver"
        })
        
        print(f"🔗 P2P initié entre {requester_username} et {target_username}")
    
    def handle_upload_file(self, client_socket, payload):
        """Gérer l'upload d'un fichier dans la room"""
        session_token = payload.get("session_token")
        filename = payload.get("filename")
        file_size = payload.get("size")
        
        if session_token not in self.sessions:
            self.send_message(client_socket, "ERROR", {
                "error": "Session invalide",
                "code": "INVALID_SESSION"
            })
            return
        
        username = self.sessions[session_token]
        
        if client_socket not in self.clients or "room" not in self.clients[client_socket]:
            self.send_message(client_socket, "ERROR", {
                "error": "Vous devez rejoindre une room d'abord",
                "code": "NOT_IN_ROOM"
            })
            return
        
        room_id = self.clients[client_socket]["room"]
        
        if not room_id or room_id not in self.rooms:
            self.send_message(client_socket, "ERROR", {
                "error": "Room invalide",
                "code": "INVALID_ROOM"
            })
            return
        
        # Vérifier la taille du fichier (max 100 MB)
        if file_size > 100 * 1024 * 1024:
            self.send_message(client_socket, "ERROR", {
                "error": "Fichier trop volumineux (max 100 MB)",
                "code": "FILE_TOO_LARGE"
            })
            return
        
        # Créer un nom de fichier unique
        file_id = str(uuid.uuid4())[:8]
        safe_filename = f"{file_id}_{filename}"
        file_path = os.path.join(self.upload_dir, room_id, safe_filename)
        
        print(f"📤 [{room_id}] {username} upload '{filename}' ({file_size} octets)")
        
        # Signaler que le serveur est prêt à recevoir
        self.send_message(client_socket, "UPLOAD_READY", {
            "upload_id": file_id,
            "ready": True
        })
        
        # Recevoir les données binaires
        try:
            received = 0
            with open(file_path, 'wb') as f:
                while received < file_size:
                    # Lire la taille du chunk (8 octets)
                    chunk_size_data = client_socket.recv(8)
                    if not chunk_size_data or len(chunk_size_data) < 8:
                        break
                    
                    chunk_size = struct.unpack('!Q', chunk_size_data)[0]
                    
                    # Lire le chunk
                    chunk_data = b''
                    while len(chunk_data) < chunk_size:
                        remaining = chunk_size - len(chunk_data)
                        data = client_socket.recv(min(8192, remaining))
                        if not data:
                            break
                        chunk_data += data
                    
                    f.write(chunk_data)
                    received += len(chunk_data)
            
            if received == file_size:
                # Enregistrer les métadonnées
                file_metadata = {
                    "filename": filename,
                    "safe_filename": safe_filename,
                    "uploader": username,
                    "size": file_size,
                    "path": file_path,
                    "upload_date": datetime.now().isoformat()
                }
                self.files_by_room[room_id].append(file_metadata)
                
                # Confirmer l'upload
                self.send_message(client_socket, "UPLOAD_COMPLETE", {
                    "upload_id": file_id,
                    "filename": filename,
                    "success": True
                })
                
                print(f"✅ [{room_id}] Fichier '{filename}' uploadé par {username}")
                
                # Notifier tous les membres de la room
                self.broadcast_to_room(room_id, "FILE_SHARED", {
                    "filename": filename,
                    "uploader": username,
                    "size": file_size,
                    "room_id": room_id,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                os.remove(file_path)
                self.send_message(client_socket, "ERROR", {
                    "error": "Transfert incomplet",
                    "code": "TRANSFER_INCOMPLETE"
                })
        
        except Exception as e:
            print(f"❌ Erreur d'upload: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)
            self.send_message(client_socket, "ERROR", {
                "error": f"Erreur d'upload: {str(e)}",
                "code": "UPLOAD_ERROR"
            })
    
    def handle_list_room_files(self, client_socket, payload):
        """Lister les fichiers de la room actuelle"""
        session_token = payload.get("session_token")
        
        if session_token not in self.sessions:
            self.send_message(client_socket, "ERROR", {
                "error": "Session invalide",
                "code": "INVALID_SESSION"
            })
            return
        
        username = self.sessions[session_token]
        
        if client_socket not in self.clients or "room" not in self.clients[client_socket]:
            self.send_message(client_socket, "ERROR", {
                "error": "Vous devez rejoindre une room d'abord",
                "code": "NOT_IN_ROOM"
            })
            return
        
        room_id = self.clients[client_socket]["room"]
        
        files = self.files_by_room.get(room_id, [])
        
        # Formater les infos des fichiers
        files_info = [
            {
                "filename": f["filename"],
                "uploader": f["uploader"],
                "size": f["size"],
                "upload_date": f["upload_date"]
            }
            for f in files
        ]
        
        self.send_message(client_socket, "ROOM_FILES_LIST", {
            "room_id": room_id,
            "files": files_info
        })
    
    def handle_download_file(self, client_socket, payload):
        """Gérer le téléchargement d'un fichier de la room"""
        session_token = payload.get("session_token")
        filename = payload.get("filename")
        
        if session_token not in self.sessions:
            self.send_message(client_socket, "ERROR", {
                "error": "Session invalide",
                "code": "INVALID_SESSION"
            })
            return
        
        username = self.sessions[session_token]
        
        if client_socket not in self.clients or "room" not in self.clients[client_socket]:
            self.send_message(client_socket, "ERROR", {
                "error": "Vous devez rejoindre une room d'abord",
                "code": "NOT_IN_ROOM"
            })
            return
        
        room_id = self.clients[client_socket]["room"]
        
        # Trouver le fichier
        file_metadata = None
        for f in self.files_by_room.get(room_id, []):
            if f["filename"] == filename:
                file_metadata = f
                break
        
        if not file_metadata:
            self.send_message(client_socket, "ERROR", {
                "error": "Fichier introuvable",
                "code": "FILE_NOT_FOUND"
            })
            return
        
        file_path = file_metadata["path"]
        
        if not os.path.exists(file_path):
            self.send_message(client_socket, "ERROR", {
                "error": "Fichier physique introuvable",
                "code": "FILE_NOT_FOUND"
            })
            return
        
        print(f"📥 [{room_id}] {username} télécharge '{filename}'")
        
        # Signaler que le serveur est prêt à envoyer
        self.send_message(client_socket, "DOWNLOAD_READY", {
            "filename": filename,
            "size": file_metadata["size"]
        })
        
        # Envoyer les données binaires par chunks
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    
                    # Envoyer la taille du chunk (8 octets)
                    chunk_size = struct.pack('!Q', len(chunk))
                    client_socket.sendall(chunk_size)
                    
                    # Envoyer le chunk
                    client_socket.sendall(chunk)
            
            print(f"✅ [{room_id}] Fichier '{filename}' téléchargé par {username}")
        
        except Exception as e:
            print(f"❌ Erreur de download: {e}")
            self.send_message(client_socket, "ERROR", {
                "error": f"Erreur de téléchargement: {str(e)}",
                "code": "DOWNLOAD_ERROR"
            })
    
    def handle_sync_room(self, client_socket, payload):
        """Gérer la synchronisation de la room (action avec séquence d'états)"""
        session_token = payload.get("session_token")
        
        if session_token not in self.sessions:
            self.send_message(client_socket, "ERROR", {
                "error": "Session invalide",
                "code": "INVALID_SESSION"
            })
            return
        
        username = self.sessions[session_token]
        
        if client_socket not in self.clients or "room" not in self.clients[client_socket]:
            self.send_message(client_socket, "ERROR", {
                "error": "Vous devez rejoindre une room d'abord",
                "code": "NOT_IN_ROOM"
            })
            return
        
        room_id = self.clients[client_socket]["room"]
        
        print(f"🔄 [{room_id}] {username} demande une synchronisation")
        
        # ÉTAT 1 : SYNC_PREPARING - Préparation de la synchronisation
        self.send_message(client_socket, "SYNC_PREPARING", {
            "message": "Préparation de la synchronisation...",
            "state": "preparing"
        })
        
        import time
        time.sleep(0.5)  # Simuler un traitement
        
        # ÉTAT 2 : SYNC_READY - Prêt à envoyer les données
        files = self.files_by_room.get(room_id, [])
        members = self.rooms[room_id]["members"]
        
        self.send_message(client_socket, "SYNC_READY", {
            "message": "Données prêtes",
            "state": "ready",
            "files_count": len(files),
            "members_count": len(members)
        })
        
        time.sleep(0.3)
        
        # ÉTAT 3 : SYNC_DATA - Envoi des données de synchronisation
        files_info = [
            {
                "filename": f["filename"],
                "uploader": f["uploader"],
                "size": f["size"],
                "upload_date": f["upload_date"]
            }
            for f in files
        ]
        
        self.send_message(client_socket, "SYNC_DATA", {
            "state": "syncing",
            "room_id": room_id,
            "room_name": self.rooms[room_id]["name"],
            "files": files_info,
            "members": members,
            "total_files_size": sum(f["size"] for f in files)
        })
        
        time.sleep(0.3)
        
        # ÉTAT 4 : SYNC_COMPLETE - Synchronisation terminée
        self.send_message(client_socket, "SYNC_COMPLETE", {
            "message": "Synchronisation terminée avec succès",
            "state": "completed",
            "synced_files": len(files),
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"✅ [{room_id}] Synchronisation complétée pour {username}")
    
    def handle_client(self, client_socket, address):
        """Gérer un client connecté"""
        # Stocker l'adresse du client
        with self.clients_lock:
            self.clients[client_socket] = {
                "address": address,
                "last_message_time": datetime.now()
            }
        
        try:
            while self.running:
                message = self.receive_message(client_socket)
                
                if not message:
                    break
                
                # Mettre à jour le timestamp du dernier message
                with self.clients_lock:
                    if client_socket in self.clients:
                        self.clients[client_socket]["last_message_time"] = datetime.now()
                
                message_type = message.get("type")
                payload = message.get("payload", {})
                
                # Router les messages
                if message_type == "REGISTER":
                    self.handle_register(client_socket, payload)
                elif message_type == "LOGIN":
                    self.handle_login(client_socket, payload)
                elif message_type == "LIST_ROOMS":
                    self.handle_list_rooms(client_socket, payload)
                elif message_type == "JOIN_ROOM":
                    self.handle_join_room(client_socket, payload)
                elif message_type == "SEND_MESSAGE":
                    self.handle_send_message(client_socket, payload)
                elif message_type == "P2P_REQUEST":
                    self.handle_p2p_request(client_socket, payload)
                elif message_type == "UPLOAD_FILE":
                    self.handle_upload_file(client_socket, payload)
                elif message_type == "LIST_ROOM_FILES":
                    self.handle_list_room_files(client_socket, payload)
                elif message_type == "DOWNLOAD_FILE":
                    self.handle_download_file(client_socket, payload)
                elif message_type == "SYNC_ROOM":
                    self.handle_sync_room(client_socket, payload)
                elif message_type == "LIST_FILES":
                    self.handle_list_files(client_socket, payload)
                elif message_type == "LOGOUT":
                    self.handle_logout(client_socket, payload)
                    break
                elif message_type == "PING":
                    self.send_message(client_socket, "PONG", {
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    self.send_message(client_socket, "ERROR", {
                        "error": f"Type de message inconnu: {message_type}",
                        "code": "INVALID_DATA"
                    })
        
        except Exception as e:
            print(f"❌ Erreur avec {address}: {e}")
        
        finally:
            # Nettoyer le client
            if client_socket in self.clients:
                pseudo = self.clients[client_socket].get("pseudo", "Inconnu")
                room_id = self.clients[client_socket].get("room")
                
                # Retirer de la room
                if room_id and room_id in self.rooms:
                    if pseudo in self.rooms[room_id]["members"]:
                        self.rooms[room_id]["members"].remove(pseudo)
                        # Notifier les autres membres
                        self.broadcast_to_room(room_id, "USER_LEFT", {
                            "username": pseudo,
                            "room_id": room_id
                        })
                
                print(f"🔌 Déconnexion: {pseudo} ({address})")
                del self.clients[client_socket]
            
            client_socket.close()
    
    def kick_client(self, client_address):
        """Kicker un client par son adresse (IP, port)"""
        with self.clients_lock:
            for client_socket, client_info in list(self.clients.items()):
                if client_info.get("address") == client_address:
                    pseudo = client_info.get("pseudo", "Inconnu")
                    room_id = client_info.get("room")
                    
                    # Notifier les autres membres de la room
                    if room_id and room_id in self.rooms:
                        if pseudo in self.rooms[room_id]["members"]:
                            self.rooms[room_id]["members"].remove(pseudo)
                            # Envoyer le message USER_KICKED aux autres
                            self.broadcast_to_room(room_id, "USER_KICKED", {
                                "username": pseudo,
                                "room_id": room_id
                            }, exclude_socket=client_socket)
                    
                    # Envoyer un message de kick au client
                    try:
                        self.send_message(client_socket, "KICKED", {
                            "reason": "Vous avez été déconnecté par un administrateur"
                        })
                    except:
                        pass
                    
                    # Fermer la connexion
                    print(f"⚠️  Admin a kické: {pseudo} ({client_address})")
                    del self.clients[client_socket]
                    
                    try:
                        client_socket.close()
                    except:
                        pass
                    
                    return True
        return False
    
    def broadcast_server_message(self, message, target_type="all", target_id=None):
        """
        Envoyer un message broadcast du serveur
        
        Args:
            message (str): Le message à envoyer
            target_type (str): "all", "room", ou "user"
            target_id (str): ID de la room ou adresse du user (si applicable)
        """
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        with self.clients_lock:
            if target_type == "all":
                # Envoyer à tous les clients connectés
                for client_socket in self.clients.keys():
                    try:
                        self.send_message(client_socket, "SERVER_BROADCAST", {
                            "message": message,
                            "timestamp": timestamp,
                            "target": "Tous les clients"
                        })
                    except:
                        pass
                print(f"📢 Broadcast envoyé à tous les clients: {message}")
            
            elif target_type == "room" and target_id:
                # Envoyer à tous les clients d'une room spécifique
                if target_id in self.rooms:
                    room_name = self.rooms[target_id]["name"]
                    for client_socket, client_info in self.clients.items():
                        if client_info.get("room") == target_id:
                            try:
                                self.send_message(client_socket, "SERVER_BROADCAST", {
                                    "message": message,
                                    "timestamp": timestamp,
                                    "target": f"Room {room_name}"
                                })
                            except:
                                pass
                    print(f"📢 Broadcast envoyé à la room {room_name}: {message}")
            
            elif target_type == "user" and target_id:
                # Envoyer à un client spécifique (par adresse)
                for client_socket, client_info in self.clients.items():
                    if client_info.get("address") == target_id:
                        pseudo = client_info.get("pseudo", "Inconnu")
                        try:
                            self.send_message(client_socket, "SERVER_BROADCAST", {
                                "message": message,
                                "timestamp": timestamp,
                                "target": f"Message privé pour {pseudo}"
                            })
                            print(f"📢 Message privé envoyé à {pseudo}: {message}")
                        except:
                            pass
                        break
    
    def stop(self):
        """Arrêter le serveur"""
        print("\n⏳ Arrêt du serveur...")
        self.running = False
        if self.socket:
            self.socket.close()


class AdminDashboard:
    """Dashboard admin pour monitorer le serveur en temps réel"""
    
    def __init__(self, server):
        self.server = server
        self.page = None
        self.clients_table = None
        self.stats_text = None
        self.update_timer = None
    
    def build_ui(self, page: ft.Page):
        """Construire l'interface utilisateur"""
        self.page = page
        page.title = "Admin Dashboard - Serveur de Partage de Fichiers"
        page.theme_mode = ft.ThemeMode.DARK
        page.window.width = 1200
        page.window.height = 700
        page.padding = 20
        
        # Titre
        title = ft.Text(
            "🖥️ Dashboard Administrateur",
            size=32,
            weight=ft.FontWeight.BOLD,
            color="#42A5F5"
        )
        
        # Statistiques générales
        self.stats_text = ft.Text(
            self.get_stats_text(),
            size=16,
            color="#66BB6A"
        )
        
        # En-têtes du tableau
        header_row = ft.DataRow(
            cells=[
                ft.DataCell(ft.Text("Adresse IP", weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text("Port", weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text("Pseudo", weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text("Room", weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text("Dernier Message", weight=ft.FontWeight.BOLD)),
            ]
        )
        
        # Tableau des clients
        self.clients_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Adresse IP", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Port", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Pseudo", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Room", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Dernier Message", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Action", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            border=ft.Border.all(2, "#1976D2"),
            border_radius=10,
            vertical_lines=ft.BorderSide(1, "#1976D2"),
            horizontal_lines=ft.BorderSide(1, "#1976D2"),
        )
        
        # Container scrollable pour le tableau
        table_container = ft.Container(
            content=ft.Column(
                [self.clients_table],
                scroll=ft.ScrollMode.AUTO,
            ),
            height=450,
            border=ft.Border.all(2, "#42A5F5"),
            border_radius=10,
            padding=10,
        )
        
        # Bouton de rafraîchissement manuel
        refresh_button = ft.FilledButton(
            "🔄 Rafraîchir",
            on_click=lambda _: self.update_clients_list(),
        )
        
        # === Section Broadcast ===
        ft.Text("📢 Envoyer un message serveur", size=22, weight=ft.FontWeight.BOLD)
        
        # Champ de texte pour le message
        self.broadcast_message = ft.TextField(
            label="Message à diffuser",
            multiline=True,
            min_lines=2,
            max_lines=3,
            hint_text="Tapez votre message...",
        )
        
        # Sélection de la destination
        self.broadcast_target = ft.Dropdown(
            label="Destination",
            width=200,
            value="all",
            options=[
                ft.dropdown.Option("all", "Tous les clients"),
                ft.dropdown.Option("general", "Room Général"),
                ft.dropdown.Option("projets", "Room Projets"),
                ft.dropdown.Option("tech", "Room Tech"),
                ft.dropdown.Option("random", "Room Random"),
            ],
        )
        
        # Bouton d'envoi
        send_broadcast_button = ft.FilledButton(
            "📢 Envoyer le broadcast",
            on_click=lambda _: self.send_broadcast(),
            bgcolor="#FF9800",
        )
        
        broadcast_section = ft.Container(
            content=ft.Column([
                ft.Text("📢 Envoyer un message serveur", size=20, weight=ft.FontWeight.BOLD),
                self.broadcast_message,
                ft.Row([
                    self.broadcast_target,
                    send_broadcast_button,
                ]),
            ]),
            padding=10,
            border=ft.Border.all(2, "#FF9800"),
            border_radius=10,
        )
        
        # Layout principal
        page.add(
            ft.Column([
                title,
                ft.Divider(height=20, color="#42A5F5"),
                self.stats_text,
                ft.Divider(height=10, color="#1976D2"),
                ft.Text("📊 Clients Connectés", size=22, weight=ft.FontWeight.BOLD),
                table_container,
                ft.Row([refresh_button], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=20, color="#1976D2"),
                broadcast_section,
            ])
        )
        
        # Lancer la mise à jour automatique
        self.start_auto_update()
    
    def get_stats_text(self):
        """Obtenir le texte des statistiques"""
        with self.server.clients_lock:
            num_clients = len(self.server.clients)
        
        num_users = len(self.server.users)
        num_rooms = len(self.server.rooms)
        
        return f"👥 Clients connectés: {num_clients} | 📝 Utilisateurs enregistrés: {num_users} | 🚪 Rooms: {num_rooms}"
    
    def confirm_kick(self, address, pseudo):
        """Afficher une boîte de dialogue de confirmation pour kicker un client"""
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        def kick_user(e):
            # Kicker le client
            success = self.server.kick_client(address)
            if success:
                # Fermer le dialog
                dialog.open = False
                self.page.update()
                # Rafraîchir la liste
                self.update_clients_list()
            else:
                close_dialog(e)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚠️ Confirmation"),
            content=ft.Text(f"Êtes-vous sûr de vouloir kicker {pseudo} ?"),
            actions=[
                ft.TextButton("❌ Annuler", on_click=close_dialog),
                ft.TextButton("✔️ Kicker", on_click=kick_user),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def send_broadcast(self):
        """Envoyer le message broadcast"""
        message = self.broadcast_message.value
        target = self.broadcast_target.value
        
        if not message or not message.strip():
            # Afficher une erreur
            error_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("❌ Erreur"),
                content=ft.Text("Le message ne peut pas être vide!"),
                actions=[
                    ft.TextButton("OK", on_click=lambda e: self.close_dialog()),
                ],
            )
            self.page.dialog = error_dialog
            error_dialog.open = True
            self.page.update()
            return
        
        # Déterminer le type et l'ID de la cible
        if target == "all":
            self.server.broadcast_server_message(message, "all")
        elif target in ["general", "projets", "tech", "random"]:
            self.server.broadcast_server_message(message, "room", target)
        
        # Vider le champ de texte
        self.broadcast_message.value = ""
        self.page.update()
        
        # Afficher une confirmation
        success_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("✅ Envoyé"),
            content=ft.Text("Le message a été diffusé avec succès!"),
            actions=[
                ft.TextButton("OK", on_click=lambda e: self.close_dialog()),
            ],
        )
        self.page.dialog = success_dialog
        success_dialog.open = True
        self.page.update()
    
    def close_dialog(self):
        """Fermer le dialog actuel"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    
    def update_clients_list(self):
        """Mettre à jour la liste des clients"""
        if not self.page or not self.clients_table:
            return
        
        # Récupérer les données des clients de façon thread-safe
        with self.server.clients_lock:
            clients_data = []
            for client_socket, client_info in self.server.clients.items():
                address = client_info.get("address", ("Unknown", 0))
                pseudo = client_info.get("pseudo", "Non authentifié")
                room = client_info.get("room", "Aucune")
                last_msg = client_info.get("last_message_time")
                
                # Formater le dernier message
                if last_msg:
                    elapsed = datetime.now() - last_msg
                    if elapsed.total_seconds() < 60:
                        last_msg_str = f"Il y a {int(elapsed.total_seconds())}s"
                    elif elapsed.total_seconds() < 3600:
                        last_msg_str = f"Il y a {int(elapsed.total_seconds() / 60)}min"
                    else:
                        last_msg_str = last_msg.strftime("%H:%M:%S")
                else:
                    last_msg_str = "Jamais"
                
                # Trouver le nom de la room
                room_name = "Aucune"
                if room and room in self.server.rooms:
                    room_name = self.server.rooms[room]["name"]
                
                clients_data.append({
                    "ip": address[0],
                    "port": str(address[1]),
                    "address": address,  # Garder l'adresse complète pour le kick
                    "pseudo": pseudo,
                    "room": room_name,
                    "last_msg": last_msg_str
                })
        
        # Mettre à jour le tableau
        self.clients_table.rows.clear()
        for client in clients_data:
            icons_mod = getattr(ft, "Icons", None) or getattr(ft, "icons", None)
            kick_icon = None
            if icons_mod is not None:
                kick_icon = (
                    getattr(icons_mod, "CANCEL", None)
                    or getattr(icons_mod, "CLOSE", None)
                    or getattr(icons_mod, "HIGHLIGHT_OFF", None)
                )

            # Créer le bouton kick
            kick_button = ft.IconButton(
                icon=kick_icon,
                icon_color="#F44336",
                tooltip="Kicker ce client",
                on_click=lambda e, addr=client["address"], pseudo=client["pseudo"]: self.confirm_kick(addr, pseudo)
            )
            
            self.clients_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(client["ip"])),
                        ft.DataCell(ft.Text(client["port"])),
                        ft.DataCell(ft.Text(client["pseudo"], color="#4DD0E1")),
                        ft.DataCell(ft.Text(client["room"], color="#FFD54F")),
                        ft.DataCell(ft.Text(client["last_msg"], color="#66BB6A")),
                        ft.DataCell(kick_button),
                    ]
                )
            )
        
        # Mettre à jour les stats
        self.stats_text.value = self.get_stats_text()
        
        # Rafraîchir la page
        try:
            self.page.update()
        except:
            pass
    
    def start_auto_update(self):
        """Démarrer la mise à jour automatique toutes les 2 secondes"""
        async def update_loop():
            while True:
                try:
                    self.update_clients_list()
                except Exception as e:
                    print(f"❌ Dashboard update error: {e}")
                await asyncio.sleep(2)

        self.page.run_task(update_loop)
    
    def run(self):
        """Lancer le dashboard"""
        if hasattr(ft, "run"):
            ft.run(self.build_ui)
        else:
            ft.app(self.build_ui)


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════╗
    ║   PARTAGE DE FICHIERS - SERVEUR       ║
    ║   Dropbox Like - Version 0.1          ║
    ║   Avec Dashboard Admin                ║
    ╚═══════════════════════════════════════╝
    """)
    
    server = FileShareServer()
    
    # Lancer le serveur dans un thread séparé
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    print("✅ Serveur démarré en arrière-plan")
    print("🖥️  Ouverture du dashboard admin...\n")
    
    # Lancer le dashboard admin (interface graphique)
    dashboard = AdminDashboard(server)
    
    try:
        dashboard.run()
    except KeyboardInterrupt:
        print("\n")
        server.stop()
        print("👋 Serveur arrêté")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        server.stop()

