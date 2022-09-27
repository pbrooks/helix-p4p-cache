from argparse import ArgumentParser as ArgParse
from itertools import islice
import logging as log
from pathlib import Path
from time import time

MB = 1024 * 1024
GB = 1024 * MB


def get_args():
    parser = ArgParse(description="Flush helix-p4p cache")
    parser.add_argument("path", type=Path)
    parser.add_argument("--ttl", type=int, default=0*24,
                        help="Expiry time (hours)"),
    parser.add_argument("--min-vers", type=int, default=1,
                        help="Number of revisions to keep")
    parser.add_argument("--purge", action="store_true",
                        help="Remove expired items from disk"
                        )
    '''
    parser.add_argument("--quiet", action="store_true", default=False,
                        help="Suppress file output")
    parser.add_argument("--summary", action="store_true", default=True,
                        help="Show operation summary")
    parser.add_argument("--human", action="store_true", default=True,
                        help="Output file sizes in human readable formats")
    '''
    return parser.parse_args()


def find_files(path):
    if not path.exists():
        raise ValueError("Path {} doesn't exist".format(path))
    if not path.is_dir():
        raise ValueError("Path {} is not a directory".format(path))

    pattern = "**/*,d"
    return path.glob(pattern)


def filter_expired(files, ttl, min_vers):
    older_than = time() - ttl * 60 * 60
    return filter(lambda x: x[1], (
        (record, [(a, a.name[2:], a.stat().st_size) for a in
         filter(lambda y: y.stat().st_ctime < older_than,
                islice(sorted(record.iterdir(), reverse=True),
                       min_vers, None)
                )
         ])
        for record in files
        )
    )


def process(path, items, purge):
    # XXX: Potentially replace with file count
    found = False

    total = 0
    for item in items:
        path_total = sum([x[2] for x in item[1]])
        total += path_total
        if purge:
            for x in item[1]:
                x[0].unlink()
        log.info("%s%s %.2fMB [%s]",
                 "Purged " if purge else "",
                 item[0].relative_to(path), path_total / MB,
                 ", ".join(["r{}: {:.2f}MB".format(x[1], x[2]/MB)
                            for x in item[1]]))
        found = True

    if not found:
        log.warning("No cache files found.")
    else:
        log.info("{}Total: {:.2f}MB".format(
            "Purge " if purge else "",
            total/MB))


def __main__():
    args = get_args()
    log.basicConfig(level=log.INFO)
    path = Path(args.path)
    try:
        process(path, filter_expired(find_files(Path(args.path)),
                                     args.ttl, args.min_vers),
                args.purge)
    except ValueError as ex:
        import sys
        sys.stderr.write(str(ex))
        sys.exit(2)
