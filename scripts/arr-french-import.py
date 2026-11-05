#!/usr/bin/env python3
# Radarr / Sonarr French-audio import fixer (2026-11-04, Sonarr added 2026-11-05).
# The arrs re-score a finished download from its file names only. When the uploader renamed the files ("brave.mkv",
# "dark-s02e01.mkv"), the MULTi / VFF info the tracker had is gone, so the arr refuses them as "not an upgrade" or
# blocks them for manual import, although they were grabbed precisely for their French audio.
# Every run: for each finished but not imported download, read the real audio tracks with ffprobe. If the files have
# French (plus the original language), and the release scored better at grab time than the current files, import
# them with the real languages. Everything else is left alone (Cleanuparr's failed-import rule deals with it).
# Usage: arr-french-import.py [--dry-run]
import json, os, re, subprocess, sys, time, urllib.request, urllib.parse

DRY = '--dry-run' in sys.argv
APPS = {
    'radarr': (os.environ.get('RADARR_URL', 'http://radarr:7878'), os.environ.get('RADARR_CONFIG', '/radarr/config.xml')),
    'sonarr': (os.environ.get('SONARR_URL', 'http://sonarr:8989'), os.environ.get('SONARR_CONFIG', '/sonarr/config.xml')),
}
MIN_VIDEO = {'radarr': 300e6, 'sonarr': 50e6}  # smaller files are samples / extras

# ISO 639-2 audio tags -> arr language names
ISO = {'eng': 'English', 'fre': 'French', 'fra': 'French', 'ger': 'German', 'deu': 'German', 'spa': 'Spanish',
       'ita': 'Italian', 'jpn': 'Japanese', 'kor': 'Korean', 'chi': 'Chinese', 'zho': 'Chinese', 'cmn': 'Chinese',
       'rus': 'Russian', 'por': 'Portuguese', 'dut': 'Dutch', 'nld': 'Dutch', 'dan': 'Danish', 'swe': 'Swedish',
       'nor': 'Norwegian', 'nob': 'Norwegian', 'fin': 'Finnish', 'pol': 'Polish', 'cze': 'Czech', 'ces': 'Czech',
       'hun': 'Hungarian', 'gre': 'Greek', 'ell': 'Greek', 'tur': 'Turkish', 'ara': 'Arabic', 'arb': 'Arabic',
       'heb': 'Hebrew', 'hin': 'Hindi', 'tha': 'Thai', 'ukr': 'Ukrainian', 'vie': 'Vietnamese', 'per': 'Persian',
       'fas': 'Persian', 'ice': 'Icelandic', 'isl': 'Icelandic', 'rum': 'Romanian', 'ron': 'Romanian'}
FRENCH_TITLE = re.compile(r'\b(VFF|VFQ|VF2|VFI|VOF|VF|TRUEFRENCH|FRENCH|Fran[cç]ais|FR)\b', re.I)


class Arr:
    def __init__(self, app):
        url, config = APPS[app]
        self.app, self.base = app, url + '/api/v3/'
        self.key = re.search(r'<ApiKey>([^<]+)', open(config).read()).group(1)

    def call(self, method, path, body=None):
        r = urllib.request.Request(self.base + path, method=method,
                                   data=json.dumps(body).encode() if body is not None else None,
                                   headers={'X-Api-Key': self.key, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(r, timeout=300) as resp:
            t = resp.read()
            return json.loads(t) if t else None

    def run_command(self, body):
        cmd = self.call('POST', 'command', body)
        for _ in range(90):
            time.sleep(10)
            cmd = self.call('GET', f"command/{cmd['id']}")
            if cmd['status'] in ('completed', 'failed'):
                break
        print(f"       -> {cmd['status']}: {cmd.get('message')}")


def audio_languages(path):
    """Language names of the audio tracks; untagged tracks count as 'und' unless their title says French."""
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream_tags=language,title',
                          '-of', 'json', path], capture_output=True, text=True, timeout=300)
    langs = []
    for s in json.loads(out.stdout or '{}').get('streams', []):
        tags = {k.lower(): v for k, v in (s.get('tags') or {}).items()}
        code = (tags.get('language') or 'und').lower()
        if code in ISO:
            langs.append(ISO[code])
        elif FRENCH_TITLE.search(tags.get('title') or ''):
            langs.append('French')
        else:
            langs.append('und')
    return langs


def french_problem(langs, original):
    """None when the tracks are French + original language, else why not."""
    if 'French' not in langs:
        return f'no French audio track {langs}'
    if original != 'French' and original not in langs and 'und' not in langs:
        return f'original language {original} missing {langs}'
    return None


def import_languages(langs, original, known):
    keep = []
    for n in langs:
        n = original if n == 'und' and original in known else n
        if n in known and n not in keep:
            keep.append(n)
    return [{'id': known[n]['id'], 'name': n} for n in keep]


def stuck_downloads(arr, include):
    seen, out = set(), []
    for q in arr.call('GET', f'queue?pageSize=1000&{include}=true')['records']:
        if q.get('status') == 'completed' and q.get('trackedDownloadState') in ('importPending', 'importBlocked') \
                and q.get('downloadId') and q['downloadId'] not in seen:
            seen.add(q['downloadId'])
            out.append(q)
    return out


