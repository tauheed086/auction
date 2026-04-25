import csv
import json
import mimetypes
import re
from urllib.error import HTTPError, URLError
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from players.models import Player


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
ROLE_MAP = {
    "batsman": "batsman",
    "batsmen": "batsman",
    "wicket-keeper batsman": "batsman",
    "wicket keeper batsman": "batsman",
    "wicketkeeper batsman": "batsman",
    "wicket-keeper batsmen": "batsman",
    "wicket keeper batsmen": "batsman",
    "wicketkeeper batsmen": "batsman",
    "bowler": "bowler",
    "allrounder": "allrounder",
    "all-rounder": "allrounder",
    "all rounder": "allrounder",
}


def normalize_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def normalize_role(value):
    normalized = str(value).strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    if not normalized:
        return ""
    return ROLE_MAP.get(normalized, "")


def extract_drive_file_id(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "drive.google.com" not in host and "docs.google.com" not in host:
        return None

    path_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", parsed.path)
    if path_match:
        return path_match.group(1)

    query_params = parse_qs(parsed.query)
    file_ids = query_params.get("id")
    if file_ids:
        return file_ids[0]

    return None


def build_download_url(source_url):
    file_id = extract_drive_file_id(source_url)
    if not file_id:
        return source_url
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def download_drive_thumbnail_jpeg(file_id):
    thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w2000"
    request = Request(thumbnail_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=45) as response:
        content_type = response.headers.get_content_type()
        content = response.read()
    if not content:
        raise CommandError("Empty thumbnail response from Google Drive.")
    if content_type != "image/jpeg":
        raise CommandError(f"Unexpected thumbnail content type: {content_type}")
    return content


def is_heic_content(content, content_type):
    ct = (content_type or "").lower()
    if "heic" in ct or "heif" in ct:
        return True

    # ISO-BMFF headers for HEIC/HEIF are often in the first 32 bytes.
    header = content[:32]
    return (b"ftypheic" in header) or (b"ftypheif" in header)


def guess_extension(content_type, source_url):
    extension = mimetypes.guess_extension(content_type or "")
    if extension == ".jpe":
        extension = ".jpg"

    if extension and extension.lower() in IMAGE_EXTENSIONS:
        return extension.lower()

    source_extension = Path(urlparse(source_url).path).suffix.lower()
    if source_extension in IMAGE_EXTENSIONS:
        return source_extension

    return ".jpg"


def download_image(image_url):
    file_id = extract_drive_file_id(image_url)
    download_url = build_download_url(image_url)
    request = Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=45) as response:
        content_type = response.headers.get_content_type()
        content = response.read()
        final_url = response.geturl()

    if not content:
        raise CommandError(f"Empty response while downloading image: {image_url}")
    if content_type == "text/html":
        raise CommandError(
            f"Could not download image bytes from URL: {image_url}. "
            "Check that the Google Drive file is publicly accessible."
        )
    if file_id and is_heic_content(content, content_type):
        try:
            jpeg_content = download_drive_thumbnail_jpeg(file_id)
            return jpeg_content, ".jpg"
        except Exception:
            # Fallback to original bytes; keep real extension so we don't store HEIC as .jpg.
            return content, ".heic"

    extension = guess_extension(content_type, final_url or image_url)
    return content, extension


class Command(BaseCommand):
    help = (
        "Import players from CSV/JSON and download each image URL into local media storage."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "data_file",
            type=str,
            help="Path to CSV or JSON file with name, mobile_number, photo_url, role.",
        )

    def handle(self, *args, **options):
        data_file = Path(options["data_file"]).expanduser().resolve()
        if not data_file.exists():
            raise CommandError(f"File not found: {data_file}")

        rows = self.load_rows(data_file)
        imported = 0
        skipped = 0

        for index, row in enumerate(rows, start=1):
            try:
                name = self.pick_field(row, "name") or ""
                mobile_number = self.pick_field(row, "mobilenumber", "mobile")
                photo_url = self.pick_field(row, "photourl", "imageurl", "url")
                role_input = self.pick_field(row, "role") or ""
                normalized_role = normalize_role(role_input)

                if role_input and not normalized_role:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Row {index}: unsupported role '{role_input}'. Saved as blank role."
                        )
                    )

                if not any([name, mobile_number, photo_url, role_input]):
                    skipped += 1
                    self.stderr.write(
                        self.style.WARNING(f"Row {index}: empty row. Skipped.")
                    )
                    continue

                defaults = {
                    "name": name.strip(),
                    "role": normalized_role,
                }

                if mobile_number:
                    player, _ = Player.objects.update_or_create(
                        mobile_number=mobile_number.strip(),
                        defaults=defaults,
                    )
                else:
                    player = Player.objects.create(
                        mobile_number=None,
                        **defaults,
                    )

                image_saved = False
                if photo_url:
                    try:
                        content, extension = download_image(photo_url)
                        name_fragment = slugify(name) or "player"
                        mobile_fragment = (
                            re.sub(r"\D", "", mobile_number)[-4:]
                            if mobile_number
                            else f"r{index}"
                        )
                        filename = f"{name_fragment}-{mobile_fragment}{extension}"
                        player.image.save(filename, ContentFile(content), save=False)
                        image_saved = True
                    except (CommandError, HTTPError, URLError, TimeoutError, ValueError) as exc:
                        self.stderr.write(
                            self.style.WARNING(
                                f"Row {index}: image download failed ({exc}). Saved without image."
                            )
                        )

                player.save()
                imported += 1
                image_status = "image saved" if image_saved else "image blank"
                mobile_status = player.mobile_number or "no-mobile"
                display_name = player.name or "<blank-name>"
                self.stdout.write(
                    f"Imported row {index}: {display_name} ({mobile_status}) - {image_status}"
                )
            except Exception as exc:
                skipped += 1
                self.stderr.write(
                    self.style.WARNING(
                        f"Row {index}: failed ({exc}). Row skipped without crashing import."
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete. Imported: {imported}, Skipped: {skipped}"
            )
        )

    def load_rows(self, data_file):
        suffix = data_file.suffix.lower()
        if suffix == ".csv":
            with data_file.open("r", encoding="utf-8-sig", newline="") as file_obj:
                return list(csv.DictReader(file_obj))

        if suffix == ".json":
            with data_file.open("r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
            if isinstance(data, dict) and "players" in data:
                data = data["players"]
            if not isinstance(data, list):
                raise CommandError(
                    "JSON input must be a list of player objects or {'players': [...]}."
                )
            return data

        raise CommandError("Unsupported file type. Use .csv or .json")

    def pick_field(self, row, *aliases):
        normalized = {normalize_key(key): value for key, value in row.items()}
        for alias in aliases:
            value = normalized.get(alias)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None
