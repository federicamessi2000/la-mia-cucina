"""Promemoria del congelatore: la sera prima, alle 19 a Zurigo, una notifica a chi l'ha attivata nel profilo
(users/<uid>/push/<id>), con i piatti "dal freezer" di pranzo e cena del giorno dopo: dal planner personale,
o da quello di famiglia per chi ha un codice famiglia.

Gira su GitHub (.github/workflows/freezer-reminder.yml) alle 17 e alle 18 UTC: alle 19 di Zurigo d'estate la
prima, d'inverno la seconda. Manda una volta per sera (reminderLog/<data>) e solo tra le 19 e le 22, così un
ritardo di GitHub non fa saltare il promemoria. Lanciato a mano con "force" manda subito (per provare) e non
segna la sera come fatta.

I log di un repo pubblico li vedono tutti: qui si stampano solo numeri, niente nomi, piatti o indirizzi.
Segreti: FIREBASE_SERVICE_ACCOUNT (JSON della chiave), VAPID_PRIVATE_KEY (chiave privata delle notifiche).
"""

import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DB_URL = 'https://la-mia-cucina-48a48-default-rtdb.europe-west1.firebasedatabase.app'
APP_URL = 'https://federicamessi2000.github.io/la-mia-cucina/'
TZ = ZoneInfo('Europe/Zurich')
MEALS = ('pranzo', 'cena')
MAX_DISHES = 6  # come in index.html: pranzo, pranzo2 … pranzo6 (idem cena)
TTL = 4 * 3600  # un telefono spento la riceve fino alle 23 circa; dopo non serve più

# Stesse parole dell'app (planner.lunch / planner.dinner in i18n.js)
TEXTS = {
    'it': {
        'title': '🧊 Domani dal congelatore', 'pranzo': 'Pranzo', 'cena': 'Cena',
        'some': 'qualcosa dal congelatore',
        'tail1': 'Da tirare fuori stasera per scongelare.', 'tailN': 'Da tirare fuori stasera per scongelare.',
    },
    'en': {
        'title': '🧊 Tomorrow from the freezer', 'pranzo': 'Lunch', 'cena': 'Dinner',
        'some': 'something from the freezer',
        'tail1': 'Take it out tonight to thaw.', 'tailN': 'Take them out tonight to thaw.',
    },
    'de': {
        'title': '🧊 Morgen aus dem Tiefkühler', 'pranzo': 'Mittag', 'cena': 'Abend',
        'some': 'etwas aus dem Tiefkühler',
        'tail1': 'Heute Abend zum Auftauen herausnehmen.', 'tailN': 'Heute Abend zum Auftauen herausnehmen.',
    },
}


def planner_key(d):
    """Chiave di un giorno nel planner, come in index.html: 'AAAA-M-G' senza zeri davanti."""
    return f'{d.year}-{d.month}-{d.day}'


def freezer_dishes(day):
    """[(pasto, nome o None)] dei piatti "dal freezer" di un giorno del planner."""
    day = day if isinstance(day, dict) else {}
    out = []
    for meal in MEALS:
        for n in range(1, MAX_DISHES + 1):
            slot = meal if n == 1 else f'{meal}{n}'
            if day.get(slot) == '__dal_freezer':
                name = str(day.get(slot + '_freezer_name') or '').strip()
                out.append((meal, name or None))
    return out


def message(dishes, lang, day_key):
    """Testo della notifica nella lingua dell'app di chi la riceve."""
    t = TEXTS.get(lang) or TEXTS['it']
    lines = []
    for meal in MEALS:
        names = [n or t['some'] for m, n in dishes if m == meal]
        if names:
            lines.append(f"{t[meal]}: {', '.join(names)}")
    lines.append(t['tail1'] if len(dishes) == 1 else t['tailN'])
    # tag uguale per la stessa sera: una notifica sola, anche se arrivasse due volte
    return {'title': t['title'], 'body': '\n'.join(lines), 'tag': 'freezer-' + day_key, 'url': APP_URL}


def is_time(now):
    """Tra le 19 e le 22 a Zurigo."""
    return 19 <= now.hour < 22


def valid_sub(sub):
    if not isinstance(sub, dict) or not isinstance(sub.get('endpoint'), str):
        return False
    keys = sub.get('keys')
    return isinstance(keys, dict) and bool(keys.get('p256dh')) and bool(keys.get('auth'))


def main(now=None):
    force = os.environ.get('FORCE', '').strip().lower() == 'true'
    now = now or datetime.now(TZ)
    if not force and not is_time(now):
        print(f'A Zurigo sono le {now:%H:%M}: i promemoria partono tra le 19 e le 22.')
        return

    import firebase_admin
    from firebase_admin import credentials, db
    from pywebpush import WebPushException, webpush

    if not firebase_admin._apps:
        firebase_admin.initialize_app(
            credentials.Certificate(json.loads(os.environ['FIREBASE_SERVICE_ACCOUNT'])), {'databaseURL': DB_URL})
    log = db.reference('reminderLog/' + now.date().isoformat())
    if not force and log.get():
        print('Il promemoria di stasera è già partito.')
        return

    key = os.environ['VAPID_PRIVATE_KEY'].strip()
    tomorrow = planner_key((now + timedelta(days=1)).date())
    people = sent = gone = failed = 0
    for uid in db.reference('users').get(shallow=True) or {}:
        subs = db.reference(f'users/{uid}/push').get()
        if not isinstance(subs, dict) or not subs:
            continue
        code = db.reference(f'users/{uid}/familyCode').get()
        base = f'families/{code}' if code else f'users/{uid}'
        dishes = freezer_dishes(db.reference(f'{base}/planner/{tomorrow}').get())
        if not dishes:
            continue
        people += 1
        for sid, sub in subs.items():
            if not valid_sub(sub):
                continue
            try:
                webpush(
                    subscription_info={'endpoint': sub['endpoint'], 'keys': sub['keys']},
                    data=json.dumps(message(dishes, sub.get('lang'), tomorrow)),
                    vapid_private_key=key,
                    # Apple vuole un contatto (https o mailto) e una scadenza entro 24 ore
                    vapid_claims={'sub': APP_URL, 'exp': int(time.time()) + 12 * 3600},
                    ttl=TTL,
                )
                sent += 1
            except WebPushException as e:
                status = getattr(getattr(e, 'response', None), 'status_code', None)
                if status in (404, 410):  # quel telefono non è più iscritto: si toglie
                    db.reference(f'users/{uid}/push/{sid}').delete()
                    gone += 1
                else:
                    failed += 1
                    print(f'Una notifica non è partita (stato {status}).')
    if not force:
        log.set({'sent': sent, 'at': now.isoformat(timespec='seconds')})
    print(f'Promemoria: {people} persone con piatti dal congelatore domani, {sent} notifiche mandate, '
          f'{gone} iscrizioni scadute tolte, {failed} non partite.')


if __name__ == '__main__':
    main()