def preview(arr, q):
    files = arr.call('GET', 'manualimport?' + urllib.parse.urlencode({'downloadId': q['downloadId'], 'filterExistingFiles': 'false'}))
    return [p for p in files if p.get('size', 0) >= MIN_VIDEO[arr.app]]


def radarr():
    arr = Arr('radarr')
    known = {l['name']: l for l in arr.call('GET', 'language')}
    for q in stuck_downloads(arr, 'includeMovie'):
        if not q.get('movieId'):
            continue
        movie = q['movie']
        name = f"{movie['title']} ({movie.get('year')})"
        def skip(why):
            print(f"skip   radarr {name}: {why} | {q['title'][:80]}")
        files = preview(arr, q)
        if len(files) != 1:
            skip(f'{len(files)} video files, needs a human'); continue
        f = files[0]
        quality = f.get('quality') if (f.get('quality') or {}).get('quality') else q['quality']
        if quality['quality']['name'] == 'BR-DISK' or f['path'].lower().endswith('.iso'):
            skip('disc image, Plex cannot play it'); continue
        if not os.path.exists(f['path']):
            skip(f"file not visible here: {f['path']}"); continue
        langs = audio_languages(f['path'])
        original = (movie.get('originalLanguage') or {}).get('name')
        problem = french_problem(langs, original)
        if problem:
            skip(problem); continue
        grabs = [h for h in arr.call('GET', f"history/movie?movieId={q['movieId']}")
                 if h['eventType'] == 'grabbed' and h.get('downloadId') == q['downloadId']]
        if not grabs:
            skip('no grab in history'); continue
        grab_score = grabs[0].get('customFormatScore', 0)
        current = arr.call('GET', f"moviefile?movieId={q['movieId']}")
        current_score = max((m.get('customFormatScore', 0) for m in current), default=None)
        if current_score is not None and grab_score <= current_score:
            skip(f'grab score {grab_score} not above current file {current_score}'); continue
        print(f"{'WOULD import' if DRY else 'import'} radarr {name}: audio {langs}, grab score {grab_score} > current {current_score} | {f['path']}")
        if not DRY:
            arr.run_command({'name': 'ManualImport', 'importMode': 'auto', 'files': [{
                'path': f['path'], 'movieId': q['movieId'], 'downloadId': q['downloadId'], 'quality': quality,
                'languages': import_languages(langs, original, known),
                'releaseGroup': f.get('releaseGroup') or '', 'indexerFlags': 0}]})


def sonarr():
    arr = Arr('sonarr')
    known = {l['name']: l for l in arr.call('GET', 'language')}
    for q in stuck_downloads(arr, 'includeSeries'):
        if not q.get('seriesId'):
            continue
        series = q['series']
        name = series['title']
        def skip(why):
            print(f"skip   sonarr {name}: {why} | {q['title'][:80]}")
        files = preview(arr, q)
        if not files:
            skip('no video file'); continue
        if any(not f.get('episodes') for f in files):
            skip('some files not matched to episodes, needs a human'); continue
        if any(not os.path.exists(f['path']) for f in files):
            skip('files not visible here'); continue
        original = (series.get('originalLanguage') or {}).get('name')
        probed = {f['path']: audio_languages(f['path']) for f in files}
        problems = {p for p in (french_problem(l, original) for l in probed.values()) if p}
        if problems:
            skip('; '.join(sorted(problems))[:200]); continue
        grabs = [h for h in arr.call('GET', f"history/series?seriesId={q['seriesId']}")
                 if h['eventType'] == 'grabbed' and h.get('downloadId') == q['downloadId']]
        if not grabs:
            skip('no grab in history'); continue
        grab_score = max(h.get('customFormatScore', 0) for h in grabs)
        scores = {e['id']: e.get('customFormatScore', 0) for e in arr.call('GET', f"episodefile?seriesId={q['seriesId']}")}
        todo = []
        for f in files:
            current = [scores[e['episodeFileId']] for e in f['episodes'] if e.get('episodeFileId') in scores]
            if not current or grab_score > max(current):
                todo.append(f)
        if not todo:
            skip(f'grab score {grab_score} not above the current files'); continue
        print(f"{'WOULD import' if DRY else 'import'} sonarr {name}: {len(todo)}/{len(files)} files, audio {probed[todo[0]['path']]}, grab score {grab_score} | {q['title'][:70]}")
        if not DRY:
            arr.run_command({'name': 'ManualImport', 'importMode': 'auto', 'files': [{
                'path': f['path'], 'seriesId': q['seriesId'], 'episodeIds': [e['id'] for e in f['episodes']],
                'downloadId': q['downloadId'],
                'quality': f['quality'] if (f.get('quality') or {}).get('quality') else q['quality'],
                'languages': import_languages(probed[f['path']], original, known),
                'releaseGroup': f.get('releaseGroup') or '', 'releaseType': f.get('releaseType') or 'unknown',
                'indexerFlags': 0} for f in todo]})


if __name__ == '__main__':
    print(time.strftime('%F %T'), 'run' + (' (dry run)' if DRY else ''))
    for job in (radarr, sonarr):
        try:
            job()
        except Exception as e:  # one arr down must not stop the other
            print(f'{job.__name__} failed: {type(e).__name__}: {e}')
