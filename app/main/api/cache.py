from copy import deepcopy
from threading import RLock
from time import monotonic


PROFILE_CACHE_TTL_SECONDS = 5 * 60

_lock = RLock()
_profile_cache = {}
_profile_picture_cache = {}


def get_cached_profile(user_id):
    return _get(_profile_cache, user_id)


def set_cached_profile(user_id, profile_data):
    _set(_profile_cache, user_id, profile_data)
    _set(_profile_picture_cache, user_id, profile_data.get("profile_picture"))


def get_cached_profile_picture(user_id):
    return _get(_profile_picture_cache, user_id)


def set_cached_profile_picture(user_id, profile_picture_url):
    _set(_profile_picture_cache, user_id, profile_picture_url)


def invalidate_profile_cache(user_id):
    with _lock:
        _profile_cache.pop(user_id, None)
        _profile_picture_cache.pop(user_id, None)


def _get(cache, key):
    now = monotonic()
    with _lock:
        entry = cache.get(key)
        if not entry:
            return None

        if entry["expires_at"] <= now:
            cache.pop(key, None)
            return None

        return deepcopy(entry["value"])


def _set(cache, key, value):
    with _lock:
        cache[key] = {
            "value": deepcopy(value),
            "expires_at": monotonic() + PROFILE_CACHE_TTL_SECONDS,
        }
