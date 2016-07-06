#! /usr/bin/python
import os
import re
import time
import mmap
import json
import textwrap
from pathlib import Path

import aiohttp
from aiohttp import web

IGNORE_EXTS = {'.pyc', '.pyx', '.bin', '.pak', '.so'}

WD = os.getcwd()


async def ws(request):

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    path = Path('/home/samuel/TutorCruncher2/TutorCruncher').resolve()
    results = search(path, 'foobar')
    ws.send_str(json.dumps(results))

    async for msg in ws:
        if msg.tp == aiohttp.MsgType.text:
            if msg.data == 'close':
                await ws.close()
            else:
                ws.send_str(msg.data + '/answer')
        elif msg.tp == aiohttp.MsgType.error:
            print('ws connection closed with exception %s' %
                  ws.exception())

    print('websocket connection closed')

    return ws


def app(loop):
    a = web.Application(loop=loop)
    a.router.add_route('GET', '/', ws)
    return a


def walk(root: Path):
    def gen(p):
        for _p in p.iterdir():
            if _p.is_dir():
                yield from gen(_p)
            else:
                yield _p.resolve()
    return gen(root)


def search(directory: Path, sstr: str, exclude_filter=None, include_filter=None, extension=None):
    start = time.time()
    exclude = include = None
    if exclude_filter:
        exclude = re.compile(exclude_filter).search

    if include_filter:
        include = re.compile(include_filter).search

    paths = []
    fcount = 0
    for path in walk(directory):
        fcount += 1
        path = path.resolve()
        pstr = str(path)
        if any(pstr.endswith(e) for e in IGNORE_EXTS):
            continue
        if extension and not pstr.endswith(extension):
            continue
        if exclude and exclude(pstr):
            continue
        if include and not include(pstr):
            continue
        paths.append(path.resolve())
    print('%d files filtered' % fcount)
    print('%d matching files' % len(paths))
    print('searching for "%s"' % sstr)
    sbytes = sstr.encode()
    results = []
    for path in paths:
        pstr = str(path)
        size = path.stat().st_size
        if size == 0:
            continue

        file_results = []
        with path.open() as f:
            file_map = bytes(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ))
            if not re.search(sbytes, file_map):
                continue
            try:
                s = f.read()
            except UnicodeDecodeError:
                if size > 5 * 1024 * 1024:
                    continue
                s = path.open('rb').read().decode(errors='replace')
            for i, line in enumerate(s.split('\n')):
                lines_results = []
                line2 = '\n'.join(textwrap.wrap(line.rstrip('\n')[:500], 120))
                m = re.search(sstr, line2)
                while m:
                    s, e = m.start(), m.end()
                    lines_results.append({'bf': line2[:s], 'm': line2[s:e]})
                    line2 = line2[e:]
                    m = re.search(sstr, line2)
                if not lines_results:
                    continue
                file_results.append({
                    'ln': i,
                    'lr': lines_results,
                    'end': line2
                })
        if file_results:
            results.append({'path': pstr, 'file_results': file_results})
    time_taken = time.time() - start
    result_count = sum(len(r['file_results']) for r in results)
    print('%d results found in %0.2fs' % (result_count, time_taken))
    return {
        'results': results,
        'search_term': sstr,
        'result_count': result_count,
        'time_taken': '%0.2fs' % time_taken,
        'files_filtered': fcount,
        'matching_files': len(paths),
        'files_with_results': len(results),
    }
