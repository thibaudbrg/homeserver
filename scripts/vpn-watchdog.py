#!/usr/bin/env python3
# VPN watchdog for gluetun + qBittorrent (2026-11-05).
# PIA sometimes forgets the WireGuard key it registered for us (2026-11-04 21:20: server still up, but gluetun
# retried every 6 s for 13 h and qBittorrent sat offline while Docker still showed gluetun "healthy").
# Every run: read gluetun's last minutes of log. If the tunnel keeps failing its checks and never came back up,
# register a new key (pia-wg-setup.py, same server), restart gluetun, then qBittorrent (it lives in gluetun's
# network). If a renewal less than an hour ago did not help, try another server once. Reports on Telegram.
# Usage: vpn-watchdog.py [--dry-run] [--force]   (--force: act as if the tunnel were down, to test the repair)
import json, os, re, subprocess, sys, time, urllib.request, urllib.parse

DRY = '--dry-run' in sys.argv
FORCE = '--force' in sys.argv
DOCKER = os.environ.get('DOCKER_HOST', 'tcp://socket-proxy:2375').replace('tcp://', 'http://')
WG_DIR = os.environ.get('PIA_WG_DIR', '/wireguard')
STATE = os.path.join(WG_DIR, 'watchdog.json')
SETUP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pia-wg-setup.py')
WINDOW = 300     # seconds of log looked at
MIN_FAILS = 10   # gluetun retries every ~6 s, so 10 failures = down for a minute or more without recovering
FAIL = re.compile(r'restarting VPN because it failed to pass the healthcheck')
UP = re.compile(r'Public IP address is')


def docker(method, path, timeout=60):
    r = urllib.request.Request(DOCKER + path, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return resp.read()


def logs(since):
    raw = docker('GET', f'/containers/gluetun/logs?stdout=1&stderr=1&since={int(since)}')
    return raw.decode('utf-8', 'replace').splitlines()


def notify(text):
    print(text)
    tok, chat = os.environ.get('TGRAM_BOT_TOKEN'), os.environ.get('TGRAM_CHAT_ID')
    if DRY or not tok or not chat:
        return
    try:
        data = urllib.parse.urlencode({'chat_id': chat, 'text': 'VPN watchdog: ' + text}).encode()
        urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/sendMessage', data=data, timeout=30)
    except Exception as e:
        print('telegram failed:', type(e).__name__)


def tunnel_down():
    lines = logs(time.time() - WINDOW)
    fails = [i for i, l in enumerate(lines) if FAIL.search(l)]
    ups = [i for i, l in enumerate(lines) if UP.search(l)]
    return len(fails) >= MIN_FAILS and (not ups or ups[-1] < fails[-1]), len(fails)


def restart_and_wait():
    t = time.time()
    docker('POST', '/containers/gluetun/restart?t=10', timeout=120)
    for _ in range(30):
        time.sleep(5)
        lines = logs(t)
        if any(UP.search(l) for l in lines):
            docker('POST', '/containers/qbittorrent/restart?t=30', timeout=120)
            return True
    return False


def save(state):
    json.dump(state, open(STATE, 'w'))
    if os.geteuid() == 0 and os.environ.get('PUID'):
        os.chown(STATE, int(os.environ['PUID']), int(os.environ.get('PGID', '100')))


def main():
    down, nfails = tunnel_down()
    down = down or FORCE
    if not down:
        print(time.strftime('%F %T'), f'ok ({nfails} failed checks in the last {WINDOW // 60} min)')
        return
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    recent = time.time() - state.get('renewed', 0) < 3600
    if recent and state.get('tries', 0) >= 2:
        if not state.get('gave_up'):
            notify('tunnel still down after a new key and a new server. Needs a human (PIA login? PIA outage?).')
            state['gave_up'] = True
            save(state)
        return
    args = ['--new-server'] if recent else []
    print(time.strftime('%F %T'), f'tunnel down ({nfails} failed checks), renewing the key', *args)
    if DRY:
        return
    out = subprocess.run([sys.executable, SETUP, *args], capture_output=True, text=True, timeout=180)
    print(out.stdout.strip(), out.stderr.strip()[-500:])
    state = {'renewed': time.time(), 'tries': state.get('tries', 0) + 1 if recent else 1}
    save(state)
    if out.returncode != 0:
        notify(f'tunnel down, key renewal failed: {(out.stderr or out.stdout).strip()[-200:]}')
        return
    changed = 'CHANGED' in out.stdout
    if restart_and_wait():
        msg = 'tunnel was down, new PIA key registered, gluetun and qBittorrent restarted, VPN back up.'
        if changed:
            server = re.search(r'server: (\S+)', out.stdout).group(1)
            msg += f' Server changed: set SERVER_NAMES: {server} in compose/qbittorrent.yml (port forwarding off until then).'
        notify(msg)
    else:
        notify('tunnel down, new key registered and gluetun restarted, but it is still not up. Will retry.')


if __name__ == '__main__':
    main()
