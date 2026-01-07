# Protocole de Communication - Partage de Fichiers (Dropbox Like)

## Vue d'ensemble

Ce protocole définit la communication client-serveur pour un système de partage de fichiers distribué. Il utilise des sockets TCP pour garantir la fiabilité des transferts.

## Architecture

- **Serveur** : Gère les comptes utilisateurs, stocke les fichiers, synchronise les modifications
- **Client** : Interface utilisateur, envoie/reçoit des fichiers, maintient la synchronisation locale

## Format des Messages

Tous les messages suivent le format JSON avec un délimiteur de fin `\n`.

```json
{
    "type": "TYPE_MESSAGE",
    "payload": { ... },
    "timestamp": "ISO-8601"
}
```

## Types de Messages

### 1. Authentification et Connexion

#### 1.1 REGISTER (Client → Serveur)
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

#### 1.2 REGISTER_SUCCESS (Serveur → Client)
```json
{
    "type": "REGISTER_SUCCESS",
    "payload": {
        "user_id": "string",
        "message": "Compte créé avec succès"
    }
}
```

#### 1.3 REGISTER_ERROR (Serveur → Client)
```json
{
    "type": "REGISTER_ERROR",
    "payload": {
        "error": "string",
        "code": "USERNAME_EXISTS | INVALID_DATA"
    }
}
```

#### 1.4 LOGIN (Client → Serveur)
```json
{
    "type": "LOGIN",
    "payload": {
        "username": "string",
        "password": "string"
    }
}
```

#### 1.5 LOGIN_SUCCESS (Serveur → Client)
```json
{
    "type": "LOGIN_SUCCESS",
    "payload": {
        "user_id": "string",
        "session_token": "string",
        "username": "string"
    }
}
```

#### 1.6 LOGIN_ERROR (Serveur → Client)
```json
{
    "type": "LOGIN_ERROR",
    "payload": {
        "error": "string",
        "code": "INVALID_CREDENTIALS | USER_NOT_FOUND"
    }
}
```

#### 1.7 LOGOUT (Client → Serveur)
```json
{
    "type": "LOGOUT",
    "payload": {
        "session_token": "string"
    }
}
```

### 2. Gestion des Fichiers

#### 2.1 LIST_FILES (Client → Serveur)
```json
{
    "type": "LIST_FILES",
    "payload": {
        "session_token": "string",
        "path": "string" // chemin du dossier, "/" pour racine
    }
}
```

#### 2.2 FILE_LIST (Serveur → Client)
```json
{
    "type": "FILE_LIST",
    "payload": {
        "path": "string",
        "files": [
            {
                "name": "string",
                "type": "file | folder",
                "size": "integer", // en octets
                "modified": "ISO-8601",
                "checksum": "string" // hash MD5
            }
        ]
    }
}
```

#### 2.3 UPLOAD_REQUEST (Client → Serveur)
```json
{
    "type": "UPLOAD_REQUEST",
    "payload": {
        "session_token": "string",
        "filename": "string",
        "path": "string",
        "size": "integer",
        "checksum": "string"
    }
}
```

#### 2.4 UPLOAD_READY (Serveur → Client)
```json
{
    "type": "UPLOAD_READY",
    "payload": {
        "upload_id": "string",
        "ready": true
    }
}
```

#### 2.5 UPLOAD_DATA (Client → Serveur)
Envoi en mode binaire après UPLOAD_READY :
- Header : 8 octets pour la taille du chunk
- Data : chunk de données (max 8KB)
- Répéter jusqu'à fin du fichier

#### 2.6 UPLOAD_COMPLETE (Serveur → Client)
```json
{
    "type": "UPLOAD_COMPLETE",
    "payload": {
        "upload_id": "string",
        "filename": "string",
        "success": true,
        "checksum_verified": true
    }
}
```

#### 2.7 UPLOAD_ERROR (Serveur → Client)
```json
{
    "type": "UPLOAD_ERROR",
    "payload": {
        "upload_id": "string",
        "error": "string",
        "code": "CHECKSUM_MISMATCH | STORAGE_FULL | PERMISSION_DENIED"
    }
}
```

#### 2.8 DOWNLOAD_REQUEST (Client → Serveur)
```json
{
    "type": "DOWNLOAD_REQUEST",
    "payload": {
        "session_token": "string",
        "filename": "string",
        "path": "string"
    }
}
```

#### 2.9 DOWNLOAD_READY (Serveur → Client)
```json
{
    "type": "DOWNLOAD_READY",
    "payload": {
        "download_id": "string",
        "filename": "string",
        "size": "integer",
        "checksum": "string"
    }
}
```

#### 2.10 DOWNLOAD_DATA (Serveur → Client)
Envoi en mode binaire :
- Header : 8 octets pour la taille du chunk
- Data : chunk de données (max 8KB)
- Répéter jusqu'à fin du fichier

