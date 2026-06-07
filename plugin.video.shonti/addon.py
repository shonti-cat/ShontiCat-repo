import sys
import urllib.parse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import requests

ADDON    = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
HANDLE   = int(sys.argv[1])
BASE_URL = sys.argv[0]

def get_settings():
    meta_url   = ADDON.getSetting('meta_url').strip().rstrip('/')
    stream_url = ADDON.getSetting('stream_url').strip().rstrip('/')
    for suffix in ['/manifest.json', 'manifest.json']:
        if meta_url.endswith(suffix):
            meta_url = meta_url[:-len(suffix)]
        if stream_url.endswith(suffix):
            stream_url = stream_url[:-len(suffix)]
    return meta_url, stream_url

def check_settings():
    meta_url, stream_url = get_settings()
    if not meta_url or not stream_url:
        xbmcgui.Dialog().ok('Shonti',
            'נא להגדיר את כתובות AIOMetadata ו-AIOStreams בהגדרות האד-און.')
        ADDON.openSettings()
        return False
    return True

def build_url(query):
    return BASE_URL + '?' + urllib.parse.urlencode(query)

def get_json(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        xbmc.log(f"[Shonti] Error fetching {url}: {e}", xbmc.LOGERROR)
        return None

BASE_CATALOGS = [
    {"id": "tmdb.top",             "type": "movie",  "name": "🎬 סרטים פופולריים",       "extra": "/genre=None"},
    {"id": "tmdb.top",             "type": "series", "name": "📺 סדרות פופולריות",        "extra": "/genre=None"},
    {"id": "tmdb.trending_movie",  "type": "movie",  "name": "🔥 טרנדי — סרטים",         "extra": "/genre=Day"},
    {"id": "tmdb.trending_series", "type": "series", "name": "🔥 טרנדי — סדרות",         "extra": "/genre=Day"},
    {"id": "tmdb.top_rated_movie", "type": "movie",  "name": "⭐ מדורגים גבוה — סרטים",  "extra": "/genre=None"},
    {"id": "tmdb.top_rated_series","type": "series", "name": "⭐ מדורגים גבוה — סדרות",  "extra": "/genre=None"},
    {"id": "tvmaze.schedule",      "type": "series", "name": "📅 לוח שידורים היום",       "extra": "/genre=US"},
]
ISRAEL_CATALOGS = [
    {"id": "custom.org_israeltv_stremio.series.israel_vod_12", "type": "series", "name": "🇮🇱 ערוץ 12 (קשת)", "extra": "/genre=None"},
    {"id": "custom.org_israeltv_stremio.series.israel_vod_13", "type": "series", "name": "🇮🇱 ערוץ 13 (רשת)", "extra": "/genre=None"},
    {"id": "custom.org_israeltv_stremio.series.israel_vod_11", "type": "series", "name": "🇮🇱 ערוץ 11 (כאן)",  "extra": "/genre=None"},
]
ANIME_CATALOGS = [
    {"id": "mal.airing",    "type": "anime", "name": "🎌 אנימה — משודרת עכשיו", "extra": "/genre=None"},
    {"id": "mal.top_anime", "type": "anime", "name": "🎌 אנימה — הטובות ביותר", "extra": "/genre=None"},
]

def main_menu():
    if not check_settings():
        return
    xbmcplugin.setPluginCategory(HANDLE, 'Shonti')
    xbmcplugin.setContent(HANDLE, 'files')
    show_israel = ADDON.getSetting('show_israel') == 'true'
    show_anime  = ADDON.getSetting('show_anime')  == 'true'
    catalogs = BASE_CATALOGS[:]
    if show_israel:
        catalogs += ISRAEL_CATALOGS
    if show_anime:
        catalogs += ANIME_CATALOGS
    for cat in catalogs:
        li = xbmcgui.ListItem(label=cat['name'])
        li.setArt({'icon': 'DefaultFolder.png'})
        url = build_url({'action': 'catalog', 'cat_id': cat['id'],
                         'cat_type': cat['type'], 'cat_name': cat['name'],
                         'cat_extra': cat.get('extra', '')})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    li = xbmcgui.ListItem(label='⚙️ הגדרות')
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'settings'}), li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)

