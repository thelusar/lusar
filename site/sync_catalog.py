"""Refresh the storefront snapshot used by the site build and local orders."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen
from urllib.error import URLError

ENDPOINT = "https://lusar-catalog-studio.sovazones.chatgpt.site/api/storefront"
SNAPSHOT = Path(__file__).resolve().parent.parent / "storefront.json"
MAX_BYTES = 8 * 1024 * 1024
SAFE_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}")


def validate(data):
    if not isinstance(data, dict) or type(data.get("schemaVersion")) is not int or data.get("schemaVersion") != 1 or data.get("currency") != "AMD":
        raise ValueError("Неизвестный формат каталога.")
    groups = data.get("categories")
    products = data.get("products")
    if not isinstance(groups, list) or not isinstance(products, list):
        raise ValueError("Неполная выгрузка. Текущий каталог сохранён.")

    def ids(items):
        result = set()
        for item in items:
            key = item.get("id") if isinstance(item, dict) else None
            if not isinstance(key, str) or not SAFE_ID.fullmatch(key) or key in result:
                raise ValueError("В каталоге есть повторяющийся или недопустимый ID.")
            if not isinstance(item.get("name"), str) or not item["name"].strip():
                raise ValueError("В каталоге есть запись без названия.")
            result.add(key)
        return result

    category_ids = ids(groups)
    ids(products)
    for group in groups:
        parent = group.get("parentId")
        if parent is not None and (not isinstance(parent, str) or parent not in category_ids or parent == group["id"]):
            raise ValueError("Не найдена родительская категория.")
    parents = {group["id"]: group.get("parentId") for group in groups}
    for key in parents:
        seen = set()
        while key is not None:
            if key in seen:
                raise ValueError("Цикл родительских категорий.")
            seen.add(key)
            key = parents[key]
    for product in products:
        if product.get("categoryId") not in category_ids:
            raise ValueError("У товара нет опубликованной категории.")
        if any(not isinstance(product.get(key), str) for key in ("sku", "description", "brand")):
            raise ValueError("В карточке отсутствуют обязательные поля.")
        if "price" not in product:
            raise ValueError("В карточке отсутствует цена.")
        price = product["price"]
        if price is not None and (type(price) not in (int, float) or not math.isfinite(price) or price < 0 or product.get("currency") != "AMD"):
            raise ValueError("Некорректная цена товара.")
        for key, fields in (("images", ("url",)), ("attributes", ("key", "label", "value", "unit"))):
            entries = product.get(key)
            if not isinstance(entries, list) or any(
                not isinstance(entry, dict) or any(not isinstance(entry.get(field), str) for field in fields)
                for entry in entries
            ):
                raise ValueError(f"Некорректное поле карточки: {key}.")
        if any(not re.fullmatch(r"https://lusar-catalog-studio\.sovazones\.chatgpt\.site/api/storefront/photo/[a-f0-9-]{36}", entry["url"])
               for entry in product["images"]):
            raise ValueError("Неожиданный адрес фотографии.")


def replace_snapshot(data, destination):
    validate(data)
    temp_path = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent, delete=False) as temp:
            temp_path = Path(temp.name)
            json.dump(data, temp, ensure_ascii=False, indent=2)
            temp.write("\n")
        temp_path.replace(destination)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def revision(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()[:24]


def fetch_catalog(*, timeout=8):
    # The public service rejects urllib's default user agent.
    request = Request(ENDPOINT, headers={"Accept": "application/json", "User-Agent": "LUSAR storefront"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Выгрузка каталога превышает допустимый размер.")
    data = json.loads(raw)
    validate(data)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Проверить и применить экспорт публичного каталога.")
    args = parser.parse_args()
    try:
        if args.input:
            with args.input.open("rb") as source:
                raw = source.read(MAX_BYTES + 1)
        else:
            data = fetch_catalog()
            replace_snapshot(data, SNAPSHOT)
            print(f'Каталог обновлён: {len(data["products"])} товаров, {len(data["categories"])} категорий.')
            return
    except (URLError, OSError) as error:
        raise SystemExit(f"Не удалось получить выгрузку. Рабочий каталог сохранён. {error}") from None
    if len(raw) > MAX_BYTES:
        raise ValueError("Выгрузка каталога превышает допустимый размер.")
    data = json.loads(raw)
    replace_snapshot(data, SNAPSHOT)
    print(f'Каталог обновлён: {len(data["products"])} товаров, {len(data["categories"])} категорий.')


if __name__ == "__main__":
    main()
