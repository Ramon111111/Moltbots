import json
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent
CREDS_PATH = BASE_DIR / 'moltbook-credentials.json'
LOG_PATH = BASE_DIR / 'aktivitaet.log'
BASE_URL = 'https://www.moltbook.com/api/v1'

NUM_WORDS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11,
    'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16,
    'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30,
    'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
}

def load_creds():
    return json.loads(CREDS_PATH.read_text(encoding='utf-8'))

def headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'moltbot-heartbeat/2.0',
    }

def sanitize(text):
    if text is None:
        return ''
    s = str(text)
    replacements = {
        '’': "'", '‘': "'", '`': "'", '´': "'",
        '“': '"', '”': '"', '„': '"',
        '–': '-', '—': '-', '…': '...',
        '\xa0': ' '
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.replace(';', ',').replace('\r', ' ').replace('\n', ' ').strip()

def normalize_word(token):
    token = re.sub(r'[^a-z0-9]', '', str(token).lower())
    return re.sub(r'(.)\1+', r'\1', token)

def fuzzy_number(token):
    if not token:
        return None
    if token.isdigit():
        return int(token)
    best_word, best_score = None, 0.0
    for word, val in NUM_WORDS.items():
        score = SequenceMatcher(None, token, word).ratio()
        if word in token or token in word:
            score += 0.2
        if score > best_score:
            best_score = score
            best_word = word
    if best_score >= 0.72:
        return NUM_WORDS[best_word]
    return None

def extract_numbers_from_words(text):
    tokens = [normalize_word(tok) for tok in re.split(r'\s+', text)]
    tokens = [t for t in tokens if t]
    numbers = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        current = fuzzy_number(tok)
        combined = None
        if i + 1 < len(tokens):
            combined = fuzzy_number(tok + tokens[i + 1])
        if combined is not None:
            numbers.append(combined)
            i += 2
            continue
        if current is not None:
            if current >= 20 and current % 10 == 0 and i + 1 < len(tokens):
                nxt = fuzzy_number(tokens[i + 1])
                if nxt is not None and nxt < 10:
                    numbers.append(current + nxt)
                    i += 2
                    continue
            numbers.append(current)
        i += 1
    return numbers

def solve_challenge(challenge):
    if not challenge:
        return None
    text = str(challenge)
    m = re.search(r'(-?\d+(?:\.\d+)?)\s*([+\-*/])\s*(-?\d+(?:\.\d+)?)', text.replace('=', ' '))
    if m:
        a = float(m.group(1))
        op = m.group(2)
        b = float(m.group(3))
    else:
        nums = extract_numbers_from_words(text)
        if len(nums) < 2:
            return None
        a, b = float(nums[0]), float(nums[1])
        lowered = normalize_word(text)
        if any(w in lowered for w in ['lose', 'minus', 'left', 'remain', 'afterspending']):
            op = '-'
        elif any(w in lowered for w in ['times', 'multiply', 'product']):
            op = '*'
        elif any(w in lowered for w in ['divide', 'quotient', 'per']):
            op = '/'
        else:
            op = '+'
            
    if op == '+': val = a + b
    elif op == '-': val = a - b
    elif op == '*': val = a * b
    else: val = a / b
    return f'{val:.2f}'

def extract_verify_fields(payload):
    candidates = []
    if isinstance(payload, dict):
        candidates.append(payload)
        for key in ('comment', 'post', 'verification', 'challenge'):
            val = payload.get(key)
            if isinstance(val, dict):
                candidates.append(val)
    code, challenge, status = None, '', None
    for obj in candidates:
        code = code or obj.get('verification_code')
        challenge = challenge or obj.get('challenge_text') or obj.get('verification_challenge') or obj.get('question') or (obj.get('challenge') if isinstance(obj.get('challenge'), str) else '')
        status = status or obj.get('verification_status') or obj.get('verificationStatus')
    return code, challenge, status

def verify_if_needed(session, token, payload, default_success='Kommentar'):
    code, challenge, status = extract_verify_fields(payload)

    if isinstance(payload, dict) and payload.get('success'):
        message = str(payload.get('message') or '').lower()
        if 'already said this' in message or 'comment added' in message or 'post created' in message or not code:
            return True, default_success
        if status in (None, '', 'verified'):
            return True, default_success

    if status != 'pending':
        if status == 'verified' or (isinstance(payload, dict) and payload.get('success')):
            return True, default_success
        return True, default_success

    answer = solve_challenge(challenge)
    if not code or answer is None:
        payload_preview = json.dumps(payload, ensure_ascii=False)[:800] if isinstance(payload, (dict, list)) else str(payload)[:800]
        return False, f"Fehler: Challenge ungeloest ('{challenge}') | payload={payload_preview}"

    try:
        resp = session.post(
            f'{BASE_URL}/verify',
            headers=headers(token),
            json={'verification_code': code, 'answer': answer},
            timeout=30
        )
    except Exception as e:
        return False, f"Fehler: Verify Request ({str(e)})"

    if not resp.ok:
        return False, f"Fehler: Verify HTTP {resp.status_code}"

    try:
        data = resp.json()
        if data.get('success') or data.get('verification_status') == 'verified':
            return True, default_success
        msg = data.get('message') or data.get('error') or 'abgelehnt'
        return False, f"Fehler: Verify abgelehnt ({msg})"
    except Exception:
        return True, default_success

def append_log(found_title, found_content, written_text, status, link):
    now = datetime.now().astimezone()
    line = ';'.join([
        now.strftime('%H:%M:%S'),
        now.strftime('%Y-%m-%d'),
        sanitize(found_title) or 'N/A',
        sanitize(found_content) or 'N/A',
        sanitize(written_text),
        sanitize(status),
        sanitize(link),
    ])
    with LOG_PATH.open('a', encoding='utf-8', newline='') as f:
        if f.tell() > 0:
            f.write('\n')
        f.write(line)

def fetch_post_details(session, token, post_id):
    """Holt den vollständigen Originalpost direkt über die API ab."""
    try:
        resp = session.get(f'{BASE_URL}/posts/{post_id}', headers=headers(token), timeout=15)
        if resp.ok:
            data = resp.json()
            post = data.get('post') if isinstance(data, dict) and 'post' in data else data
            if isinstance(post, dict):
                return post.get('title') or 'N/A', post.get('content') or 'N/A'
    except Exception:
        pass
    return None, None

def handle_comment(session, token, post_id, comment_text, found_title=None, found_content=None):
    link = f'https://www.moltbook.com/post/{post_id}'
    
    # Immer versuchen, den vollständigen Originaltext direkt via API zu laden
    api_title, api_content = fetch_post_details(session, token, post_id)
    if api_title is not None and api_content is not None:
        found_title = api_title
        found_content = api_content
    else:
        found_title = found_title or 'N/A'
        found_content = found_content or 'N/A'

    try:
        resp = session.post(
            f'{BASE_URL}/posts/{post_id}/comments',
            headers=headers(token),
            json={'content': comment_text},
            timeout=30
        )
        data = resp.json() if resp.ok else {'raw': resp.text}

        if resp.status_code == 429:
            append_log(found_title, found_content, comment_text, "Fehler: Rate Limited (429)", link)
            sys.exit(1)

        if not resp.ok:
            print(f"HTTP Fehler {resp.status_code}")
            sys.exit(1)

        verified, status_text = verify_if_needed(session, token, data, default_success='Kommentar')
        if verified:
            append_log(found_title, found_content, comment_text, status_text, link)
            print(f"Erfolg: {status_text} geloggt.")
            sys.exit(0)
        else:
            print(f"Verifikation fehlgeschlagen: {status_text}")
            sys.exit(1)

    except Exception as exc:
        print(f"Fehler: {str(exc)}")
        sys.exit(1)

def handle_post(session, token, title, content):
    link = 'https://www.moltbook.com'
    written = f"{title}: {content}"
    try:
        resp = session.post(
            f'{BASE_URL}/posts',
            headers=headers(token),
            json={'submolt_name': 'general', 'title': title, 'content': content},
            timeout=30
        )
        data = resp.json() if resp.ok else {'raw': resp.text}

        if resp.status_code == 429:
            append_log('N/A', 'N/A', written, "Fehler: Rate Limited (429)", link)
            sys.exit(1)

        if not resp.ok:
            print(f"HTTP Fehler {resp.status_code}")
            sys.exit(1)

        post_obj = data.get('post') if isinstance(data, dict) else None
        if isinstance(post_obj, dict) and post_obj.get('id'):
            link = f"https://www.moltbook.com/post/{post_obj.get('id')}"

        verified, status_text = verify_if_needed(session, token, data, default_success='Post')
        if verified:
            append_log('N/A', 'N/A', written, status_text, link)
            print(f"Erfolg: {status_text} geloggt.")
            sys.exit(0)
        else:
            print(f"Verifikation fehlgeschlagen: {status_text}")
            sys.exit(1)

    except Exception as exc:
        print(f"Fehler: {str(exc)}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Nutzung:")
        print("  Kommentar: python heartbeat-moltbook-action.py comment <post_id> <comment_text>")
        print("  Post:      python heartbeat-moltbook-action.py post <title> <content>")
        sys.exit(1)

    action = sys.argv[1].lower()
    creds = load_creds()
    token = creds['api_key']
    session = requests.Session()

    if action == 'comment':
        if len(sys.argv) < 4:
            print("Fehler: post_id und comment_text erforderlich.")
            sys.exit(1)
        post_id = sys.argv[2]
        comment_text = sys.argv[3]
        # Optionale manuelle Übergabe (wird durch API-Fetch überschrieben)
        found_title = sys.argv[4] if len(sys.argv) > 4 else None
        found_content = " ".join(sys.argv[5:]) if len(sys.argv) > 5 else None
        handle_comment(session, token, post_id, comment_text, found_title, found_content)

    elif action == 'post':
        if len(sys.argv) < 4:
            print("Fehler: title und content erforderlich.")
            sys.exit(1)
        title = sys.argv[2]
        content = sys.argv[3]
        handle_post(session, token, title, content)

    else:
        print(f"Unbekannte Aktion: {action}")
        sys.exit(1)

if __name__ == '__main__':
    main()