from __future__ import annotations

from pathlib import Path

from robosmix.domain.models import TrackRole
from robosmix.errors import RoleError

_ALIASES: dict[str, TrackRole] = {
    "vocal": TrackRole.VOCALS,
    "vocals": TrackRole.VOCALS,
    "vox": TrackRole.VOCALS,
    "voice": TrackRole.VOCALS,
    "sing": TrackRole.VOCALS,
    "bgv": TrackRole.BACKING_VOCALS,
    "bg_vox": TrackRole.BACKING_VOCALS,
    "backing": TrackRole.BACKING_VOCALS,
    "backing_vox": TrackRole.BACKING_VOCALS,
    "backing_vocal": TrackRole.BACKING_VOCALS,
    "backing_vocals": TrackRole.BACKING_VOCALS,
    "harmony": TrackRole.BACKING_VOCALS,
    "drum": TrackRole.DRUMS,
    "drums": TrackRole.DRUMS,
    "kick": TrackRole.DRUMS,
    "snare": TrackRole.DRUMS,
    "hat": TrackRole.DRUMS,
    "hats": TrackRole.DRUMS,
    "cymbal": TrackRole.DRUMS,
    "tom": TrackRole.DRUMS,
    "toms": TrackRole.DRUMS,
    "overhead": TrackRole.DRUMS,
    "perc": TrackRole.PERCUSSION,
    "percussion": TrackRole.PERCUSSION,
    "shaker": TrackRole.PERCUSSION,
    "tamb": TrackRole.PERCUSSION,
    "bass": TrackRole.BASS,
    "gtr": TrackRole.GUITAR,
    "guitar": TrackRole.GUITAR,
    "guitars": TrackRole.GUITAR,
    "guit": TrackRole.GUITAR,
    "keys": TrackRole.KEYS,
    "key": TrackRole.KEYS,
    "keyboard": TrackRole.KEYS,
    "piano": TrackRole.KEYS,
    "rhodes": TrackRole.KEYS,
    "organ": TrackRole.KEYS,
    "synth": TrackRole.SYNTH,
    "synthesizer": TrackRole.SYNTH,
    "pad": TrackRole.SYNTH,
    "strings": TrackRole.STRINGS,
    "violin": TrackRole.STRINGS,
    "viola": TrackRole.STRINGS,
    "cello": TrackRole.STRINGS,
    "fiddle": TrackRole.STRINGS,
    "brass": TrackRole.BRASS,
    "horn": TrackRole.BRASS,
    "horns": TrackRole.BRASS,
    "trumpet": TrackRole.BRASS,
    "sax": TrackRole.BRASS,
    "trombone": TrackRole.BRASS,
    "other": TrackRole.OTHER,
    "misc": TrackRole.OTHER,
}

_DETECTION_ORDER: tuple[tuple[TrackRole, tuple[str, ...]], ...] = (
    (TrackRole.BACKING_VOCALS, ("bgv", "backing", "harmony", "choir", "harmonies")),
    (TrackRole.DRUMS, ("drum", "kick", "snare", "hat", "cymbal", "overhead", "tom", "room")),
    (TrackRole.PERCUSSION, ("perc", "shaker", "tamb", "conga", "bongo", "clap")),
    (TrackRole.BASS, ("bass",)),
    (TrackRole.GUITAR, ("gtr", "guitar", "guit")),
    (TrackRole.STRINGS, ("violin", "viola", "cello", "string", "fiddle")),
    (TrackRole.BRASS, ("trumpet", "sax", "horn", "trombone", "brass")),
    (TrackRole.KEYS, ("keys", "keyboard", "piano", "rhodes", "organ", "wurli", "clav")),
    (TrackRole.SYNTH, ("synth", "pad", "arp", "moog")),
    (TrackRole.VOCALS, ("vocal", "vox", "voice", "sing", "lead", "rap")),
)


def normalize_role(value: str) -> TrackRole:
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    try:
        return _ALIASES[key]
    except KeyError as exc:
        choices = ", ".join(sorted(role.value for role in TrackRole))
        raise RoleError(f"unknown role {value!r}; choose one of: {choices}") from exc


def detect_role(path: Path) -> TrackRole:
    name = path.stem.lower()
    for role, keywords in _DETECTION_ORDER:
        if any(keyword in name for keyword in keywords):
            return role
    return TrackRole.OTHER
