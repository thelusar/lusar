"""Build validated public catalog generations without changing the running generation in place."""
import json
import logging
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import mkdtemp
from threading import Event, Lock, RLock, Thread

from sync_catalog import SNAPSHOT, fetch_catalog, replace_snapshot, revision, validate

ROOT = Path(__file__).resolve().parent


class CatalogUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Generation:
    revision: str
    data: dict
    directory: Path
    snapshot: Path


class CatalogService:
    def __init__(self, directory, *, snapshot=SNAPSHOT, built=None, fetcher=fetch_catalog):
        self.base = Path(directory).resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        data = json.loads(Path(snapshot).read_text(encoding="utf-8-sig"))
        validate(data)
        initial = Generation(revision(data), data, Path(built or ROOT / "dist"), Path(snapshot))
        self.active = initial
        self.generations = {initial.revision: initial}
        self.leases = {}
        self.lock = RLock()
        self.refresh_lock = Lock()
        self.fetcher = fetcher
        self.last_checked = None
        self.last_success = None
        self.failed = False
        self.stop = Event()
        self.worker = None

    @contextmanager
    def acquire(self, version=None):
        with self.lock:
            generation = self.generations.get(version, self.active)
            self.leases[generation.revision] = self.leases.get(generation.revision, 0) + 1
        try:
            yield generation
        finally:
            with self.lock:
                self.leases[generation.revision] -= 1
                self._cleanup()

    def _remove(self, path):
        path = path.resolve()
        if path != self.base and path.is_relative_to(self.base):
            shutil.rmtree(path)

    def _cleanup(self):
        # Retain recent versions for HTML that is still loading its versioned scripts.
        for version in list(self.generations)[:-3]:
            generation = self.generations[version]
            if generation is self.active or self.leases.get(version, 0):
                continue
            try:
                self._remove(generation.directory.parent)
            except OSError:
                continue
            del self.generations[version]
            self.leases.pop(version, None)

    def build(self, data):
        directory = Path(mkdtemp(prefix="catalog-", dir=self.base))
        snapshot = directory / "storefront.json"
        try:
            replace_snapshot(data, snapshot)
            environment = {**os.environ, "LUSAR_CATALOG_PATH": str(snapshot), "LUSAR_BUILD_DIR": str(directory / "dist")}
            subprocess.run([sys.executable, "-B", str(ROOT / "build.py")], env=environment,
                           capture_output=True, timeout=30, check=True)
            return Generation(revision(data), data, directory / "dist", snapshot)
        except Exception:
            self._remove(directory)
            raise

    def refresh(self):
        with self.refresh_lock:
            try:
                data = self.fetcher()
                validate(data)
                version = revision(data)
                with self.lock:
                    active = self.active
                    candidate = self.generations.get(version)
                if active.revision != version:
                    candidate = candidate or self.build(data)
                    with self.lock:
                        self.active = candidate
                        self.generations.pop(version, None)
                        self.generations[version] = candidate
                        self._cleanup()
                    logging.info("LUSAR catalog: activated %s (%d products).", version, len(data["products"]))
                with self.lock:
                    self.last_checked = self.last_success = datetime.now(timezone.utc).isoformat()
                    self.failed = False
                    return self.active
            except Exception as error:
                with self.lock:
                    self.last_checked = datetime.now(timezone.utc).isoformat()
                    self.failed = True
                logging.warning("LUSAR catalog: refresh failed (%s); keeping the last generation.", type(error).__name__)
                raise CatalogUnavailable("Каталог временно недоступен для проверки. Попробуйте отправить заявку позже.") from None

    def current_data(self):
        with self.lock:
            return self.active.data

    def status(self):
        with self.lock:
            return {"revision": self.active.revision, "products": len(self.active.data["products"]),
                    "lastChecked": self.last_checked, "lastSuccess": self.last_success,
                    "synchronized": self.last_success is not None and not self.failed}

    def start(self, interval=30):
        def run():
            while not self.stop.wait(interval):
                try:
                    self.refresh()
                except CatalogUnavailable:
                    pass
        self.worker = Thread(target=run, name="lusar-catalog", daemon=True)
        self.worker.start()

    def close(self):
        self.stop.set()
        if self.worker:
            self.worker.join(timeout=40)
