# chessgame-rawsockets
Chess Game using Raw Socket Programming with Multiple Client Support

---

## ♟️ Python Multiplayer Chess Game (LAN)

This is a **multiplayer chess game** built in Python using the `pygame` and `python-chess` libraries, with support for:

- Two-player LAN gameplay (host vs. client)
- Real-time board updates via UDP sockets
- In-game chat
- Spectator mode

The game features a classic chess UI, move legality enforcement, captured piece display, a game-end screen, and simple text chat.

---

## 🚀 How to Run

Make sure Python is installed and all dependencies are installed:

```bash
pip install pygame python-chess
```

Then, clone the repo and navigate into the directory:

```bash
git clone https://github.com/your-username/python-chess-lan.git
cd python-chess-lan
```

### 🧑‍🤝‍🧑 Game Modes

#### 🏁 Start the Server (White Player)

```bash
python chess.py server
```

- Runs the server and plays as **White**
- Accepts connections from a **Black player** and **any number of spectators**

#### ♞ Connect as Black (Client)

```bash
python chess.py client <server_ip>
```

- Replaces `<server_ip>` with the IP address of the server
- Plays as **Black**

#### 👁 Join as a Spectator

```bash
python chess.py spectator <server_ip>
```

- Views the game and can chat, but cannot make moves

---

## 📡 Networking Details

- Uses **UDP sockets** to send and receive moves and messages
- Server broadcasts board updates to all connected clients
- Designed for local or LAN play (no NAT traversal)

---

## ✅ Features

- Legal move enforcement
- Captured piece tracking
- Game end detection and restart prompt
- Lightweight spectator mode
- Simple real-time chat between all users

---

## 🛠 Requirements

- Python 3.7+
- `pygame`
- `python-chess`

---
