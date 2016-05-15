import requests
import sys

API_BASE = 'http://concours/api'


def champion_upload(base, tarball, name, comment):
    s = requests.session()
    # acquire CSRF token
    s.get(base + "/champions")
    try:
        token = s.cookies['csrftoken']
    except KeyError:
        print("Error: could not retrieve CSRF token (no SSO?)", file=sys.stderr)
        return 1
    res = s.post(base + "/champions",
                 data={'name': name, 'comment': comment, 'csrfmiddlewaretoken': token},
                 files={'sources': tarball})
    if not res.ok:
        print("Error", res.json(), file=sys.stderr)
        return 1
    res = res.json()
    print("Your champion {} was uploaded to {} ({})".format(
        res['id'], res['url'], res['status_human'].lower()))
    return 0


def map_get(base, map_id):
    res = requests.get("{}/maps/{}/".format(base, map_id))
    if not res.ok:
        print("Error", res.json(), file=sys.stderr)
        return 1
    print(res.json()['contents'])
    return 0


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Concours API consumer")
    parser.add_argument('--root', default=API_BASE)
    sub = parser.add_subparsers(help="entity")

    champion = sub.add_parser("champion")
    sub_champion = champion.add_subparsers(help="action")
    upload = sub_champion.add_parser("upload")
    upload.add_argument('-n', '--name', help="Champion name")
    upload.add_argument('-c', '--comment', help="Champion comment")
    upload.add_argument('tarball', type=argparse.FileType('rb'))

    map = sub.add_parser("map")
    sub_map = map.add_subparsers(help="action")
    get_map = sub_map.add_parser("get")
    get_map.add_argument('id', type=int, help="map ID")

    args = parser.parse_args()

    if hasattr(args, 'tarball'):
        while not args.name:
            args.name = input("Provide a name for your champion: ").strip()
        ret = champion_upload(args.root, args.tarball, args.name, args.comment)
    elif hasattr(args, 'id'):
        ret = map_get(args.root, args.id)
    else:
        ret = 1
        parser.error("No action provided")

    sys.exit(ret)
