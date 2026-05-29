#!/usr/bin/env python3
"""
VPN Bridge Server — runs as a systemd service OUTSIDE the web server's
sandboxed mount namespace.  It listens on a Unix socket and executes
bash / python commands on behalf of the PHP web panel.
"""

import socket, subprocess, base64, os, json, sys, signal, logging

SOCK_PATH = '/tmp/vpn-bridge.sock'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [vpn-bridge] %(levelname)s %(message)s'
)

ENV = {
    **os.environ,
    'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/bin/kyt',
    'TERM': 'xterm',
    'HOME': '/root',
}


def handle(raw_data):
    try:
        req = json.loads(raw_data)
        cmd_b64 = req.get('cmd', '')
        mode = req.get('mode', 'bash')
        stdin_b64 = req.get('stdin', '')

        cmd = base64.b64decode(cmd_b64).decode('utf-8', errors='replace')
        stdin_data = base64.b64decode(stdin_b64).decode('utf-8', errors='replace') if stdin_b64 else None

        logging.info("mode=%s cmd=%s", mode, cmd[:200])

        if mode == 'python':
            proc = subprocess.run(
                ['/usr/bin/kyt/.venv/bin/python', '-c', cmd],
                capture_output=True, text=True, timeout=60,
                input=stdin_data,
                env=ENV,
            )
        else:
            proc = subprocess.run(
                ['bash', '-c', cmd],
                capture_output=True, text=True, timeout=180,
                input=stdin_data,
                env=ENV,
            )

        logging.info("rc=%d stdout=%s", proc.returncode, (proc.stdout or '')[:200])
        if proc.stderr:
            logging.info("stderr=%s", proc.stderr[:200])

        return json.dumps({
            'rc': proc.returncode,
            'stdout': proc.stdout or '',
            'stderr': proc.stderr or '',
        })

    except subprocess.TimeoutExpired:
        return json.dumps({'rc': 124, 'stdout': '', 'stderr': 'Command timed out'})
    except Exception as e:
        logging.exception("handle error")
        return json.dumps({'rc': -1, 'stdout': '', 'stderr': str(e)})


def main():
    # Clean up old socket
    if os.path.exists(SOCK_PATH):
        os.unlink(SOCK_PATH)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCK_PATH)
    os.chmod(SOCK_PATH, 0o777)  # Allow www-data to connect
    server.listen(5)
    server.settimeout(None)

    logging.info("VPN Bridge listening on %s", SOCK_PATH)

    def cleanup(signum, frame):
        logging.info("Shutting down...")
        server.close()
        if os.path.exists(SOCK_PATH):
            os.unlink(SOCK_PATH)
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    while True:
        try:
            conn, _ = server.accept()
        except OSError:
            break

        try:
            # Read all data from client (client shuts down write end when done)
            chunks = []
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b''.join(chunks).decode('utf-8', errors='replace')

            # Process and send response
            result = handle(raw)
            conn.sendall(result.encode('utf-8'))
        except Exception as e:
            logging.exception("connection error")
            try:
                conn.sendall(json.dumps({'rc': -1, 'stdout': '', 'stderr': str(e)}).encode())
            except:
                pass
        finally:
            try:
                conn.close()
            except:
                pass


if __name__ == '__main__':
    main()
