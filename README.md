# Mesh Client

Client de bureau pour les nœuds [Meshtastic](https://meshtastic.org/), construit avec PySide6 (Qt for Python).

Se connecte à un nœud Meshtastic via TCP (port 4403) et offre une interface graphique complète pour la gestion du réseau mesh.

## Fonctionnalités

- **Messagerie** — Envoi et réception de messages texte sur le réseau mesh, avec sélection de canal
- **Nœuds** — Visualisation des nœuds connectés au réseau (ID, nom, position, batterie, SNR)
- **Carte** — Affichage des nœuds sur une carte
- **Canaux** — Configuration des canaux (nom, clé, paramètres)
- **Radio** — Configuration LoRa (région, bande passante, puissance, etc.)
- **Device** — Configuration de l'appareil (nom, rôle, affichage, Bluetooth, etc.)
- **Modules** — Configuration des modules (MQTT, télémétrie, série, etc.)
- **Contrôle** — Redémarrage, arrêt et réinitialisation d'usine du nœud

## Architecture

```
main.py                     Point d'entrée
mesh/
  connection.py             MeshtasticBridge — pont entre la lib meshtastic et Qt (signaux/slots)
  models.py                 Dataclasses (Message, NodeEntry)
  database.py               SQLite (WAL mode, connexions thread-local)
ui/
  main_window.py            Fenêtre principale (sidebar + pages empilées)
  pages/                    Pages de l'interface (messaging, nodes, channels, …)
  widgets/
    config_form.py          Génération automatique de formulaires Qt depuis les descripteurs protobuf
    status_bar.py           Barre de statut de connexion
```

Le threading repose sur 4 fils d'exécution : le thread principal Qt (GUI), un QThread worker (`MeshtasticBridge`), et les deux threads internes de la bibliothèque meshtastic (`_rxThread`, `publishingThread`). Les callbacks pypubsub émis par meshtastic sont convertis en signaux Qt pour garantir la sécurité inter-threads.

## Prérequis

- Python 3.13+
- Un nœud Meshtastic accessible en TCP (port 4403)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement

```bash
python main.py
```

Aller ensuite dans l'onglet **Connect** pour se connecter au nœud (par défaut `localhost:4403`).
