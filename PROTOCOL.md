# Protocole de Communication - Partage de Fichiers (Dropbox Like)

## Vue d'ensemble

Protocole client-serveur pour système de partage de fichiers utilisant TCP et JSON.

## Format des Messages

Tous les messages suivent le format JSON avec délimiteur `\n` :

```json
{
    "type": "TYPE_MESSAGE",
    "payload": { ... },
    "timestamp": "ISO-8601"
}
```

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
