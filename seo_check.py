#!/usr/bin/env python3
"""Small, dependency-free SEO checker. Python 3.10+."""
import argparse
import json
import sys
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

MAX_BYTES = 5 * 1024 * 1024


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = []
        self.in_title = False
        self.h1 = 0
        self.images = 0
        self.missing_alt = 0
        self.description = ''
        self.canonical = ''
        self.robots = ''
        self.lang = ''
        self.viewport = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'title':
            self.in_title = True
        elif tag == 'h1':
            self.h1 += 1
        elif tag == 'html':
            self.lang = a.get('lang') or ''
        elif tag == 'img':
            self.images += 1
            # Empty alt is valid for decorative images.
            self.missing_alt += 'alt' not in a
        elif tag == 'meta':
            name = (a.get('name') or '').lower()
            value = a.get('content') or ''
            if name == 'description':
                self.description = value.strip()
            elif name == 'robots':
                self.robots = value
            elif name == 'viewport':
                self.viewport = bool(value)
        elif tag == 'link' and 'canonical' in (a.get('rel') or '').lower().split():
            self.canonical = a.get('href') or ''

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)


def fetch(url):
    request = Request(url, headers={'User-Agent': 'SimpleSEOChecker/1.0'})
    with urlopen(request, timeout=15) as response:
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('Response exceeds 5 MB limit')
        encoding = response.headers.get_content_charset() or 'utf-8'
        return response.status, response.url, response.headers, data.decode(encoding, errors='replace')


def audit(url):
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise ValueError('URL must start with http:// or https:// and contain a hostname')
    status, final_url, headers, html = fetch(url)
    if 'text/html' not in headers.get('Content-Type', '').lower():
        raise ValueError('Target is not an HTML page')
    page = Page()
    page.feed(html)
    checks = []

    def add(name, ok, detail):
        checks.append({'check': name, 'status': 'PASS' if ok else 'WARN', 'detail': detail})

    title = ' '.join(''.join(page.title).split())
    add('HTTP status', status == 200, str(status))
    add('HTTPS', urlsplit(final_url).scheme == 'https', final_url)
    add('Title', bool(title), title or 'Missing title')
    add('Meta description', bool(page.description), page.description or 'Missing description')
    add('H1', page.h1 == 1, f'{page.h1} H1 elements; review page heading structure')
    add('Image alt', page.missing_alt == 0, f'{page.missing_alt}/{page.images} images lack an alt attribute')
    canonical = urljoin(final_url, page.canonical)
    valid_canonical = bool(page.canonical) and urlsplit(canonical).scheme in ('http', 'https') and bool(urlsplit(canonical).hostname)
    add('Canonical', valid_canonical, canonical if page.canonical else 'Missing canonical link')
    add('HTML language', bool(page.lang.strip()), page.lang or 'Missing lang attribute')
    add('Mobile viewport', page.viewport, 'Present' if page.viewport else 'Missing viewport meta tag')
    directives = (page.robots + ',' + headers.get('X-Robots-Tag', '')).lower()
    blocked = 'noindex' in directives or 'none' in directives.replace(',', ' ').split()
    add('Indexing directives', not blocked, directives or 'No explicit noindex directive found')
    for name, path in [('robots.txt', '/robots.txt'), ('sitemap.xml', '/sitemap.xml')]:
        resource = urljoin(final_url, path)
        try:
            code, resolved, resource_headers, body = fetch(resource)
            is_html = 'text/html' in resource_headers.get('Content-Type', '').lower() or body.lstrip().lower().startswith(('<!doctype html', '<html'))
            looks_valid = bool(body.strip()) and not is_html
            if name == 'sitemap.xml':
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(body)
                    looks_valid = looks_valid and root.tag.split('}')[-1] in ('urlset', 'sitemapindex')
                except ET.ParseError:
                    looks_valid = False
            add(name, code == 200 and looks_valid, f'{code} {resolved}; content checked, crawling rules not evaluated')
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            add(name, False, str(exc))
    return {'url': url, 'final_url': final_url, 'checks': checks,
            'warnings': sum(c['status'] == 'WARN' for c in checks)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', nargs='?', default='https://aipctool.com',
                        help='Full URL to inspect (default: https://aipctool.com)')
    parser.add_argument('--json', action='store_true', help='Print JSON')
    args = parser.parse_args()
    try:
        report = audit(args.url)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, LookupError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"SEO check: {report['final_url']}")
        for check in report['checks']:
            print(f"[{check['status']}] {check['check']}: {check['detail']}")
        print(f"Warnings: {report['warnings']}")
    return 1 if report['warnings'] else 0


if __name__ == '__main__':
    sys.exit(main())
