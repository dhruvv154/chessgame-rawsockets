import socket
import pygame
import chess
import sys
import time
import threading

# --- Config ---
PORT = 9999
server_ip = "192.168.0.134"  # Change on client side

# --- Role Selection ---
print("Chess Multiplayer")
print("1. Host Game (White)")
print("2. Join Game (Black)")
print("3. Spectate Game")
choice = input("Choose (1, 2 or 3): ")
is_server = choice.strip() == "1"
is_client = choice.strip() == "2"
is_spectator = choice.strip() == "3"

player_color = None
if is_server:
    player_color = chess.WHITE
elif is_client:
    player_color = chess.BLACK

# --- Networking Setup ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(False)
if is_server:
    sock.bind(("0.0.0.0", PORT))
    print("Waiting for connections...")
    client_addr = None
    spectator_addrs = set()
else:
    server_addr = (server_ip, PORT)
    if is_client:
        sock.sendto(b"hello_client", server_addr)
        print(f"Client connected from {server_addr}")
    else:
        sock.sendto(b"hello_spectator", server_addr)
        print(f"Spectator connected from {server_addr}")

# --- Game State ---
board = chess.Board()
pygame.init()
BOARD_SIZE = 640
CHAT_WIDTH = 300
HEIGHT = BOARD_SIZE
SQUARE_SIZE = BOARD_SIZE // 8
screen = pygame.display.set_mode((BOARD_SIZE + CHAT_WIDTH, HEIGHT))
pygame.display.set_caption("Styled Chess Game")

font = pygame.font.SysFont("calibri", 24)
input_font = pygame.font.SysFont("calibri", 28)
big_font = pygame.font.SysFont("calibri", 60)

chat_log = []
chat_input = ""
chat_scroll = 0
max_chat_lines = 12
is_check = False
game_over = False
winner_text = ""
game_started = False
selected_square = None
legal_moves = []

captured_white = []
captured_black = []
piece_values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9}

white_time = 600
black_time = 600
last_tick = time.time()

resign_rect = pygame.Rect(BOARD_SIZE + 100, HEIGHT - 40, 80, 30)

def format_time(seconds):
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02}:{s:02}"

def get_captured_text(label, captured):
    text = label + ' '.join(captured)
    score = sum(piece_values.get(p.lower(), 0) for p in captured)
    return f"{text} (Total: {score})"