def show_catalog(cat_id, cat_type, cat_name, cat_extra, skip=0):
    meta_url, _ = get_settings()
    xbmcplugin.setPluginCategory(HANDLE, cat_name)
    xbmcplugin.setContent(HANDLE, 'movies' if cat_type == 'movie' else 'tvshows')
    url  = f"{meta_url}/catalog/{cat_type}/{cat_id}{cat_extra}/skip={skip}.json"
    data = get_json(url)
    if not data or 'metas' not in data:
        xbmcgui.Dialog().notification('Shonti', 'אין תוצאות', xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    for item in data['metas']:
        item_id   = item.get('id', '')
        item_type = item.get('type', cat_type)
        title     = item.get('name', item.get('title', 'ללא שם'))
        year      = item.get('year', '')
        poster    = item.get('poster', '')
        bg        = item.get('background', item.get('fanart', ''))
        desc      = item.get('description', '')
        rating    = item.get('imdbRating', '')
        label = f"{title} ({year})" if year else title
        li = xbmcgui.ListItem(label=label)
        li.setArt({'poster': poster, 'fanart': bg, 'thumb': poster})
        li.setInfo('video', {'title': title, 'year': int(year) if str(year).isdigit() else 0,
                             'plot': desc, 'rating': float(rating) if rating else 0.0,
                             'mediatype': 'movie' if item_type == 'movie' else 'tvshow'})
        target_url = build_url({'action': 'detail', 'item_id': item_id, 'item_type': item_type,
                                 'title': title, 'poster': poster, 'bg': bg})
        xbmcplugin.addDirectoryItem(HANDLE, target_url, li, isFolder=True)
    if len(data['metas']) >= 50:
        li = xbmcgui.ListItem(label='⏩ עמוד הבא')
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'catalog', 'cat_id': cat_id,
            'cat_type': cat_type, 'cat_name': cat_name, 'cat_extra': cat_extra,
            'skip': skip + 50}), li, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def show_detail(item_id, item_type, title, poster, bg):
    meta_url, _ = get_settings()
    xbmcplugin.setPluginCategory(HANDLE, title)
    url  = f"{meta_url}/meta/{item_type}/{urllib.parse.quote(item_id, safe='')}.json"
    data = get_json(url)
    if not data or 'meta' not in data:
        show_streams(item_id, item_type, title, poster, bg)
        return
    meta = data['meta']
    if item_type == 'movie':
        show_streams(item_id, item_type, title, poster, bg)
    elif item_type in ('series', 'anime', 'anime.series', 'tv'):
        xbmcplugin.setContent(HANDLE, 'episodes')
        videos  = meta.get('videos', [])
        seasons = {}
        for v in videos:
            seasons.setdefault(v.get('season', 1), []).append(v)
        if len(seasons) > 1:
            for s_num in sorted(seasons.keys()):
                li = xbmcgui.ListItem(label=f"עונה {s_num}")
                li.setArt({'poster': poster, 'fanart': bg})
                xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'season',
                    'item_id': item_id, 'item_type': item_type, 'title': title,
                    'poster': poster, 'bg': bg, 'season': s_num}), li, isFolder=True)
        else:
            for v in videos:
                _add_episode_item(v, item_id, item_type, title, poster, bg)
        xbmcplugin.endOfDirectory(HANDLE)

def show_season(item_id, item_type, title, poster, bg, season):
    meta_url, _ = get_settings()
    xbmcplugin.setPluginCategory(HANDLE, f"{title} — עונה {season}")
    xbmcplugin.setContent(HANDLE, 'episodes')
    url  = f"{meta_url}/meta/{item_type}/{urllib.parse.quote(item_id, safe='')}.json"
    data = get_json(url)
    if not data or 'meta' not in data:
        xbmcplugin.endOfDirectory(HANDLE)
        return
    for v in [v for v in data['meta'].get('videos', []) if str(v.get('season', 1)) == str(season)]:
        _add_episode_item(v, item_id, item_type, title, poster, bg)
    xbmcplugin.endOfDirectory(HANDLE)

def _add_episode_item(v, item_id, item_type, title, poster, bg):
    ep_id    = v.get('id', item_id)
    ep_num   = v.get('episode', v.get('number', '?'))
    ep_title = v.get('title', v.get('name', f"פרק {ep_num}"))
    ep_thumb = v.get('thumbnail', poster)
    label    = f"פרק {ep_num} — {ep_title}"
    li = xbmcgui.ListItem(label=label)
    li.setArt({'thumb': ep_thumb, 'fanart': bg, 'poster': poster})
    li.setInfo('video', {'title': label, 'episode': ep_num, 'mediatype': 'episode'})
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'streams', 'item_id': ep_id,
        'item_type': item_type, 'title': label, 'poster': ep_thumb, 'bg': bg}), li, isFolder=True)

def show_streams(item_id, item_type, title, poster, bg):
    _, stream_url = get_settings()
    xbmcplugin.setPluginCategory(HANDLE, f"סטרימים — {title}")
    xbmcplugin.setContent(HANDLE, 'files')
    url  = f"{stream_url}/stream/{item_type}/{urllib.parse.quote(item_id, safe='')}.json"
    data = get_json(url)
    if not data or not data.get('streams'):
        xbmcgui.Dialog().notification('Shonti', 'לא נמצאו סטרימים', xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    for stream in data['streams']:
        s_url  = stream.get('url', '')
        s_name = stream.get('name', 'Stream')
        s_desc = stream.get('description', stream.get('title', ''))
        if not s_url:
            continue
        label = s_name + (f"  |  {s_desc[:80]}" if s_desc else '')
        li = xbmcgui.ListItem(label=label)
        li.setArt({'thumb': poster, 'fanart': bg})
        li.setInfo('video', {'title': title})
        li.setProperty('IsPlayable', 'true')
        li.setPath(s_url)
        subs = [s.get('url') for s in stream.get('subtitles', []) if s.get('url')]
        if subs:
            li.setSubtitles(subs)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'play',
            'stream_url': s_url, 'title': title}), li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)

def play_stream(stream_url, title):
    li = xbmcgui.ListItem(label=title, path=stream_url)
    li.setProperty('IsPlayable', 'true')
    xbmcplugin.setResolvedUrl(HANDLE, True, li)

def router(params):
    action = params.get('action', 'main')
    if action == 'main':
        main_menu()
    elif action == 'settings':
        ADDON.openSettings()
    elif action == 'catalog':
        show_catalog(params['cat_id'], params['cat_type'],
                     params.get('cat_name', ''), params.get('cat_extra', ''),
                     int(params.get('skip', 0)))
    elif action == 'detail':
        show_detail(params['item_id'], params['item_type'],
                    params.get('title', ''), params.get('poster', ''), params.get('bg', ''))
    elif action == 'season':
        show_season(params['item_id'], params['item_type'],
                    params.get('title', ''), params.get('poster', ''),
                    params.get('bg', ''), params.get('season', 1))
    elif action == 'streams':
        show_streams(params['item_id'], params['item_type'],
                     params.get('title', ''), params.get('poster', ''), params.get('bg', ''))
    elif action == 'play':
        play_stream(params['stream_url'], params.get('title', ''))

if __name__ == '__main__':
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
    router(params)