#### 2.11 DOWNLOAD_COMPLETE (Client → Serveur)
```json
{
    "type": "DOWNLOAD_COMPLETE",
    "payload": {
        "download_id": "string",
        "checksum_verified": true
    }
}
```

#### 2.12 DELETE_FILE (Client → Serveur)
```json
{
    "type": "DELETE_FILE",
    "payload": {
        "session_token": "string",
        "filename": "string",
        "path": "string"
    }
}
```

#### 2.13 DELETE_SUCCESS (Serveur → Client)
```json
{
    "type": "DELETE_SUCCESS",
    "payload": {
        "filename": "string",
        "path": "string"
    }
}
```

#### 2.14 CREATE_FOLDER (Client → Serveur)
```json
{
    "type": "CREATE_FOLDER",
    "payload": {
        "session_token": "string",
        "folder_name": "string",
        "path": "string"
    }
}
```

#### 2.15 FOLDER_CREATED (Serveur → Client)
```json
{
    "type": "FOLDER_CREATED",
    "payload": {
        "folder_name": "string",
        "path": "string"
    }
}
```

### 3. Partage et Permissions

#### 3.1 SHARE_FILE (Client → Serveur)
```json
{
    "type": "SHARE_FILE",
    "payload": {
        "session_token": "string",
        "filename": "string",
        "path": "string",
        "share_with": "string", // username du destinataire
        "permission": "read | write"
    }
}
```

#### 3.2 SHARE_SUCCESS (Serveur → Client)
```json
{
    "type": "SHARE_SUCCESS",
    "payload": {
        "share_id": "string",
        "filename": "string",
        "shared_with": "string"
    }
}
```

#### 3.3 SHARE_NOTIFICATION (Serveur → Client)
```json
{
    "type": "SHARE_NOTIFICATION",
    "payload": {
        "from_user": "string",
        "filename": "string",
        "path": "string",
        "permission": "read | write"
    }
}
```

#### 3.4 LIST_SHARED (Client → Serveur)
```json
{
    "type": "LIST_SHARED",
    "payload": {
        "session_token": "string"
    }
}
```

#### 3.5 SHARED_LIST (Serveur → Client)
```json
{
    "type": "SHARED_LIST",
    "payload": {
        "shared_files": [
            {
                "filename": "string",
                "path": "string",
                "owner": "string",
                "permission": "read | write",
                "shared_date": "ISO-8601"
            }
        ]
    }
}
```

### 4. Synchronisation

#### 4.1 SYNC_REQUEST (Client → Serveur)
```json
{
    "type": "SYNC_REQUEST",
    "payload": {
        "session_token": "string",
        "last_sync": "ISO-8601",
        "local_files": [
            {
                "filename": "string",
                "path": "string",
                "checksum": "string",
                "modified": "ISO-8601"
            }
        ]
    }
}
```

#### 4.2 SYNC_RESPONSE (Serveur → Client)
```json
{
    "type": "SYNC_RESPONSE",
    "payload": {
        "to_download": ["string"], // liste des fichiers à télécharger
        "to_delete": ["string"], // fichiers supprimés sur le serveur
        "conflicts": [
            {
                "filename": "string",
                "server_modified": "ISO-8601",
                "client_modified": "ISO-8601"
            }
        ]
    }
}
```

#### 4.3 FILE_UPDATED (Serveur → Client)
Notification push en temps réel :
```json
{
    "type": "FILE_UPDATED",
    "payload": {
        "filename": "string",
        "path": "string",
        "action": "created | modified | deleted",
        "modified_by": "string"
    }
}
```

### 5. Messages Génériques

#### 5.1 ERROR (Serveur → Client)
```json
{
    "type": "ERROR",
    "payload": {
        "error": "string",
        "code": "string",
        "details": "string"
    }
}
```

#### 5.2 PING (Client ↔ Serveur)
```json
{
    "type": "PING",
    "payload": {}
}
```

#### 5.3 PONG (Client ↔ Serveur)
```json
{
    "type": "PONG",
    "payload": {
        "timestamp": "ISO-8601"
    }
}
```

## Séquences d'Actions

### Séquence 1 : Inscription et Connexion

```
Client                          Serveur
  |                                |
  |-------- REGISTER ------------>|
  |                                | [Créer compte]
  |<----- REGISTER_SUCCESS -------|
  |                                |
  |--------- LOGIN -------------->|
  |                                | [Vérifier credentials]
  |<------ LOGIN_SUCCESS ---------|
  |                                |
  |------- LIST_FILES ----------->|
  |                                | [Récupérer fichiers]
  |<------- FILE_LIST ------------|
  |                                |
```

### Séquence 2 : Upload de Fichier