def draw_board():
    for r in range(8):
        for c in range(8):
            row = r if player_color == chess.WHITE or is_spectator else 7 - r
            col = c if player_color == chess.WHITE or is_spectator else 7 - c
            square = chess.square(col, 7 - row)
            color = pygame.Color("white") if (r + c) % 2 == 0 else pygame.Color("gray")
            pygame.draw.rect(screen, color, pygame.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

            if square == selected_square:
                pygame.draw.rect(screen, pygame.Color("blue"), (c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 4)

            if square in legal_moves:
                center = (c * SQUARE_SIZE + SQUARE_SIZE // 2, r * SQUARE_SIZE + SQUARE_SIZE // 2)
                pygame.draw.circle(screen, pygame.Color("green"), center, 10)

            piece = board.piece_at(square)
            if piece:
                symbol = piece.symbol()
                filename = f"{symbol}.png" if symbol.isupper() else f"b{symbol}.png"
                try:
                    img = pygame.image.load(filename)
                    screen.blit(pygame.transform.scale(img, (SQUARE_SIZE, SQUARE_SIZE)), (c * SQUARE_SIZE, r * SQUARE_SIZE))
                except:
                    pass

def draw_chat():
    chat_x = BOARD_SIZE + 10
    chat_y = 10
    pygame.draw.rect(screen, (25, 25, 25), pygame.Rect(BOARD_SIZE, 0, CHAT_WIDTH, HEIGHT))
    visible_lines = chat_log[-max_chat_lines - chat_scroll:-chat_scroll or None]
    for line in visible_lines:
        screen.blit(font.render(line, True, pygame.Color("white")), (chat_x, chat_y))
        chat_y += 22
    input_surf = input_font.render("> " + chat_input, True, pygame.Color("lime"))
    screen.blit(input_surf, (chat_x, HEIGHT // 2 - 30))

def draw_status():
    # Define the rectangle area for the status section
    status_x = BOARD_SIZE
    status_y = HEIGHT // 2
    status_width = CHAT_WIDTH
    status_height = HEIGHT // 2

    # Choose your background color (example: light gray)
    status_bg_color = (101, 67, 33)

    # Draw the rectangle
    pygame.draw.rect(screen, status_bg_color, pygame.Rect(status_x, status_y, status_width, status_height))
    x = BOARD_SIZE + 10
    y = HEIGHT // 2 + 10

    you = captured_white if player_color == chess.BLACK else captured_black
    opponent = captured_black if player_color == chess.BLACK else captured_white
    lines = [
        get_captured_text("You captured: ", you),
        get_captured_text("Opponent captured: ", opponent),
        "",
        f"Your Time: {format_time(white_time if player_color == chess.WHITE else black_time)}",
        f"Opponent Time: {format_time(black_time if player_color == chess.WHITE else white_time)}"
    ]
    for line in lines:
        screen.blit(font.render(line, True, pygame.Color("white")), (x, y))
        y += 24

    if is_check:
        screen.blit(font.render("CHECK!", True, pygame.Color("red")), (x, y))

    pygame.draw.rect(screen, pygame.Color("darkred"), resign_rect, border_radius=5)
    screen.blit(font.render("Resign", True, pygame.Color("white")), (resign_rect.x + 10, resign_rect.y + 5))

def draw_winner():
    overlay = pygame.Surface((BOARD_SIZE + CHAT_WIDTH, HEIGHT))
    overlay.set_alpha(220)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    screen.blit(big_font.render(winner_text, True, pygame.Color("gold")), (100, HEIGHT // 2 - 40))
    screen.blit(font.render("Press ESC to quit", True, pygame.Color("white")), (200, HEIGHT // 2 + 30))

def square_from_mouse(pos):
    x, y = pos
    if x >= BOARD_SIZE or y >= HEIGHT:
        return None
    col = x // SQUARE_SIZE
    row = 7 - (y // SQUARE_SIZE)
    if player_color == chess.BLACK and not is_spectator:
        col = 7 - col
        row = 7 - row
    return chess.square(col, row)

# --- Networking Threads ---

def server_thread():
    global client_addr, spectator_addrs, game_over, winner_text, game_started, is_check
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            decoded = data.decode()
            if decoded.startswith("hello_client"):
                client_addr = addr
                sock.sendto("WELCOME".encode(), client_addr)
                chat_log.append("A player joined as Black.")
                print(f"Client connected from {client_addr}")
            elif decoded.startswith("hello_spectator"):
                spectator_addrs.add(addr)
                sock.sendto("WELCOME_SPECTATOR".encode(), addr)
                chat_log.append("A spectator joined.")
                print(f"Spectator connected from {spectator_addrs}")
                # Send current board state and chat log
                sock.sendto(f"BOARD:{board.fen()}".encode(), addr)
                for msg in chat_log[-10:]:
                    sock.sendto(f"CHAT:{msg}".encode(), addr)
            elif addr == client_addr:
                if decoded.startswith("MOVE:"):
                    move = chess.Move.from_uci(decoded[5:])
                    if move in board.legal_moves:
                        captured = board.piece_at(move.to_square)
                        if captured:
                            if captured.color == chess.WHITE:
                                captured_white.append(captured.symbol())
                            else:
                                captured_black.append(captured.symbol())
                        board.push(move)
                        is_check = board.is_check()
                        game_started = True

                        # ✅ SEND updated board state to all spectators
                        for saddr in spectator_addrs:
                            sock.sendto(f"BOARD:{board.fen()}".encode(), saddr)

                        # ✅ SEND captured pieces to spectators
                        captured_data = f"CAPTURED:{','.join(captured_white)}|{','.join(captured_black)}"
                        for saddr in spectator_addrs:
                            sock.sendto(captured_data.encode(), saddr)
                        for saddr in spectator_addrs:
                            sock.sendto(f"BOARD:{board.fen()}".encode(), saddr)
                elif decoded.startswith("CHAT:"):
                    chat_log.append("Black: " + decoded[5:])
                    for saddr in spectator_addrs:
                        sock.sendto(f"CHAT:Black: {decoded[5:]}".encode(), saddr)
                elif decoded == "RESIGN":
                    winner_text = "Black resigned. White wins!"
                    game_over = True
                    for saddr in spectator_addrs:
                        sock.sendto(f"GAMEOVER:{winner_text}".encode(), saddr)
            elif addr in spectator_addrs:
                if decoded.startswith("CHAT:"):
                    chat_log.append("Spectator: " + decoded[5:])
                    if client_addr:
                        sock.sendto(f"CHAT:Spectator: {decoded[5:]}".encode(), client_addr)
                    for saddr in spectator_addrs:
                        if saddr != addr:
                            sock.sendto(f"CHAT:Spectator: {decoded[5:]}".encode(), saddr)
        except:
            time.sleep(0.05)

def client_thread():
    global board, is_check, game_started, game_over, winner_text
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            decoded = data.decode()
            if decoded.startswith("MOVE:"):
                move = chess.Move.from_uci(decoded[5:])
                if move in board.legal_moves:
                    captured = board.piece_at(move.to_square)
                    if captured:
                        if captured.color == chess.WHITE:
                            captured_white.append(captured.symbol())
                        else:
                            captured_black.append(captured.symbol())
                    board.push(move)
                    is_check = board.is_check()
                    game_started = True
            elif decoded.startswith("CHAT:"):
                chat_log.append(decoded[5:])
            elif decoded == "RESIGN":
                winner_text = "White resigned. Black wins!"
                game_over = True
        except:
            time.sleep(0.05)

def spectator_thread():
    global board, chat_log, is_check, game_over, winner_text
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            decoded = data.decode()
            if decoded.startswith("BOARD:"):
                fen = decoded[6:]
                board.set_fen(fen)
                is_check = board.is_check()
            elif decoded.startswith("CAPTURED:"):
                parts = decoded[9:].split("|")
                captured_white[:] = parts[0].split(",") if parts[0] else []
                captured_black[:] = parts[1].split(",") if parts[1] else []
            elif decoded.startswith("GAMEOVER:"):
                winner_text = decoded[9:]
                game_over = True
        except:
            time.sleep(0.05)

# --- Start Networking Thread ---
if is_server:
    threading.Thread(target=server_thread, daemon=True).start()
elif is_client:
    threading.Thread(target=client_thread, daemon=True).start()
else:
    threading.Thread(target=spectator_thread, daemon=True).start()

clock = pygame.time.Clock()
running = True

while running:
    now = time.time()
    delta = now - last_tick
    last_tick = now

    if not game_over and game_started and not is_spectator:
        if board.turn == chess.WHITE:
            white_time -= delta
            if white_time <= 0:
                winner_text = "Black wins by timeout!"
                game_over = True
        else:
            black_time -= delta
            if black_time <= 0:
                winner_text = "White wins by timeout!"
                game_over = True

    screen.fill((0, 0, 0))
    draw_board()
    draw_chat()
    draw_status()
    if game_over:
        draw_winner()
    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif game_over and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                chat_input = chat_input[:-1]
            elif event.key == pygame.K_RETURN:
                if chat_input.strip():
                    chat_log.append("You: " + chat_input)
                    if is_server and client_addr:
                        sock.sendto(f"CHAT:{chat_input}".encode(), client_addr)
                        for saddr in getattr(sys.modules[__name__], 'spectator_addrs', []):
                            sock.sendto(f"CHAT:Host: {chat_input}".encode(), saddr)
                    elif is_client:
                        sock.sendto(f"CHAT:{chat_input}".encode(), server_addr)
                    elif is_spectator:
                        sock.sendto(f"CHAT:{chat_input}".encode(), server_addr)
                    chat_input = ""
            elif event.key == pygame.K_UP:
                chat_scroll = min(chat_scroll + 1, len(chat_log))
            elif event.key == pygame.K_DOWN:
                chat_scroll = max(chat_scroll - 1, 0)
            else:
                chat_input += event.unicode

        elif event.type == pygame.MOUSEBUTTONDOWN and not game_over and not is_spectator:
            if resign_rect.collidepoint(event.pos):
                if is_server and client_addr:
                    sock.sendto("RESIGN".encode(), client_addr)
                elif is_client:
                    sock.sendto("RESIGN".encode(), server_addr)
                winner_text = "You resigned. Opponent wins!"
                game_over = True
            elif board.turn == player_color:
                clicked_square = square_from_mouse(event.pos)
                if clicked_square is not None:
                    piece = board.piece_at(clicked_square)
                    if selected_square is None:
                        if piece and piece.color == player_color:
                            selected_square = clicked_square
                            legal_moves = [move.to_square for move in board.legal_moves if move.from_square == selected_square]
                    else:
                        move = chess.Move(selected_square, clicked_square)
                        if move in board.legal_moves:
                            captured = board.piece_at(move.to_square)
                            if captured:
                                if captured.color == chess.WHITE:
                                    captured_white.append(captured.symbol())
                                else:
                                    captured_black.append(captured.symbol())
                            board.push(move)
                            if is_server and client_addr:
                                sock.sendto(f"MOVE:{move.uci()}".encode(), client_addr)
                                for saddr in getattr(sys.modules[__name__], 'spectator_addrs', []):
                                    sock.sendto(f"BOARD:{board.fen()}".encode(), saddr)
                            elif is_client:
                                sock.sendto(f"MOVE:{move.uci()}".encode(), server_addr)
                            is_check = board.is_check()
                            game_started = True
                        selected_square = None
                        legal_moves = []

    if not game_over:
        if board.is_stalemate():
            winner_text = "Draw by stalemate!"
            game_over = True
        elif board.is_checkmate():
            winner_text = ("Black" if board.turn == chess.WHITE else "White") + " wins by checkmate!"
            game_over = True

    clock.tick(30)

pygame.quit()
