import socket
import json
import threading
import hashlib
import uuid
import os
import struct
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
            message_json = json.dumps(message) + "\n"
            client_socket.sendall(message_json.encode('utf-8'))
        except Exception as e:
            print(f"❌ Erreur d'envoi: {e}")
    
    def receive_message(self, client_socket):
        """Recevoir un message d'un client"""
        try:
            buffer = ""
            while True:
                chunk = client_socket.recv(1024).decode('utf-8')
                if not chunk:
                    return None
                buffer += chunk
                if "\n" in buffer:
                    message_str, buffer = buffer.split("\n", 1)
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
            self.clients[client_socket] = {
                "pseudo": username,
                "session_token": session_token
            }
        
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
    
    def handle_client(self, client_socket, address):
        """Gérer un client connecté"""
        try:
            while self.running:
                message = self.receive_message(client_socket)
                
                if not message:
                    break
                
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
                elif message_type == "UPLOAD_FILE":
                    self.handle_upload_file(client_socket, payload)
                elif message_type == "LIST_ROOM_FILES":
                    self.handle_list_room_files(client_socket, payload)
                elif message_type == "DOWNLOAD_FILE":
                    self.handle_download_file(client_socket, payload)
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
    
    def stop(self):
        """Arrêter le serveur"""
        print("\n⏳ Arrêt du serveur...")
        self.running = False
        if self.socket:
            self.socket.close()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════╗
    ║   PARTAGE DE FICHIERS - SERVEUR       ║
    ║   Dropbox Like - Version 0.1          ║
    ╚═══════════════════════════════════════╝
    """)
    
    server = FileShareServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n")
        server.stop()
        print("👋 Serveur arrêté")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
