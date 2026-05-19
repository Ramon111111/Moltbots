import json
import re
import sys
from datetime import datetime
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent
CREDS_PATH = BASE_DIR / 'moltbook-credentials.json'
LOG_PATH = BASE_DIR / 'aktivitaet.log'
RESULT_PATH = BASE_DIR / 'heartbeat-action-result.json'
BASE_URL = 'https://www.moltbook.com/api/v1'

def load_creds():
    return json.loads(CREDS_PATH.read_text(encoding='utf-8'))

def headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'moltbot-heartbeat/1.1',
    }

def sanitize(text):
    if text is None:
        return ''
    return str(text).replace(';', ' ').replace('\r', ' ').replace('\n', ' ').strip()

def solve_challenge(challenge):
    if not challenge or not isinstance(challenge, str):
        return None
    expr = challenge.replace('=', ' ').strip()
    m = re.search(r'(-?\d+(?:\.\d+)?)\s*([+\-*/])\s*(-?\d+(?:\.\d+)?)', expr)
    if not m:
        return None
    a, op, b = float(m.group(1)), m.group(2), float(m.group(3))
    if op == '+': return f'{a + b:.2f}'
    elif op == '-': return f'{a - b:.2f}'
    elif op == '*': return f'{a * b:.2f}'
    else: return f'{a / b:.2f}'

def extract_verification(payload):
    verification = payload.get('verification') or {}
    challenge_value = payload.get('challenge')
    challenge_obj = challenge_value if isinstance(challenge_value, dict) else {}
    challenge_text = challenge_value if isinstance(challenge_value, str) else ''
    code = payload.get('verification_code') or verification.get('verification_code') or challenge_obj.get('verification_code')
    challenge = challenge_text or payload.get('verification_challenge') or payload.get('challenge_text') or verification.get('challenge') or verification.get('question') or challenge_obj.get('question') or ''
    return code, challenge

def verify_if_needed(session, token, payload):
    status = payload.get('verification_status')
    if status != 'pending':
        return {'verified': status == 'verified', 'verification_status': status}
    code, challenge = extract_verification(payload)
    answer = solve_challenge(challenge)
    result = {'verified': False, 'verification_status': 'pending', 'verification_code': code, 'challenge': challenge, 'answer': answer}
    if not code or answer is None:
        result['verification_error'] = 'missing verification data'
        return result
    resp = session.post(f'{BASE_URL}/verify', headers=headers(token), json={'verification_code': code, 'answer': answer}, timeout=30)
    result['verify_status_code'] = resp.status_code
    result['verified'] = resp.ok
    if resp.ok: result['verification_status'] = 'verified'
    return result

def append_log(found_text, written_text, link, status):
    now = datetime.now().astimezone()
    line = ';'.join([
        now.strftime('%H:%M:%S'),
        now.strftime('%Y-%m-%d'),
        sanitize(found_text) or 'N/A',
        sanitize(written_text),
        sanitize(link),
        sanitize(status),
    ])
    with LOG_PATH.open('a', encoding='utf-8', newline='') as f:
        if f.tell() > 0: f.write('\n')
        f.write(line)

def main():
    if len(sys.argv) < 3:
        print("Fehler: Bitte Parameter übergeben. Nutzung: python heartbeat-moltbook-action.py <post_id> <comment_text>")
        sys.exit(1)
        
    post_id = sys.argv[1]
    comment_text = sys.argv[2]
    
    creds = load_creds()
    token = creds['api_key']
    session = requests.Session()
    
    link = f'https://www.moltbook.com/post/{post_id}'
    
    try:
        resp = session.post(f'{BASE_URL}/posts/{post_id}/comments', headers=headers(token), json={'content': comment_text}, timeout=30)
        data = resp.json() if resp.ok else {'raw': resp.text}
        
        if resp.status_code == 429:
            append_log(f"Post {post_id}", comment_text, link, "Fehler: Rate Limited (429)")
            return
            
        if not resp.ok:
            append_log(f"Post {post_id}", comment_text, link, f"Fehler: HTTP {resp.status_code}")
            return
            
        verify = verify_if_needed(session, token, data)
        status = 'Kommentar' if verify.get('verified') else 'Fehler: Verifikation ausstehend'
        append_log(f"Post {post_id}", comment_text, link, status)
        print("Erfolgreich gepostet und geloggt.")
        
    except Exception as exc:
        append_log(f"Post {post_id}", comment_text, link, f"Fehler: {str(exc)}")

if __name__ == '__main__':
    main()