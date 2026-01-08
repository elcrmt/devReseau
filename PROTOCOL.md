# Protocole de Communication - Partage de Fichiers (Dropbox Like)

## Vue d'ensemble

Protocole client-serveur pour système de partage de fichiers utilisant TCP et JSON.

## Format des Messages

### Structure de base

Chaque message est composé de deux parties :
1. **En-tête de taille** (4 octets) : Un entier 32 bits (big-endian) indiquant la taille des données JSON qui suivent
2. **Données JSON** : Le contenu du message au format JSON

### Format JSON

Tous les messages suivent le format JSON :

```json
{
    "type": "TYPE_MESSAGE",
    "payload": { ... },
    "timestamp": "ISO-8601"
}
```

**Note**: L'en-tête de taille (4 octets) doit être envoyé AVANT le contenu JSON. Cette taille correspond au nombre d'octets du message JSON encodé en UTF-8.

## Messages Principaux

### Authentification

**REGISTER** (Client → Serveur)
```json
{
    "type": "REGISTER",
    "payload": {
        "username": "string",
        "password": "string",
        "email": "string"
    }
}
```

**LOGIN** (Client → Serveur)
```json
{
    "type": "LOGIN",
    "payload": {
        "username": "string",
        "password": "string"
    }
}
```

**LOGIN_SUCCESS** (Serveur → Client)
```json
{
    "type": "LOGIN_SUCCESS",
    "payload": {
        "session_token": "string",
        "username": "string"
    }
}
```

### Rooms

**LIST_ROOMS** (Client → Serveur)
```json
{
    "type": "LIST_ROOMS",
    "payload": {
        "session_token": "string"
    }
}
```

**ROOMS_LIST** (Serveur → Client)
```json
{
    "type": "ROOMS_LIST",
    "payload": {
        "rooms": [
            {
                "id": "string",
                "name": "string",
                "description": "string",
                "members_count": "integer"
            }
        ]
    }
}
```

**JOIN_ROOM** (Client → Serveur)
```json
{
    "type": "JOIN_ROOM",
    "payload": {
        "session_token": "string",
        "room_id": "string"
    }
}
```

**SEND_MESSAGE** (Client → Serveur)
```json
{
    "type": "SEND_MESSAGE",
    "payload": {
        "session_token": "string",
        "message": "string"
    }
}
```

**MESSAGE** (Serveur → Clients de la room)
```json
{
    "type": "MESSAGE",
    "payload": {
        "username": "string",
        "message": "string",
        "room_id": "string"
    }
}
```

**USER_JOINED** (Serveur → Clients de la room)
```json
{
    "type": "USER_JOINED",
    "payload": {
        "username": "string",
        "room_id": "string"
    }
}
```
*Note: Envoyé à tous les clients déjà connectés dans la room (sauf le nouveau) quand un utilisateur rejoint.*

**USER_LEFT** (Serveur → Clients de la room)
```json
{
    "type": "USER_LEFT",
    "payload": {
        "username": "string",
        "room_id": "string"
    }
}
```
*Note: Envoyé à tous les clients de la room quand un utilisateur quitte.*

**USER_KICKED** (Serveur → Clients de la room)
```json
{
    "type": "USER_KICKED",
    "payload": {
        "username": "string",
        "room_id": "string"
    }
}
```
*Note: Envoyé à tous les clients de la room (sauf celui qui est kické) quand un administrateur déconnecte un utilisateur.*

**KICKED** (Serveur → Client kické)
```json
{
    "type": "KICKED",
    "payload": {
        "reason": "string"
    }
}
```
*Note: Envoyé au client qui vient d'être kické par un administrateur juste avant la fermeture de sa connexion.*

**SERVER_BROADCAST** (Serveur → Client(s))
```json
{
    "type": "SERVER_BROADCAST",
    "payload": {
        "message": "string",
        "timestamp": "string (dd/mm/yyyy HH:MM)",
        "target": "string"
    }
}
```
*Note: Message broadcast envoyé par l'administrateur. Peut être envoyé à tous les clients, une room spécifique, ou en message privé. Le client affiche ce message dans un format spécial pour le distinguer des messages normaux.*

