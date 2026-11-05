#!/usr/bin/env python3
"""Create a PIA WireGuard config for gluetun (custom provider), using the PIA login in the Docker secrets.

Writes /volume2/docker/appdata/gluetun/wireguard/wg0.conf (mode 600, contains the private key, never printed)
and server.txt next to it (server name, IP and port only). Picks the fastest French PIA server that supports
port forwarding, but keeps the current server while PIA lists it. Run again to renew the key:  python3 ~/pia-wg-setup.py
(--new-server picks the fastest server again). scripts/vpn-watchdog.py runs it by itself when the tunnel dies.
"""
import base64, json, os, socket, ssl, sys, time, urllib.parse, urllib.request, uuid
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization

SECRETS = os.environ.get("PIA_SECRETS", "/volume2/docker/secrets")  # /run/secrets in the vpn-watchdog container
OUT = os.environ.get("PIA_WG_DIR", "/volume2/docker/appdata/gluetun/wireguard")
CA_URL = "https://raw.githubusercontent.com/pia-foss/manual-connections/master/ca.rsa.4096.crt"
UA = {"User-Agent": "curl/8.5.0"}  # Cloudflare in front of PIA answers 403 to Python's default User-Agent

user = open(f"{SECRETS}/pia_username").read().strip()
password = open(f"{SECRETS}/pia_password").read().strip()

# 1. login token (multipart form, like PIA's own manual-connections scripts)
boundary = uuid.uuid4().hex
body = "".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in (("username", user), ("password", password)))
body += f"--{boundary}--\r\n"
req = urllib.request.Request("https://www.privateinternetaccess.com/api/client/v2/token", data=body.encode(),
                             headers={"Content-Type": f"multipart/form-data; boundary={boundary}", **UA})
try:
    token = json.load(urllib.request.urlopen(req, timeout=30))["token"]
except Exception as e:
    sys.exit(f"PIA login failed: {e}")
print("PIA login: OK")

# 2. French servers with port forwarding, pick the fastest to reach
raw = urllib.request.urlopen(urllib.request.Request("https://serverlist.piaservers.net/vpninfo/servers/v6", headers=UA), timeout=30).read().decode()
regions = json.loads(raw.split("\n")[0])["regions"]
cands = [(r["name"], s["ip"], s["cn"]) for r in regions if r.get("country") == "FR" and r.get("port_forward") for s in r["servers"].get("wg", [])]
if not cands: sys.exit("No French PIA WireGuard server with port forwarding found")
def rtt(ip):
    t = time.time()
    try:
        socket.create_connection((ip, 1337), timeout=3).close(); return time.time() - t
    except OSError: return 99
current = dict(l.strip().split("=", 1) for l in open(os.path.join(OUT, "server.txt")) if "=" in l).get("SERVER_NAMES") \
    if os.path.exists(os.path.join(OUT, "server.txt")) else None
same = [c for c in cands if c[2] == current and rtt(c[1]) < 99]
if same and "--new-server" not in sys.argv:  # keep the server: SERVER_NAMES in compose/qbittorrent.yml stays valid
    region, ip, cn = same[0]
else:
    region, ip, cn = min(cands, key=lambda c: rtt(c[1]))
print(f"server: {cn} ({region}, {ip}), picked among {len(cands)}" + (" (same as before)" if cn == current else " (CHANGED: update SERVER_NAMES)"))

# 3. new key pair, registered on that server (TLS checked against PIA's CA and the server name)
priv = X25519PrivateKey.generate()
priv_b64 = base64.b64encode(priv.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())).decode()
pub_b64 = base64.b64encode(priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
ca = os.path.join(OUT, "pia-ca.rsa.4096.crt")
os.makedirs(OUT, exist_ok=True)
open(ca, "wb").write(urllib.request.urlopen(urllib.request.Request(CA_URL, headers=UA), timeout=30).read())
ctx = ssl.create_default_context(cafile=ca)
sock = ctx.wrap_socket(socket.create_connection((ip, 1337), timeout=20), server_hostname=cn)
q = urllib.parse.urlencode({"pt": token, "pubkey": pub_b64})
sock.sendall(f"GET /addKey?{q} HTTP/1.1\r\nHost: {cn}\r\nConnection: close\r\n\r\n".encode())
resp = b""
while True:
    chunk = sock.recv(65536)
    if not chunk: break
    resp += chunk
sock.close()
data = json.loads(resp.split(b"\r\n\r\n", 1)[1])
if data.get("status") != "OK":
    sys.exit(f"PIA refused the key: {data.get('status')} {data.get('message', '')}")

# 4. gluetun config (custom provider reads /gluetun/wireguard/wg0.conf)
os.umask(0o077)
conf = (f"[Interface]\nPrivateKey = {priv_b64}\nAddress = {data['peer_ip']}/32\n\n"
        f"[Peer]\nPublicKey = {data['server_key']}\nEndpoint = {data['server_ip']}:{data['server_port']}\nAllowedIPs = 0.0.0.0/0\n")
path = os.path.join(OUT, "wg0.conf")
with open(path + ".tmp", "w") as f: f.write(conf)
os.replace(path + ".tmp", path)
with open(os.path.join(OUT, "server.txt"), "w") as f:
    f.write(f"SERVER_NAMES={cn}\nENDPOINT={data['server_ip']}:{data['server_port']}\nREGION={region}\nCREATED={time.strftime('%Y-%m-%d %H:%M')}\n")
os.chmod(os.path.join(OUT, "server.txt"), 0o644)
if os.geteuid() == 0 and os.environ.get("PUID"):  # run by the watchdog as root: hand the files back to the NAS user
    for n in ("wg0.conf", "server.txt", "pia-ca.rsa.4096.crt"):
        os.chown(os.path.join(OUT, n), int(os.environ["PUID"]), int(os.environ.get("PGID", "100")))
print(f"wrote {path} (600, key not shown) and server.txt. Endpoint {data['server_ip']}:{data['server_port']}")
