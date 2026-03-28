import json
import pymysql
import uuid
import time
import os
import random

DB_HOST = os.environ['DB_HOST']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_NAME = os.environ['DB_NAME']

def get_conn():
    return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
                           db=DB_NAME, charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)

def init_db(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                room_id VARCHAR(8) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                game_type VARCHAR(50) DEFAULT 'rps',
                status VARCHAR(20) DEFAULT 'waiting',
                players TEXT,
                rounds TEXT,
                choices TEXT,
                created_at BIGINT
            )
        """)
        for col, defn in [('game_type',"VARCHAR(50) DEFAULT 'rps'"), ('choices','TEXT')]:
            try:
                cur.execute(f"ALTER TABLE rooms ADD COLUMN {col} {defn}")
            except: pass
    conn.commit()

def resp(code, body):
    return {
        'statusCode': code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,POST,DELETE,OPTIONS'
        },
        'body': json.dumps(body, ensure_ascii=False)
    }

def next_pow2(n):
    p = 1
    while p < n: p *= 2
    return p

def build_bracket(players):
    size = next_pow2(len(players))
    shuffled = players[:]
    random.shuffle(shuffled)
    # 부전승을 최소화: None을 최대한 분산 배치 (뒤쪽에 몰기)
    byes = size - len(shuffled)
    # None을 짝수 인덱스 뒤쪽에 배치해서 부전승이 한쪽에 몰리게
    slots = []
    bye_positions = set(range(size - byes * 2, size, 2))  # 뒤쪽 짝수 위치에 bye
    bye_idx = 0
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

    # 초기 부전승만 처리 (첫 라운드에서 None 상대인 경우만)
    for mi, m in enumerate(rounds[0]):
        if m['p1'] and not m['p2']:
            m['winner'] = m['p1']
            prop(rounds, 0, mi, m['p1'])
        elif not m['p1'] and m['p2']:
            m['winner'] = m['p2']
            prop(rounds, 0, mi, m['p2'])
        elif not m['p1'] and not m['p2']:
            pass  # 빈 슬롯, 나중에 전파로 채워짐

    return rounds

def prop(rounds, ri, mi, winner):
    if ri + 1 >= len(rounds): return
    nxt = rounds[ri+1][mi//2]
    if mi % 2 == 0: nxt['p1'] = winner
    else: nxt['p2'] = winner

def init_chito_state(p1name, p2name, p1char=None, p2char=None):
    chars = list(CHITO_SKILLS.keys())
    return {
        'p1': {'name': p1name, 'char': p1char or chars[0], 'hp': 100, 'mp': 100, 'x': 2, 'y': 3, 'dir': -1, 'queue': []},
        'p2': {'name': p2name, 'char': p2char or chars[1], 'hp': 100, 'mp': 100, 'x': 2, 'y': 1, 'dir': 1, 'queue': []},
        'turn': 1, 'winner': None, 'log': [], 'phase': 'char_select'
    }

def rps_win(a, b):
    if a == b: return None
    wins = [('✊','✌️'),('✌️','🖐️'),('🖐️','✊')]
    return a if (a,b) in wins else b

CHITO_SKILLS = {
  "팔달 치토": [
    {"name":"팔달 강타","power":30,"cost":25,"range":[[0,1]]},
    {"name":"팔달 폭풍","power":50,"cost":50,"range":[[-1,0],[1,0],[0,1],[0,-1]]},
    {"name":"팔달 돌진","power":25,"cost":25,"range":[[-1,1],[0,1],[1,1]]},
    {"name":"팔달 회전베기","power":25,"cost":35,"range":[[0,1],[1,0]]},
    {"name":"팔달 찌르기","power":15,"cost":15,"range":[[0,1]]}
  ],
  "다산관 치토": [
    {"name":"다산 일격","power":50,"cost":50,"range":[[0,1]]},
    {"name":"다산 지식파동","power":15,"cost":15,"range":[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]},
    {"name":"다산 직진공격","power":25,"cost":15,"range":[[0,1],[0,2]]},
    {"name":"다산 견제","power":25,"cost":25,"range":[[0,1]]},
    {"name":"다산 기본타","power":15,"cost":15,"range":[[0,1]]}
  ],
  "원천 치토": [
    {"name":"원천 파쇄","power":40,"cost":45,"range":[[0,1],[0,2]]},
    {"name":"원천 확산","power":25,"cost":30,"range":[[-1,1],[0,1],[1,1]]},
    {"name":"원천 찌르기","power":15,"cost":25,"range":[[0,1]]},
    {"name":"원천 반격","power":30,"cost":20,"range":[[0,1],[1,0]]},
    {"name":"원천 기본타","power":15,"cost":15,"range":[[0,1]]}
  ],
  "율곡 치토": [
    {"name":"율곡 강습","power":50,"cost":50,"range":[[0,1]]},
    {"name":"율곡 파동","power":15,"cost":15,"range":[[-1,1],[0,1],[1,1]]},
    {"name":"율곡 연격","power":25,"cost":35,"range":[[0,1],[0,2]]},
    {"name":"율곡 견제","power":25,"cost":20,"range":[[0,1]]},
    {"name":"율곡 기본타","power":15,"cost":15,"range":[[0,1]]}
  ],
  "연암 치토": [
    {"name":"연암 붕괴","power":40,"cost":50,"range":[[0,1],[0,2]]},
    {"name":"연암 확산타","power":25,"cost":30,"range":[[-1,1],[0,1],[1,1]]},
    {"name":"연암 찌르기","power":25,"cost":15,"range":[[0,1]]},
    {"name":"연암 콤보","power":25,"cost":30,"range":[[0,1],[1,0]]},
    {"name":"연암 기본타","power":15,"cost":15,"range":[[0,1]]}
  ],
  "성호 치토": [
    {"name":"성호 강타","power":35,"cost":25,"range":[[0,1]]},
    {"name":"성호 폭발","power":50,"cost":45,"range":[[-1,1],[0,1],[1,1],[0,2]]},
    {"name":"성호 견제","power":25,"cost":15,"range":[[0,1]]},
    {"name":"성호 측면타","power":20,"cost":35,"range":[[-1,0],[1,0]]},
    {"name":"성호 강화타","power":25,"cost":40,"range":[[0,1],[1,0]]}
  ],
  "용지 치토": [
    {"name":"용지 돌격","power":40,"cost":50,"range":[[0,1],[0,2]]},
    {"name":"용지 견제","power":25,"cost":25,"range":[[0,1]]},
    {"name":"용지 필살","power":60,"cost":50,"range":[[0,1],[0,2],[0,3]]},
    {"name":"용지 콤보","power":30,"cost":20,"range":[[0,1],[1,0]]},
    {"name":"용지 기본타","power":25,"cost":15,"range":[[0,1]]}
  ],
  "아주대 본관 치토": [
    {"name":"본관 붕괴","power":60,"cost":70,"range":[[0,1],[0,2]]},
    {"name":"본관 파동","power":20,"cost":15,"range":[[-1,0],[1,0],[0,1]]},
    {"name":"본관 확산","power":40,"cost":50,"range":[[-1,1],[0,1],[1,1],[0,2]]},
    {"name":"본관 견제","power":25,"cost":20,"range":[[0,1]]},
    {"name":"본관 기본타","power":15,"cost":15,"range":[[0,1]]}
  ]
}

def chito_resolve(gs):
    """치토 배틀 턴 처리: 이동 먼저, 공격 나중"""
    p1, p2 = gs['p1'], gs['p2']
    log = []
    GRID = 5

    def clamp(v): return max(0, min(GRID-1, v))
    def in_range(attacker, target, skill_range):
        d = attacker['dir']
        for dx, dy in skill_range:
            if attacker['x']+dx == target['x'] and attacker['y']+dy*d == target['y']:
                return True
        return False

    # 이동 먼저
    for p, other in [(p1,p2),(p2,p1)]:
        for card in p['queue']:
            if card['type'] == 'move':
                nx = clamp(p['x'] + card['dx'])
                ny = clamp(p['y'] + card['dy'] * p['dir'])
                if nx != other['x'] or ny != other['y']:
                    p['x'], p['y'] = nx, ny
                    log.append(f"{p['name']} {card['name']}")

    # 공격
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

    # 기력 회복
    for p in [p1, p2]:
        p['mp'] = min(100, p['mp'] + 15)
        p['queue'] = []

    gs['turn'] = gs.get('turn', 1) + 1
    gs['log'] = (log + gs.get('log', []))[:30]

    # 승패
    if p1['hp'] <= 0 and p2['hp'] <= 0: gs['winner'] = 'draw'
    elif p1['hp'] <= 0: gs['winner'] = p2['name']
    elif p2['hp'] <= 0: gs['winner'] = p1['name']
    return gs

def lambda_handler(event, context):
    conn = get_conn()
    init_db(conn)
    method = event.get('httpMethod','')
    path = event.get('path','').rstrip('/')
    parts = [p for p in path.split('/') if p]
    body = {}
    if event.get('body'):
        try: body = json.loads(event['body'])
        except: pass

    if method == 'OPTIONS':
        conn.close(); return resp(200, {})

    try:
        # GET /rooms
        if method == 'GET' and parts == ['rooms']:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM rooms ORDER BY created_at DESC")
                rows = cur.fetchall()
            for r in rows:
                r['players'] = json.loads(r['players'] or '[]')
                r['rounds'] = json.loads(r['rounds'] or '[]')
                r['choices'] = json.loads(r['choices'] or '{}')
            return resp(200, rows)

        # POST /rooms
        if method == 'POST' and parts == ['rooms']:
            name = body.get('name','').strip()
            game_type = body.get('game_type','rps')
            if not name: return resp(400, {'error': '방 이름을 입력하세요'})
            room_id = str(uuid.uuid4())[:8]
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO rooms (room_id,name,game_type,status,players,rounds,choices,created_at) VALUES (%s,%s,%s,'waiting',%s,%s,%s,%s)",
                    (room_id, name, game_type, '[]', '[]', '{}', int(time.time()))
                )
            conn.commit()
            return resp(200, {'room_id': room_id, 'name': name, 'game_type': game_type,
                              'status': 'waiting', 'players': [], 'rounds': [], 'choices': {}})

        # GET /rooms/{id}
        if method == 'GET' and len(parts) == 2 and parts[0] == 'rooms':
            room_id = parts[1]
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM rooms WHERE room_id=%s", (room_id,))
                row = cur.fetchone()
            if not row: return resp(404, {'error': '방 없음'})
            row['players'] = json.loads(row['players'] or '[]')
            row['rounds'] = json.loads(row['rounds'] or '[]')
            row['choices'] = json.loads(row['choices'] or '{}')
            return resp(200, row)

        # POST /rooms/{id}/join
        if method == 'POST' and len(parts) == 3 and parts[2] == 'join':
            room_id = parts[1]
            player = body.get('player','').strip()
            if not player: return resp(400, {'error': '이름을 입력하세요'})
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM rooms WHERE room_id=%s", (room_id,))
                row = cur.fetchone()
            if not row: return resp(404, {'error': '방 없음'})
            if row['status'] != 'waiting': return resp(400, {'error': '이미 시작된 방입니다'})
            players = json.loads(row['players'] or '[]')
            if player in players: return resp(400, {'error': '이미 참가한 이름입니다'})
            players.append(player)
            with conn.cursor() as cur:
                cur.execute("UPDATE rooms SET players=%s WHERE room_id=%s",
                            (json.dumps(players, ensure_ascii=False), room_id))
            conn.commit()
            row['players'] = players
            row['rounds'] = json.loads(row['rounds'] or '[]')
            row['choices'] = json.loads(row['choices'] or '{}')
            return resp(200, row)

        # POST /rooms/{id}/leave
        if method == 'POST' and len(parts) == 3 and parts[2] == 'leave':
            room_id = parts[1]
            player = body.get('player','').strip()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM rooms WHERE room_id=%s", (room_id,))
                row = cur.fetchone()
            if not row: return resp(404, {'error': '방 없음'})
            if row['status'] != 'waiting': return resp(400, {'error': '진행 중인 방은 나갈 수 없습니다'})
            players = json.loads(row['players'] or '[]')
            players = [p for p in players if p != player]
            with conn.cursor() as cur:
                cur.execute("UPDATE rooms SET players=%s WHERE room_id=%s",
                            (json.dumps(players, ensure_ascii=False), room_id))
            conn.commit()
            row['players'] = players
            row['rounds'] = json.loads(row['rounds'] or '[]')
            row['choices'] = json.loads(row['choices'] or '{}')
            return resp(200, row)

        # POST /rooms/{id}/ready - 준비 상태 + 하트비트
        if method == 'POST' and len(parts) == 3 and parts[2] == 'ready':
            room_id = parts[1]
            player = body.get('player')
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM rooms WHERE room_id=%s", (room_id,))
                row = cur.fetchone()
            if not row: return resp(404, {'error': '방 없음'})
            choices = json.loads(row['choices'] or '{}')
            now = int(time.time())
            if 'ready' not in choices: choices['ready'] = {}
            choices['ready'][player] = now  # 마지막 heartbeat 시각
            players = json.loads(row['players'] or '[]')
            # 10초 이내 heartbeat 있는 플레이어만 online
            online = [p for p in players if now - choices['ready'].get(p, 0) <= 10]
            choices['online'] = online
            # 모두 online이면 게임 시작 가능 신호
            all_ready = set(online) == set(players) and len(players) >= 2
            choices['all_ready'] = all_ready
            with conn.cursor() as cur:
                cur.execute("UPDATE rooms SET choices=%s WHERE room_id=%s",
                            (json.dumps(choices, ensure_ascii=False), room_id))
            conn.commit()
            row['players'] = players
            row['rounds'] = json.loads(row['rounds'] or '[]')
            row['choices'] = choices
            return resp(200, row)

        # POST /rooms/{id}/forfeit - 포기
        if method == 'POST' and len(parts) == 3 and parts[2] == 'forfeit':
            room_id = parts[1]
            player = body.get('player')
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM rooms WHERE room_id=%s", (room_id,))
                row = cur.fetchone()
            if not row: return resp(404, {'error': '방 없음'})
            rounds = json.loads(row['rounds'] or '[]')
            choices = json.loads(row['choices'] or '{}')
            # 현재 경기에서 상대방을 승자로
            for ri, rd in enumerate(rounds):
                for mi, m in enumerate(rd):
                    if not m['winner'] and m['p1'] and m['p2']:
                        if m['p1'] == player or m['p2'] == player:
                            winner = m['p2'] if m['p1'] == player else m['p1']
                            m['winner'] = winner
                            m['log'].append({'forfeit': player, 'winner': winner})
                            prop(rounds, ri, mi, winner)
                            # 치토 배틀이면 game_state도 업데이트
                            if 'game_state' in choices:
                                choices['game_state']['winner'] = winner
                            status = 'finished' if rounds[-1][0].get('winner') else row['status']
                            with conn.cursor() as cur:
                                cur.execute("UPDATE rooms SET rounds=%s, choices=%s, status=%s WHERE room_id=%s",
                                            (json.dumps(rounds, ensure_ascii=False),
                                             json.dumps(choices, ensure_ascii=False),
                                             status, room_id))
                            conn.commit()
                            row['rounds'] = rounds
                            row['choices'] = choices
                            row['players'] = json.loads(row['players'] or '[]')
                            row['status'] = status
                            return resp(200, row)
            return resp(200, {'error': '진행 중인 경기 없음'})

        # POST /rooms/{id}/start
        if method == 'POST' and len(parts) == 3 and parts[2] == 'start':
            room_id = parts[1]
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM rooms WHERE room_id=%s", (room_id,))
                row = cur.fetchone()
            if not row: return resp(404, {'error': '방 없음'})
            players = json.loads(row['players'] or '[]')
            if len(players) < 2: return resp(400, {'error': '최소 2명 필요합니다'})
            choices = json.loads(row['choices'] or '{}')
            # 모든 참가자가 online 상태여야 시작 가능
            if not choices.get('all_ready'):
                return resp(400, {'error': '모든 참가자가 준비되지 않았습니다'})
            rounds = build_bracket(players)
            # 치토 배틀: 첫 경기 game_state 초기화
            game_state = {}
            if row['game_type'] == 'chito':
                m = rounds[0][0]
                if m['p1'] and m['p2']:
                    game_state = init_chito_state(m['p1'], m['p2'])
            with conn.cursor() as cur:
                cur.execute("UPDATE rooms SET status='playing', rounds=%s, choices=%s WHERE room_id=%s",
                            (json.dumps(rounds, ensure_ascii=False),
                             json.dumps({'game_state': game_state}, ensure_ascii=False),
                             room_id))
            conn.commit()
            row['status'] = 'playing'
            row['players'] = players
            row['rounds'] = rounds
            row['choices'] = {'game_state': game_state}
            return resp(200, row)

        # POST /rooms/{id}/chito - 치토 배틀 액션 (캐릭터 선택 or 카드 제출)
        if method == 'POST' and len(parts) == 3 and parts[2] == 'chito':
            room_id = parts[1]
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM rooms WHERE room_id=%s", (room_id,))
                row = cur.fetchone()
            if not row: return resp(404, {'error': '방 없음'})
            choices = json.loads(row['choices'] or '{}')
            rounds = json.loads(row['rounds'] or '[]')
            gs = choices.get('game_state', {})
            action = body.get('action')  # 'select_char' | 'submit_queue'
            player = body.get('player')

            if action == 'select_char':
                char = body.get('char')
                if gs['p1']['name'] == player: gs['p1']['char'] = char
                elif gs['p2']['name'] == player: gs['p2']['char'] = char
                # 둘 다 선택했으면 phase → select
                if gs['p1'].get('char') and gs['p2'].get('char'):
                    gs['phase'] = 'select'

            elif action == 'submit_queue':
                queue = body.get('queue', [])
                if gs['p1']['name'] == player: gs['p1']['queue'] = queue
                elif gs['p2']['name'] == player: gs['p2']['queue'] = queue
                # 둘 다 제출했으면 턴 처리
                if gs['p1']['queue'] and gs['p2']['queue']:
                    gs = chito_resolve(gs)
                    # 치토 배틀 승자 → 토너먼트 경기 결과 반영
                    if gs.get('winner') and gs['winner'] != 'draw':
                        # 현재 진행 중인 경기 찾기
                        for ri, rd in enumerate(rounds):
                            for mi, m in enumerate(rd):
                                if not m['winner'] and m['p1'] and m['p2']:
                                    if {m['p1'],m['p2']} == {gs['p1']['name'],gs['p2']['name']}:
                                        m['winner'] = gs['winner']
                                        m['log'].append({'game':'chito','winner':gs['winner']})
                                        prop(rounds, ri, mi, gs['winner'])
                                        # 다음 경기 game_state 초기화
                                        if ri+1 < len(rounds):
                                            nm = rounds[ri+1][mi//2]
                                            if nm['p1'] and nm['p2']:
                                                gs = init_chito_state(nm['p1'], nm['p2'])
                                            else:
                                                gs = {}
                                        else:
                                            gs = {}
                                        break
                    elif gs.get('winner') == 'draw':
                        # 무승부 시 재시작
                        gs['p1']['hp'] = 100; gs['p1']['mp'] = 100
                        gs['p2']['hp'] = 100; gs['p2']['mp'] = 100
                        gs['winner'] = None; gs['turn'] = 1
                        gs['phase'] = 'select'

            choices['game_state'] = gs
            status = row['status']
            if rounds and rounds[-1][0].get('winner'):
                status = 'finished'
            with conn.cursor() as cur:
                cur.execute("UPDATE rooms SET choices=%s, rounds=%s, status=%s WHERE room_id=%s",
                            (json.dumps(choices, ensure_ascii=False),
                             json.dumps(rounds, ensure_ascii=False),
                             status, room_id))
            conn.commit()
            row['choices'] = choices
            row['rounds'] = rounds
            row['players'] = json.loads(row['players'] or '[]')
            row['status'] = status
            return resp(200, row)

        # POST /rooms/{id}/choice  - RPS 개인 선택 제출
        if method == 'POST' and len(parts) == 3 and parts[2] == 'choice':
            room_id = parts[1]
            ri = body.get('round')
            mi = body.get('match')
            player = body.get('player')
            choice = body.get('choice')
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM rooms WHERE room_id=%s", (room_id,))
                row = cur.fetchone()
            if not row: return resp(404, {'error': '방 없음'})
            rounds = json.loads(row['rounds'] or '[]')
            choices = json.loads(row['choices'] or '{}')
            match = rounds[ri][mi]

            # 이미 승자 있으면 무시
            if match['winner']:
                row['players'] = json.loads(row['players'] or '[]')
                row['rounds'] = rounds
                row['choices'] = choices
                return resp(200, row)

            key = f"{ri}_{mi}"
            if key not in choices: choices[key] = {}
            choices[key][player] = choice

            # 두 선수 모두 선택했으면 결과 처리
            p1, p2 = match['p1'], match['p2']
            if p1 in choices[key] and p2 in choices[key]:
                c1, c2 = choices[key][p1], choices[key][p2]
                winning_choice = rps_win(c1, c2)
                if winning_choice is None:
                    # 비김 - 선택 초기화
                    choices[key] = {}
                else:
                    winner = p1 if winning_choice == c1 else p2
                    match['winner'] = winner
                    match['log'].append({'p1':p1,'p2':p2,'c1':c1,'c2':c2,'winner':winner})
                    prop(rounds, ri, mi, winner)
                    del choices[key]

            status = row['status']
            if rounds[-1][0].get('winner'):
                status = 'finished'

            with conn.cursor() as cur:
                cur.execute("UPDATE rooms SET rounds=%s, choices=%s, status=%s WHERE room_id=%s",
                            (json.dumps(rounds, ensure_ascii=False),
                             json.dumps(choices, ensure_ascii=False),
                             status, room_id))
            conn.commit()
            row['players'] = json.loads(row['players'] or '[]')
            row['rounds'] = rounds
            row['choices'] = choices
            row['status'] = status
            return resp(200, row)

        # DELETE /rooms/{id}
        if method == 'DELETE' and len(parts) == 2 and parts[0] == 'rooms':
            room_id = parts[1]
            requester = body.get('requester', '')
            if not requester.endswith('_admin'):
                return resp(403, {'error': '관리자만 삭제할 수 있습니다'})
            with conn.cursor() as cur:
                cur.execute("DELETE FROM rooms WHERE room_id=%s", (room_id,))
            conn.commit()
            return resp(200, {'ok': True})

        return resp(404, {'error': 'Not found'})
    finally:
        conn.close()
