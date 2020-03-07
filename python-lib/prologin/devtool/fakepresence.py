import time
import argparse

from prologin.presencesync.client import connect

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('login', help="Logged-in username")
    p.add_argument(
        'hostname', help="Machine hostname on which the user is logged-in"
    )

    args = p.parse_args()

    presence = connect(publish=True)
    print(f"Faking presence of {args.login} on {args.hostname}. ^C to quit.")

    while True:
        presence.send_heartbeat(args.login, args.hostname)
        time.sleep(4)
