#!/usr/bin/env python3
# Radarr French-audio import fixer (2026-11-04).
# Radarr re-scores a finished download from its file name only. When the uploader renamed the file ("brave.mkv"),
# the MULTi / VFF info the tracker had is gone, so Radarr refuses the file as "not an upgrade" or blocks it for
# manual import, although it was grabbed precisely for its French audio.
# Every run: for each finished but not imported movie, read the real audio tracks with ffprobe. If the file has
# French (plus the original language), and the release scored better at grab time than the current file, import
# it with the real languages. Everything else is left alone (Cleanuparr's failed-import rule deals with it).
# Usage: radarr-french-import.py [--dry-run]
import json, os, re, subprocess, sys, time, urllib.request, urllib.parse

DRY = '--dry-run' in sys.argv
KEY = re.search(r'<ApiKey>([^<]+)', open(os.environ.get('RADARR_CONFIG', '/radarr/config.xml')).read()).group(1)
B = os.environ.get('RADARR_URL', 'http://radarr:7878') + '/api/v3/'
MIN_VIDEO = 300e6  # smaller files are samples / extras

# ISO 639-2 audio tags -> Radarr language names
ISO = {'eng': 'English', 'fre': 'French', 'fra': 'French', 'ger': 'German', 'deu': 'German', 'spa': 'Spanish',
       'ita': 'Italian', 'jpn': 'Japanese', 'kor': 'Korean', 'chi': 'Chinese', 'zho': 'Chinese', 'cmn': 'Chinese',
       'rus': 'Russian', 'por': 'Portuguese', 'dut': 'Dutch', 'nld': 'Dutch', 'dan': 'Danish', 'swe': 'Swedish',
       'nor': 'Norwegian', 'nob': 'Norwegian', 'fin': 'Finnish', 'pol': 'Polish', 'cze': 'Czech', 'ces': 'Czech',
       'hun': 'Hungarian', 'gre': 'Greek', 'ell': 'Greek', 'tur': 'Turkish', 'ara': 'Arabic', 'arb': 'Arabic',
       'heb': 'Hebrew', 'hin': 'Hindi', 'tha': 'Thai', 'ukr': 'Ukrainian', 'vie': 'Vietnamese', 'per': 'Persian',
       'fas': 'Persian', 'ice': 'Icelandic', 'isl': 'Icelandic', 'rum': 'Romanian', 'ron': 'Romanian'}
FRENCH_TITLE = re.compile(r'\b(VFF|VFQ|VF2|VFI|VOF|VF|TRUEFRENCH|FRENCH|Fran[cç]ais|FR)\b', re.I)


def call(method, path, body=None):
    r = urllib.request.Request(B + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                               headers={'X-Api-Key': KEY, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(r, timeout=300) as resp:
        t = resp.read()
        return json.loads(t) if t else None


def audio_languages(path):
    """Radarr language names of the audio tracks; untagged tracks count as 'und' unless their title says French."""
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


def main():
    radarr_langs = {l['name']: l for l in call('GET', 'language')}
    queue = call('GET', 'queue?pageSize=1000&includeMovie=true')['records']
    stuck = [q for q in queue if q.get('status') == 'completed' and q.get('movieId')
             and q.get('trackedDownloadState') in ('importPending', 'importBlocked')]
    for q in stuck:
        movie = q['movie']
        name = f"{movie['title']} ({movie.get('year')})"
        def skip(why):
            print(f"skip   {name}: {why} | {q['title'][:80]}")
        files = [p for p in call('GET', 'manualimport?' + urllib.parse.urlencode({'downloadId': q['downloadId'], 'filterExistingFiles': 'false'}))
                 if p.get('size', 0) >= MIN_VIDEO]
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
        if 'French' not in langs:
            skip(f'no French audio track {langs}'); continue
        if original != 'French' and original not in langs and 'und' not in langs:
            skip(f'original language {original} missing {langs}'); continue
        grabs = [h for h in call('GET', f"history/movie?movieId={q['movieId']}")
                 if h['eventType'] == 'grabbed' and h.get('downloadId') == q['downloadId']]
        grab_score = grabs[0].get('customFormatScore', 0) if grabs else None
        current = call('GET', f"moviefile?movieId={q['movieId']}")
        current_score = max((m.get('customFormatScore', 0) for m in current), default=None)
        if grab_score is None:
            skip('no grab in history'); continue
        if current_score is not None and grab_score <= current_score:
            skip(f'grab score {grab_score} not above current file {current_score}'); continue
        keep = []
        for n in langs:
            n = original if n == 'und' and original in radarr_langs else n
            if n in radarr_langs and n not in keep:
                keep.append(n)
        print(f"{'WOULD import' if DRY else 'import'} {name}: audio {langs}, grab score {grab_score} > current {current_score} | {f['path']}")
        if DRY:
            continue
        cmd = call('POST', 'command', {'name': 'ManualImport', 'importMode': 'auto', 'files': [{
            'path': f['path'], 'movieId': q['movieId'], 'downloadId': q['downloadId'], 'quality': quality,
            'languages': [{'id': radarr_langs[n]['id'], 'name': n} for n in keep],
            'releaseGroup': f.get('releaseGroup') or '', 'indexerFlags': 0}]})
        for _ in range(90):
            time.sleep(10)
            cmd = call('GET', f"command/{cmd['id']}")
            if cmd['status'] in ('completed', 'failed'):
                break
        print(f"       -> {cmd['status']}: {cmd.get('message')}")


if __name__ == '__main__':
    print(time.strftime('%F %T'), 'run' + (' (dry run)' if DRY else ''))
    main()
