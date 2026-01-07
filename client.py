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
        self.running = False
        
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
        print("="*50)
        print("1. 📂 Lister mes fichiers")
        print("2. ⬆️  Uploader un fichier")
        print("3. ⬇️  Télécharger un fichier")
        print("4. 🗑️  Supprimer un fichier")
        print("5. 🔄 Synchroniser")
        print("6. 🚪 Déconnexion")
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
        
        # Menu principal
        self.running = True
        while self.running:
            self.show_menu()
            choice = input("\nChoix: ").strip()
            
            if choice == "1":
                self.list_files()
            elif choice == "6":
                self.send_message("LOGOUT", {"session_token": self.session_token})
                print(f"\n👋 À bientôt {self.pseudo}!")
                self.running = False
            else:
                print("⚠️  Fonctionnalité en cours de développement...")
        
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
