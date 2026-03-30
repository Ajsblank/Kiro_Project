import json
import sqlite3
import uuid
import time
import os
import random
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = 'game.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            game_type TEXT DEFAULT 'rps',
            status TEXT DEFAULT 'waiting',
            players TEXT,
            rounds TEXT,
            choices TEXT,
            created_at INTEGER
        )
    """)
    conn.commit()
    conn.close()

# --- 내부 헬퍼 함수 ---
def fetch_room_dict(conn, room_id):
    row = conn.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()
    if not row: return None
    d = dict(row)
    d['players'] = json.loads(d['players'] or '[]')
    d['rounds'] = json.loads(d['rounds'] or '[]')
    d['choices'] = json.loads(d['choices'] or '{}')
    return d

# --- 게임 로직 ---
def next_pow2(n):
    p = 1
    while p < n: p *= 2
    return p

def build_bracket(players):
    size = next_pow2(len(players))
    shuffled = players[:]
    random.shuffle(shuffled)
    byes = size - len(shuffled)
    slots = []
    bye_positions = set(range(size - byes * 2, size, 2))
    player_idx = 0
    for i in range(0, size, 2):
        if i in bye_positions:
            slots.append(shuffled[player_idx] if player_idx < len(shuffled) else None)
            slots.append(None)
            player_idx += 1
        else:
            slots.append(shuffled[player_idx] if player_idx < len(shuffled) else None)
            player_idx += 1
            slots.append(shuffled[player_idx] if player_idx < len(shuffled) else None)
            player_idx += 1

    rounds = []
    r0 = [{'p1': slots[i], 'p2': slots[i+1], 'winner': None, 'log': []} for i in range(0, size, 2)]
    rounds.append(r0)
    prev = r0
    while len(prev) > 1:
        nxt = [{'p1': None, 'p2': None, 'winner': None, 'log': []} for _ in range(len(prev)//2)]
        rounds.append(nxt)
        prev = nxt

    for mi, m in enumerate(rounds[0]):
        if m['p1'] and not m['p2']:
            m['winner'] = m['p1']
            prop(rounds, 0, mi, m['p1'])
        elif not m['p1'] and m['p2']:
            m['winner'] = m['p2']
            prop(rounds, 0, mi, m['p2'])
    return rounds

def prop(rounds, ri, mi, winner):
    if ri + 1 >= len(rounds): return
    nxt = rounds[ri+1][mi//2]
    if mi % 2 == 0: nxt['p1'] = winner
    else: nxt['p2'] = winner

CHITO_SKILLS = {
  "팔달 치토": [{"name":"팔달 강타","power":30,"cost":25,"range":[[0,1]]},{"name":"팔달 폭풍","power":50,"cost":50,"range":[[-1,0],[1,0],[0,1],[0,-1]]},{"name":"팔달 돌진","power":25,"cost":25,"range":[[-1,1],[0,1],[1,1]]},{"name":"팔달 회전베기","power":25,"cost":35,"range":[[0,1],[1,0]]},{"name":"팔달 찌르기","power":15,"cost":15,"range":[[0,1]]}],
  "다산관 치토": [{"name":"다산 일격","power":50,"cost":50,"range":[[0,1]]},{"name":"다산 지식파동","power":15,"cost":15,"range":[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]},{"name":"다산 직진공격","power":25,"cost":15,"range":[[0,1],[0,2]]},{"name":"다산 견제","power":25,"cost":25,"range":[[0,1]]},{"name":"다산 기본타","power":15,"cost":15,"range":[[0,1]]}],
  "원천 치토": [{"name":"원천 파쇄","power":40,"cost":45,"range":[[0,1],[0,2]]},{"name":"원천 확산","power":25,"cost":30,"range":[[-1,1],[0,1],[1,1]]},{"name":"원천 찌르기","power":15,"cost":25,"range":[[0,1]]},{"name":"원천 반격","power":30,"cost":20,"range":[[0,1],[1,0]]},{"name":"원천 기본타","power":15,"cost":15,"range":[[0,1]]}],
  "율곡 치토": [{"name":"율곡 강습","power":50,"cost":50,"range":[[0,1]]},{"name":"율곡 파동","power":15,"cost":15,"range":[[-1,1],[0,1],[1,1]]},{"name":"율곡 연격","power":25,"cost":35,"range":[[0,1],[0,2]]},{"name":"율곡 견제","power":25,"cost":20,"range":[[0,1]]},{"name":"율곡 기본타","power":15,"cost":15,"range":[[0,1]]}],
  "연암 치토": [{"name":"연암 붕괴","power":40,"cost":50,"range":[[0,1],[0,2]]},{"name":"연암 확산타","power":25,"cost":30,"range":[[-1,1],[0,1],[1,1]]},{"name":"연암 찌르기","power":25,"cost":15,"range":[[0,1]]},{"name":"연암 콤보","power":25,"cost":30,"range":[[0,1],[1,0]]},{"name":"연암 기본타","power":15,"cost":15,"range":[[0,1]]}],
  "성호 치토": [{"name":"성호 강타","power":35,"cost":25,"range":[[0,1]]},{"name":"성호 폭발","power":50,"cost":45,"range":[[-1,1],[0,1],[1,1],[0,2]]},{"name":"성호 견제","power":25,"cost":15,"range":[[0,1]]},{"name":"성호 측면타","power":20,"cost":35,"range":[[-1,0],[1,0]]},{"name":"성호 강화타","power":25,"cost":40,"range":[[0,1],[1,0]]}],
  "용지 치토": [{"name":"용지 돌격","power":40,"cost":50,"range":[[0,1],[0,2]]},{"name":"용지 견제","power":25,"cost":25,"range":[[0,1]]},{"name":"용지 필살","power":60,"cost":50,"range":[[0,1],[0,2],[0,3]]},{"name":"용지 콤보","power":30,"cost":20,"range":[[0,1],[1,0]]},{"name":"용지 기본타","power":25,"cost":15,"range":[[0,1]]}],
  "남제 치토": [{"name":"남제 붕괴","power":60,"cost":70,"range":[[0,1],[0,2]]},{"name":"남제 파동","power":20,"cost":15,"range":[[-1,0],[1,0],[0,1]]},{"name":"남제 확산","power":40,"cost":50,"range":[[-1,1],[0,1],[1,1],[0,2]]},{"name":"남제 견제","power":25,"cost":20,"range":[[0,1]]},{"name":"남제 기본타","power":15,"cost":15,"range":[[0,1]]}]
}

def init_chito_state(p1name, p2name, p1char=None, p2char=None):
    chars = list(CHITO_SKILLS.keys())
    return {
        'p1': {'name': p1name, 'char': p1char or chars[0], 'hp': 100, 'mp': 100, 'x': 2, 'y': 2, 'dir': -1, 'queue': []},
        'p2': {'name': p2name, 'char': p2char or chars[1], 'hp': 100, 'mp': 100, 'x': 1, 'y': 0, 'dir': 1, 'queue': []},
        'turn': 1, 'winner': None, 'log': [], 'phase': 'char_select'
    }

def chito_resolve(gs):
    p1, p2 = gs['p1'], gs['p2']
    log = []
    GW, GH = 4, 3
    def clamp_x(v): return max(0, min(GW-1, v))
    def clamp_y(v): return max(0, min(GH-1, v))
    def in_range(attacker, target, skill_range):
        d = attacker['dir']
        for dx, dy in skill_range:
            if attacker['x']+dx == target['x'] and attacker['y']+dy*d == target['y']:
                return True
        return False
    for p, other in [(p1,p2),(p2,p1)]:
        for card in p['queue']:
            if card['type'] == 'move':
                nx = clamp_x(p['x'] + card['dx'])
                ny = clamp_y(p['y'] + card['dy'] * p['dir'])
                if nx != other['x'] or ny != other['y']:
                    p['x'], p['y'] = nx, ny
                    log.append(f"{p['name']} {card['name']}")
    for p, other in [(p1,p2),(p2,p1)]:
        for card in p['queue']:
            if card['type'] == 'skill':
                if p['mp'] < card['cost']:
                    log.append(f"{p['name']} 기력 부족")
                    continue
                p['mp'] -= card['cost']
                if in_range(p, other, card['range']):
                    other['hp'] = max(0, other['hp'] - card['power'])
                    log.append(f"{p['name']}→{card['name']} {card['power']}데미지!")
                else:
                    log.append(f"{p['name']}→{card['name']} 빗나감")
    for p in [p1, p2]:
        p['mp'] = min(100, p['mp'] + 15)
        p['queue'] = []
    gs['turn'] = gs.get('turn', 1) + 1
    gs['log'] = (log + gs.get('log', []))[:30]
    if p1['hp'] <= 0 and p2['hp'] <= 0: gs['winner'] = 'draw'
    elif p1['hp'] <= 0: gs['winner'] = p2['name']
    elif p2['hp'] <= 0: gs['winner'] = p1['name']
    return gs

def rps_win(a, b):
    if a == b: return None
    wins = [('✊','✌️'),('✌️','🖐️'),('🖐️','✊')]
    return a if (a,b) in wins else b

# --- Flask Routes ---

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/rooms', methods=['GET', 'POST'])
def handle_rooms():
    conn = get_db()
    try:
        if request.method == 'GET':
            rows = conn.execute("SELECT * FROM rooms ORDER BY created_at DESC").fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d['players'] = json.loads(d['players'] or '[]')
                d['rounds'] = json.loads(d['rounds'] or '[]')
                d['choices'] = json.loads(d['choices'] or '{}')
                res.append(d)
            return jsonify(res)
        
        body = request.get_json(silent=True) or {}
        name = body.get('name','').strip()
        game_type = body.get('game_type','rps')
        if not name: return jsonify({'error': '방 이름을 입력하세요'}), 400
        room_id = str(uuid.uuid4())[:8]
        conn.execute(
            "INSERT INTO rooms (room_id,name,game_type,status,players,rounds,choices,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (room_id, name, game_type, 'waiting', '[]', '[]', '{}', int(time.time()))
        )
        conn.commit()
        return jsonify({'room_id': room_id, 'name': name, 'game_type': game_type, 'status': 'waiting', 'players': [], 'rounds': [], 'choices': {}})
    finally:
        conn.close()

@app.route('/rooms/<room_id>', methods=['GET', 'DELETE'])
def handle_room(room_id):
    conn = get_db()
    try:
        if request.method == 'GET':
            d = fetch_room_dict(conn, room_id)
            if not d: return jsonify({'error': '방 없음'}), 404
            return jsonify(d)
        
        # DELETE만 수행
        conn.execute("DELETE FROM rooms WHERE room_id=?", (room_id,))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        conn.close()

@app.route('/rooms/<room_id>/join', methods=['POST'])
def join_room(room_id):
    conn = get_db()
    try:
        body = request.get_json(silent=True) or {}
        player = body.get('player','').strip()
        row = conn.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()
        if not row: return jsonify({'error': '방 없음'}), 404
        players = json.loads(row['players'] or '[]')
        if player in players: return jsonify({'error': '이미 참가함'}), 400
        players.append(player)
        conn.execute("UPDATE rooms SET players=? WHERE room_id=?", (json.dumps(players, ensure_ascii=False), room_id))
        conn.commit()
        # 직접 fetch하여 반환 (handle_room 호출 안함)
        return jsonify(fetch_room_dict(conn, room_id))
    finally:
        conn.close()

@app.route('/rooms/<room_id>/leave', methods=['POST'])
def leave_room(room_id):
    conn = get_db()
    try:
        body = request.get_json(silent=True) or {}
        player = body.get('player','').strip()
        row = conn.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()
        if not row: return jsonify({'error': '방 없음'}), 404
        players = json.loads(row['players'] or '[]')
        players = [p for p in players if p != player]
        conn.execute("UPDATE rooms SET players=? WHERE room_id=?", (json.dumps(players, ensure_ascii=False), room_id))
        conn.commit()
        return jsonify(fetch_room_dict(conn, room_id))
    finally:
        conn.close()

@app.route('/rooms/<room_id>/ready', methods=['POST'])
def ready_room(room_id):
    conn = get_db()
    try:
        body = request.get_json(silent=True) or {}
        player = body.get('player')
        row = conn.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()
        if not row: return jsonify({'error': '방 없음'}), 404
        choices = json.loads(row['choices'] or '{}')
        now = int(time.time())
        if 'ready' not in choices: choices['ready'] = {}
        choices['ready'][player] = now
        players = json.loads(row['players'] or '[]')
        online = [p for p in players if now - choices['ready'].get(p, 0) <= 10]
        choices['online'] = online
        choices['all_ready'] = (set(online) == set(players) and len(players) >= 2)
        conn.execute("UPDATE rooms SET choices=? WHERE room_id=?", (json.dumps(choices, ensure_ascii=False), room_id))
        conn.commit()
        return jsonify(fetch_room_dict(conn, room_id))
    finally:
        conn.close()

@app.route('/rooms/<room_id>/start', methods=['POST'])
def start_room(room_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()
        if not row: return jsonify({'error': '방 없음'}), 404
        players = json.loads(row['players'] or '[]')
        rounds = build_bracket(players)
        game_state = {}
        if row['game_type'] in ['chito', 'test_chito', 'test_rps', 'test']:
            m = rounds[0][0]
            if m['p1'] and m['p2']: game_state = init_chito_state(m['p1'], m['p2'])
        
        # 가위바위보 타입은 game_state를 사용하지 않으므로 초기화하지 않음
        if row['game_type'] in ['rps', 'test_rps']:
            game_state = {}
        conn.execute("UPDATE rooms SET status='playing', rounds=?, choices=? WHERE room_id=?",
                     (json.dumps(rounds, ensure_ascii=False), json.dumps({'game_state': game_state}, ensure_ascii=False), room_id))
        conn.commit()
        return jsonify(fetch_room_dict(conn, room_id))
    finally:
        conn.close()

@app.route('/rooms/<room_id>/forfeit', methods=['POST'])
def forfeit_room(room_id):
    conn = get_db()
    try:
        body = request.get_json(silent=True) or {}
        player = body.get('player')
        row = conn.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()
        if not row: return jsonify({'error': '방 없음'}), 404
        rounds = json.loads(row['rounds'] or '[]')
        choices = json.loads(row['choices'] or '{}')
        for ri, rd in enumerate(rounds):
            for mi, m in enumerate(rd):
                if not m['winner'] and m['p1'] and m['p2'] and (m['p1'] == player or m['p2'] == player):
                    winner = m['p2'] if m['p1'] == player else m['p1']
                    m['winner'] = winner
                    prop(rounds, ri, mi, winner)
                    if 'game_state' in choices: choices['game_state']['winner'] = winner
                    status = 'finished' if rounds[-1][0].get('winner') else row['status']
                    conn.execute("UPDATE rooms SET rounds=?, choices=?, status=? WHERE room_id=?",
                                 (json.dumps(rounds, ensure_ascii=False), json.dumps(choices, ensure_ascii=False), status, room_id))
                    conn.commit()
                    return jsonify(fetch_room_dict(conn, room_id))
        return jsonify({'error': '진행중인 경기 없음'}), 400
    finally:
        conn.close()

@app.route('/rooms/<room_id>/choice', methods=['POST'])
def choice_room(room_id):
    conn = get_db()
    try:
        body = request.get_json(silent=True) or {}
        ri, mi, player, choice = body['round'], body['match'], body['player'], body['choice']
        row = conn.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()
        if not row: return jsonify({'error': '방 없음'}), 404
        rounds = json.loads(row['rounds'] or '[]')
        choices = json.loads(row['choices'] or '{}')
        match = rounds[ri][mi]
        key = f"{ri}_{mi}"
        if key not in choices: choices[key] = {}
        choices[key][player] = choice
        p1, p2 = match['p1'], match['p2']
        if p1 in choices[key] and p2 in choices[key]:
            c1, c2 = choices[key][p1], choices[key][p2]
            win_c = rps_win(c1, c2)
            if win_c is None: choices[key] = {}
            else:
                winner = p1 if win_c == c1 else p2
                match['winner'] = winner
                prop(rounds, ri, mi, winner)
                del choices[key]
        status = 'finished' if rounds[-1][0].get('winner') else row['status']
        conn.execute("UPDATE rooms SET rounds=?, choices=?, status=? WHERE room_id=?",
                     (json.dumps(rounds, ensure_ascii=False), json.dumps(choices, ensure_ascii=False), status, room_id))
        conn.commit()
        return jsonify(fetch_room_dict(conn, room_id))
    finally:
        conn.close()

@app.route('/rooms/<room_id>/chito', methods=['POST'])
def chito_room(room_id):
    conn = get_db()
    try:
        body = request.get_json(silent=True) or {}
        action, player = body.get('action'), body.get('player')
        row = conn.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()
        if not row: return jsonify({'error': '방 없음'}), 404
        choices = json.loads(row['choices'] or '{}')
        rounds = json.loads(row['rounds'] or '[]')
        gs = choices.get('game_state', {})
        if action == 'select_char':
            char = body.get('char')
            if gs['p1']['name'] == player: gs['p1']['char'] = char
            elif gs['p2']['name'] == player: gs['p2']['char'] = char
            if gs['p1'].get('char') and gs['p2'].get('char'): gs['phase'] = 'select'
        elif action == 'submit_queue':
            queue = body.get('queue', [])
            if gs['p1']['name'] == player: gs['p1']['queue'] = queue
            elif gs['p2']['name'] == player: gs['p2']['queue'] = queue
            if gs['p1']['queue'] and gs['p2']['queue']:
                gs = chito_resolve(gs)
                if gs.get('winner') and gs['winner'] != 'draw':
                    for ri, rd in enumerate(rounds):
                        for mi, m in enumerate(rd):
                            if not m['winner'] and m['p1'] and m['p2'] and {m['p1'],m['p2']} == {gs['p1']['name'],gs['p2']['name']}:
                                m['winner'] = gs['winner']
                                prop(rounds, ri, mi, gs['winner'])
                                if ri+1 < len(rounds):
                                    nm = rounds[ri+1][mi//2]
                                    if nm['p1'] and nm['p2']: gs = init_chito_state(nm['p1'], nm['p2'])
                                    else: gs = {}
                                else: gs = {}
                                break
        choices['game_state'] = gs
        status = 'finished' if (rounds and rounds[-1][0].get('winner')) else row['status']
        conn.execute("UPDATE rooms SET choices=?, rounds=?, status=? WHERE room_id=?",
                     (json.dumps(choices, ensure_ascii=False), json.dumps(rounds, ensure_ascii=False), status, room_id))
        conn.commit()
        return jsonify(fetch_room_dict(conn, room_id))
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    print("Local server started at http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
