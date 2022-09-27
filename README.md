# Helix Perforce Proxy - Cache 

[helix-p4p](https://www.perforce.com/manuals/p4dist/Content/P4Dist/chapter.proxy.html) is a proxy cache for Perforce servers.

## Flush

As revisions are added to files within the proxy, there is no internal cache expiry performed.
Thus, a proxy server can retain excessive amounts of cached file revisions.

p4p-flush allows sysadmins to periodically expire content.


```
usage: p4p-flush [-h] [--ttl TTL] [--min-vers MIN_VERS] [--purge] path

Flush helix-p4p cache

positional arguments:
  path

options:
  -h, --help           show this help message and exit
  --ttl TTL            Expiry time (hours)
  --min-vers MIN_VERS  Number of revisions to keep
  --purge              Remove expired items from disk
```

## TODO

- Humanize file size outputs, such that automatic care is taken betwen bytes/MB/GB.
- Read in argparse config variables from the environment.
- Expand on test cases, expressing more edge cases.
- Add Systemd scripts for configuration & running.
