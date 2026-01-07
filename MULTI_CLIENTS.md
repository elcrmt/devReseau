# Guide de Test Multi-Clients

## Objectif
Démontrer que le serveur peut gérer plusieurs clients connectés simultanément grâce à l'utilisation de threads.

## Architecture Multi-Threading

Le serveur utilise le modèle **un thread par client** :

```
Serveur Principal (Thread Main)
│
├─ Thread Accept Loop
│  └─ socket.accept() → Nouvelle connexion
│     └─ Crée un nouveau thread client
│
├─ Thread Client 1 (handle_client)
│  └─ Gère toutes les communications avec le client 1
│
├─ Thread Client 2 (handle_client)
│  └─ Gère toutes les communications avec le client 2
│
└─ Thread Client N (handle_client)
   └─ Gère toutes les communications avec le client N
```

## Mécanismes Thread-Safe

### Lock pour l'accès concurrent
```python
self.clients_lock = threading.Lock()
```

Utilisé pour protéger l'accès à `self.clients` lors de :
- Ajout d'un client (LOGIN)
- Suppression d'un client (déconnexion)
- Lecture du nombre de clients

### Structures de données partagées
- `self.clients` : dictionnaire des clients connectés
- `self.users` : base des utilisateurs enregistrés
- `self.sessions` : mapping token → username
- `self.rooms` : état des rooms et leurs membres

## Tests

### Test Manuel
1. Lancer le serveur : `python server.py`
2. Ouvrir plusieurs terminaux
3. Dans chaque terminal, lancer : `python client.py`
4. Observer que tous les clients peuvent se connecter simultanément

### Test Automatisé
```bash
python test_multi_clients.py
```

Le script va :
1. Lancer N clients simultanément (par défaut 3)
2. Chaque client va :
   - Se connecter au serveur
   - S'inscrire avec un pseudo unique
   - Se connecter avec ses credentials
   - Rejoindre une room
   - Envoyer des messages
   - Tester le ping/pong
   - Se déconnecter

### Résultat Attendu

Côté serveur, vous devriez voir :
```
✅ Serveur démarré sur 0.0.0.0:5555
⏳ En attente de connexions...
💡 Le serveur utilise un thread par client pour gérer les connexions simultanées

🔌 Nouvelle connexion: ('127.0.0.1', 54321) (Total: 1 client(s))
🔌 Nouvelle connexion: ('127.0.0.1', 54322) (Total: 2 client(s))
🔌 Nouvelle connexion: ('127.0.0.1', 54323) (Total: 3 client(s))

📝 Tentative d'inscription: TestUser1
✅ Inscription réussie: TestUser1 (...)
🔑 Tentative de connexion: TestUser2
✅ Connexion réussie: TestUser2 (Thread: Client-127.0.0.1:54322)
...
```

## Limites

- **Nombre max de threads** : Limité par les ressources système
- **Connexions simultanées** : `socket.listen(5)` permet jusqu'à 5 connexions en attente
- **Scalabilité** : Pour >100 clients, envisager asyncio ou un architecture événementielle

## Avantages du Threading

✅ **Simplicité** : Code facile à comprendre et maintenir
✅ **Isolation** : Chaque client est géré indépendamment
✅ **Blocage** : Les opérations bloquantes d'un client n'affectent pas les autres
✅ **Compatibilité** : Fonctionne sur tous les OS (Windows, Linux, macOS)

## Points d'Attention

⚠️ **Thread-safety** : Toujours utiliser des locks pour accéder aux ressources partagées
⚠️ **Daemon threads** : Les threads clients sont daemon (se terminent avec le serveur)
⚠️ **Gestion des erreurs** : Chaque thread doit gérer ses propres exceptions