```
Client                          Serveur
  |                                |
  |------ UPLOAD_REQUEST -------->|
  |                                | [Vérifier espace]
  |<------ UPLOAD_READY ----------|
  |                                |
  |------ UPLOAD_DATA ----------->|
  |------ UPLOAD_DATA ----------->|
  |------ UPLOAD_DATA ----------->|
  |         [chunks...]            |
  |                                | [Vérifier checksum]
  |<---- UPLOAD_COMPLETE ---------|
  |                                |
  |                                | [Notifier autres clients]
  |                                |
```

### Séquence 3 : Téléchargement de Fichier

```
Client                          Serveur
  |                                |
  |----- DOWNLOAD_REQUEST ------->|
  |                                | [Récupérer fichier]
  |<----- DOWNLOAD_READY ---------|
  |                                |
  |<----- DOWNLOAD_DATA ----------|
  |<----- DOWNLOAD_DATA ----------|
  |<----- DOWNLOAD_DATA ----------|
  |         [chunks...]            |
  |                                |
  |---- DOWNLOAD_COMPLETE ------->|
  |                                |
```

### Séquence 4 : Synchronisation

```
Client                          Serveur
  |                                |
  |------ SYNC_REQUEST ---------->|
  |    [Envoie liste locale]       |
  |                                | [Compare avec serveur]
  |<----- SYNC_RESPONSE ----------|
  |    [Reçoit différences]        |
  |                                |
  |----- DOWNLOAD_REQUEST ------->|
  |         [pour chaque]          |
  |<----- DOWNLOAD_DATA ----------|
  |         [fichier]              |
  |                                |
```

### Séquence 5 : Partage de Fichier

```
Client A                    Serveur                    Client B
   |                           |                           |
   |------ SHARE_FILE -------->|                           |
   |                           | [Créer partage]           |
   |<---- SHARE_SUCCESS -------|                           |
   |                           |                           |
   |                           |---- SHARE_NOTIFICATION -->|
   |                           |                           |
   |                           |<---- LIST_SHARED ---------|
   |                           |                           |
   |                           |----- SHARED_LIST -------->|
   |                           |                           |
```

## Gestion des Erreurs

### Codes d'Erreur

| Code | Description |
|------|-------------|
| `INVALID_CREDENTIALS` | Login/password incorrect |
| `USER_NOT_FOUND` | Utilisateur inexistant |
| `USERNAME_EXISTS` | Nom d'utilisateur déjà pris |
| `INVALID_SESSION` | Token de session invalide ou expiré |
| `PERMISSION_DENIED` | Droits insuffisants |
| `FILE_NOT_FOUND` | Fichier introuvable |
| `STORAGE_FULL` | Espace de stockage insuffisant |
| `CHECKSUM_MISMATCH` | Erreur d'intégrité du fichier |
| `INVALID_DATA` | Données mal formées |
| `SERVER_ERROR` | Erreur interne du serveur |
| `NETWORK_ERROR` | Erreur de connexion réseau |

### Stratégies de Récupération

- **Perte de connexion** : Reconnexion automatique avec retry exponentiel (1s, 2s, 4s, 8s...)
- **Checksum invalide** : Réessayer l'upload/download automatiquement (max 3 fois)
- **Session expirée** : Demander à l'utilisateur de se reconnecter
- **Conflit de fichier** : Proposer à l'utilisateur de choisir (garder local / garder serveur / garder les deux)

## Sécurité

### Authentification
- Les mots de passe sont hashés avec bcrypt côté serveur
- Les tokens de session sont générés avec UUID v4
- Expiration des sessions après 24h d'inactivité

### Chiffrement
- Connexion TLS/SSL recommandée pour la production
- Checksums MD5 pour vérifier l'intégrité des fichiers

### Validation
- Taille maximale des fichiers : 1 GB
- Noms de fichiers : caractères alphanumériques + . _ -
- Chemins : validation pour éviter les path traversal attacks

## Limites et Contraintes

- **Taille maximale par fichier** : 1 GB
- **Quota utilisateur** : 10 GB par défaut
- **Taille des chunks** : 8 KB (8192 octets)
- **Timeout de connexion** : 30 secondes
- **Timeout d'upload/download** : 5 minutes
- **Nombre max de connexions simultanées par utilisateur** : 3

## Notes d'Implémentation

### Côté Client
- Maintenir un cache local de la liste des fichiers
- Implémenter un système de queue pour les uploads/downloads multiples
- Gérer les interruptions de transfert avec reprise possible
- Afficher une barre de progression pour les transferts

### Côté Serveur
- Structure de dossiers : `/data/{user_id}/{path}/{filename}`
- Base de données pour stocker les métadonnées (users, files, shares, sessions)
- Thread pool pour gérer les connexions multiples
- Système de logs pour le débogage et l'audit

## Évolutions Futures

- Versioning des fichiers (historique des modifications)
- Compression des fichiers avant transfert
- Support du streaming pour les gros fichiers
- Partage public avec liens temporaires
- Corbeille avec restauration des fichiers supprimés
- Recherche de fichiers par contenu
- Prévisualisation des images et documents
