import json
import re
from datetime import datetime
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
CREDS_PATH = BASE_DIR / 'moltbook-credentials.json'
FEED_PATH = BASE_DIR / 'feed.json'
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
    a = float(m.group(1))
    op = m.group(2)
    b = float(m.group(3))
    if op == '+':
        result = a + b
    elif op == '-':
        result = a - b
    elif op == '*':
        result = a * b
    else:
        result = a / b
    return f'{result:.2f}'


def extract_verification(payload):
    verification = payload.get('verification') or {}
    challenge_value = payload.get('challenge')
    challenge_obj = challenge_value if isinstance(challenge_value, dict) else {}
    challenge_text = challenge_value if isinstance(challenge_value, str) else ''
    code = payload.get('verification_code') or verification.get('verification_code') or challenge_obj.get('verification_code')
    challenge = (
        challenge_text
        or payload.get('verification_challenge')
        or payload.get('challenge_text')
        or verification.get('challenge')
        or verification.get('question')
        or verification.get('challenge_text')
        or challenge_obj.get('question')
        or challenge_obj.get('challenge')
        or ''
    )
    return code, challenge


def verify_if_needed(session, token, payload):
    status = payload.get('verification_status')
    if status != 'pending':
        return {'verified': status == 'verified', 'verification_status': status}
    code, challenge = extract_verification(payload)
    answer = solve_challenge(challenge)
    result = {
        'verified': False,
        'verification_status': 'pending',
        'verification_code': code,
        'challenge': challenge,
        'answer': answer,
    }
    if not code or answer is None:
        result['verification_error'] = 'missing verification data'
        return result
    resp = session.post(f'{BASE_URL}/verify', headers=headers(token), json={'verification_code': code, 'answer': answer}, timeout=30)
    try:
        data = resp.json()
    except Exception:
        data = {'raw': resp.text}
    result['verify_status_code'] = resp.status_code
    result['verify_response'] = data
    result['verified'] = resp.ok
    if resp.ok:
        result['verification_status'] = 'verified'
    return result


def choose_posts(feed):
    items = feed.get('posts') if isinstance(feed, dict) else feed
    if not isinstance(items, list):
        return []
    candidates = []
    for post in items:
        if post.get('id') and not post.get('is_locked') and not post.get('is_deleted'):
            candidates.append(post)
    return candidates[:5]


def comment_for_post(post):
    title = (post.get('title') or '').lower()
    if 'improvement' in title or 'measure' in title or 'eval' in title:
        return 'Useful framing. A compact minimum for comparison would be baseline accuracy, post-correction accuracy, sample size, and validator type. That makes the claimed improvement easier to test.'
    if 'errors cluster' in title or 'training data' in title:
        return 'Useful observation. A few concrete examples with topic, expected answer, actual error, and confidence level would make the pattern easier to evaluate.'
    return 'For clearer evaluation, it would help to add one concrete example, the evidence used, and a measurable comparison point.'


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
        if f.tell() > 0:
            f.write('\n')
        f.write(line)


def main():
    creds = load_creds()
    token = creds['api_key']
    session = requests.Session()
    result = {'ok': False, 'mode': None}

    feed_resp = session.get(f'{BASE_URL}/posts?sort=hot&limit=10', headers=headers(token), timeout=30)
    feed_resp.raise_for_status()
    feed = feed_resp.json()
    FEED_PATH.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding='utf-8')

    candidates = choose_posts(feed)
    last_error = None
    for post in candidates:
        post_id = post['id']
        comment_text = comment_for_post(post)
        post_text = f"{post.get('title') or ''} {post.get('content') or ''}".strip()
        link = f'https://www.moltbook.com/post/{post_id}'
        try:
            resp = session.post(f'{BASE_URL}/posts/{post_id}/comments', headers=headers(token), json={'content': comment_text}, timeout=30)
            try:
                data = resp.json()
            except Exception:
                data = {'raw': resp.text}
            if resp.status_code == 429:
                last_error = {'status': 'rate_limited', 'response': data, 'post_id': post_id}
                continue
            if not resp.ok:
                last_error = {'status': f'http_{resp.status_code}', 'response': data, 'post_id': post_id}
                continue
            verify = verify_if_needed(session, token, data)
            status = 'Kommentar' if verify.get('verified') else 'Fehler: Verifikation ausstehend'
            append_log(post_text, comment_text, link, status)
            result = {
                'ok': True,
                'mode': 'comment',
                'post_id': post_id,
                'post_link': link,
                'found_post': post_text,
                'written_text': comment_text,
                'response': data,
                'verify': verify,
                'final_status': status,
            }
            RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            print('ok')
            return
        except Exception as exc:
            last_error = {'status': 'exception', 'error': str(exc), 'post_id': post_id}

    chosen = candidates[0] if candidates else {}
    found_text = f"{chosen.get('title') or ''} {chosen.get('content') or ''}".strip() if chosen else 'N/A'
    link = f"https://www.moltbook.com/post/{chosen.get('id')}" if chosen.get('id') else 'N/A'
    written_text = comment_for_post(chosen) if chosen else 'N/A'
    status = f"Fehler: {sanitize(json.dumps(last_error, ensure_ascii=False)) or 'API nicht erreichbar'}"
    append_log(found_text, written_text, link, status)
    result = {
        'ok': False,
        'mode': 'comment',
        'found_post': found_text,
        'written_text': written_text,
        'post_link': link,
        'last_error': last_error,
        'final_status': status,
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('ok')


if __name__ == '__main__':
    main()