### Communication P2P (Peer-to-Peer)

**P2P_REQUEST** (Client → Serveur)
```json
{
    "type": "P2P_REQUEST",
    "payload": {
        "session_token": "string",
        "target_username": "string"
    }
}
```
*Note: Demande au serveur d'établir une connexion P2P avec un autre client.*

**P2P_CONNECT** (Serveur → Client(s))
```json
{
    "type": "P2P_CONNECT",
    "payload": {
        "peer_username": "string",
        "peer_ip": "string",
        "peer_port": "integer",
        "role": "initiator | receiver"
    }
}
```
*Note: Le serveur envoie les informations de connexion aux deux clients. Le client avec role="initiator" doit se connecter au peer, tandis que le "receiver" attend la connexion.*

**P2P_MESSAGE** (Client A → Client B, direct)
```json
{
    "type": "P2P_MESSAGE",
    "payload": {
        "message": "string"
    }
}
```
*Note: Message envoyé directement entre deux clients sans passer par le serveur. Utilise le même format avec en-tête de taille (4 octets).*

**P2P_ERROR** (Serveur → Client)
```json
{
    "type": "P2P_ERROR",
    "payload": {
        "error": "string"
    }
}
```
*Note: Erreur lors de l'établissement d'une connexion P2P (utilisateur introuvable, etc.).*

### Gestion des Fichiers

**LIST_FILES** (Client → Serveur)
```json
{
    "type": "LIST_FILES",
    "payload": {
        "session_token": "string",
        "path": "string"
    }
}
```

**FILE_LIST** (Serveur → Client)
```json
{
    "type": "FILE_LIST",
    "payload": {
        "files": [
            {
                "name": "string",
                "type": "file | folder",
                "size": "integer",
                "modified": "ISO-8601"
            }
        ]
    }
}
```

**UPLOAD_REQUEST** (Client → Serveur)
```json
{
    "type": "UPLOAD_REQUEST",
    "payload": {
        "session_token": "string",
        "filename": "string",
        "path": "string",
        "size": "integer"
    }
}
```

**UPLOAD_READY** → **UPLOAD_DATA** (binaire) → **UPLOAD_COMPLETE**

**DOWNLOAD_REQUEST** → **DOWNLOAD_READY** → **DOWNLOAD_DATA** (binaire)

**DELETE_FILE** / **CREATE_FOLDER** : même structure avec session_token, filename/folder_name, path

### Messages Génériques

**ERROR** (Serveur → Client)
```json
{
    "type": "ERROR",
    "payload": {
        "error": "string",
        "code": "string"
    }
}
```

## Séquences Principales

### Connexion et Choix de Room
```
Client → REGISTER → Serveur → REGISTER_SUCCESS
Client → LOGIN → Serveur → LOGIN_SUCCESS
Client → LIST_ROOMS → Serveur → ROOMS_LIST
Client → JOIN_ROOM → Serveur → JOIN_SUCCESS
```

### Chat dans une Room
```
Client A → SEND_MESSAGE → Serveur
Serveur → MESSAGE → Tous les clients de la room
```

### Upload de Fichier
```
Client → UPLOAD_REQUEST → Serveur → UPLOAD_READY
Client → UPLOAD_DATA (chunks binaires) → Serveur
Serveur → UPLOAD_COMPLETE → Client
```

## Codes d'Erreur

| Code | Description |
|------|-------------|
| `INVALID_CREDENTIALS` | Login/password incorrect |
| `USERNAME_EXISTS` | Pseudo déjà pris |
| `INVALID_SESSION` | Session invalide/expirée |
| `FILE_NOT_FOUND` | Fichier introuvable |
| `NOT_IN_ROOM` | Pas dans une room |
| `STORAGE_FULL` | Espace insuffisant |

## Contraintes Techniques

- **Format** : JSON + délimiteur `\n`
- **Transfert fichiers** : Chunks de 8 KB
- **Taille max fichier** : 1 GB
- **Sécurité** : SHA256 pour mots de passe, UUID pour tokens
- **Timeout** : 30s connexion, 5min transferts
