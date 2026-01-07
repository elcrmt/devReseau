import socket
import json
import threading
import hashlib
import uuid
from datetime import datetime


class FileShareServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.socket = None
        self.clients = {}  # {socket: {"pseudo": "", "session_token": ""}}
        self.users = {}  # {username: {"password": hash, "email": "", "user_id": ""}}
        self.sessions = {}  # {token: username}
        self.running = False
        
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
            
            while self.running:
                try:
                    client_socket, address = self.socket.accept()
                    print(f"🔌 Nouvelle connexion: {address}")
                    
                    # Créer un thread pour gérer le client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
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
        
        # Enregistrer le client
        self.clients[client_socket] = {
            "pseudo": username,
            "session_token": session_token
        }
        
        self.send_message(client_socket, "LOGIN_SUCCESS", {
            "user_id": self.users[username]["user_id"],
            "session_token": session_token,
            "username": username
        })
        
        print(f"✅ Connexion réussie: {username}")
    
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
            del self.sessions[session_token]
            print(f"🚪 Déconnexion: {username}")
    
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
