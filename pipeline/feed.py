"""RSS 2.0 + iTunes feed management for podcast.xml."""
import logging
from pathlib import Path
from xml.etree import ElementTree as ET

from . import config
from .models import EpisodeRecord

log = logging.getLogger(__name__)

_FEED_PATH = Path("podcast.xml")

_ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
_ATOM_NS = "http://www.w3.org/2005/Atom"

ET.register_namespace("itunes", _ITUNES_NS)
ET.register_namespace("atom", _ATOM_NS)


def _make_empty_feed() -> ET.Element:
    cfg = config.all_config()["podcast"]
    # ET.register_namespace handles xmlns injection; don't set them as explicit attribs
    rss = ET.Element("rss", attrib={"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = cfg["title"]
    ET.SubElement(channel, "description").text = cfg["description"]
    ET.SubElement(channel, "language").text = cfg["language"]
    ET.SubElement(channel, f"{{{_ITUNES_NS}}}author").text = cfg["author"]
    ET.SubElement(channel, f"{{{_ITUNES_NS}}}explicit").text = "no"
    return rss


def _load_feed(path: Path) -> ET.Element:
    if not path.exists():
        log.info("No existing feed found, creating new one")
        return _make_empty_feed()
    tree = ET.parse(path)
    return tree.getroot()


def _existing_guids(rss: ET.Element) -> set[str]:
    return {
        guid.text
        for guid in rss.findall(".//guid")
        if guid.text
    }


def _build_item(ep: EpisodeRecord) -> ET.Element:
    item = ET.Element("item")
    ET.SubElement(item, "title").text = ep.title
    ET.SubElement(item, "guid", isPermaLink="false").text = ep.guid
    ET.SubElement(item, "pubDate").text = ep.pub_date
    ET.SubElement(item, "enclosure", attrib={
        "url": ep.mp3_url,
        "length": str(ep.file_size_bytes),
        "type": "audio/mpeg",
    })
    if ep.duration_seconds:
        mins, secs = divmod(ep.duration_seconds, 60)
        ET.SubElement(item, f"{{{_ITUNES_NS}}}duration").text = f"{mins}:{secs:02d}"
    ET.SubElement(item, f"{{{_ITUNES_NS}}}explicit").text = "no"
    return item


def _validate_xml(rss: ET.Element) -> None:
    """Minimal validation: channel must have title and at least one item."""
    channel = rss.find("channel")
    if channel is None:
        raise ValueError("Feed missing <channel>")
    if channel.find("title") is None:
        raise ValueError("Feed <channel> missing <title>")


def prepend_episode(episode: EpisodeRecord, path: Path = _FEED_PATH) -> bool:
    """
    Prepend episode to feed. Returns True if added, False if guid already present.
    """
    rss = _load_feed(path)
    existing = _existing_guids(rss)

    if episode.guid in existing:
        log.info("Episode %s already in feed — skipping (idempotent)", episode.guid)
        return False

    channel = rss.find("channel")
    if channel is None:
        raise ValueError("Feed has no <channel> element")

    item = _build_item(episode)

    # Insert after last non-item child (channel metadata), before any existing items
    first_item_idx = None
    for i, child in enumerate(list(channel)):
        if child.tag == "item":
            first_item_idx = i
            break

    if first_item_idx is not None:
        channel.insert(first_item_idx, item)
    else:
        channel.append(item)

    _validate_xml(rss)

    ET.indent(rss, space="  ")
    tree = ET.ElementTree(rss)
    tree.write(path, encoding="unicode", xml_declaration=True)
    log.info("Episode %s prepended to %s", episode.guid, path)
    return True


def load_existing_guids(path: Path = _FEED_PATH) -> set[str]:
    rss = _load_feed(path)
    return _existing_guids(rss)
