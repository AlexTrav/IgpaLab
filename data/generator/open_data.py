"""Открытые данные для серии S5: UCI Student Performance (Cortez, Silva 2008), лицензия CC BY 4.0.

Скачивается архив UCI, из вложенного архива достаются таблицы; контрольные суммы закреплены, чтобы результаты
серии S5 воспроизводились на тех же файлах. В git данные не идут (data/open/ в .gitignore).
"""

import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

UCI_URL = "https://archive.ics.uci.edu/static/public/320/student+performance.zip"
UCI_FILES = {
    "student-mat.csv": "e47f9ee225e1ee6e69b7564e6dac7123e80b8486677fe111f351964cef5dec80",
    "student-por.csv": "a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f",
    "student.txt": None,
}


def download_uci(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(UCI_URL, timeout=60) as resp:
        outer = resp.read()
    (folder / "student.zip").write_bytes(outer)
    with zipfile.ZipFile(io.BytesIO(outer)) as z:
        inner = z.read("student.zip")
    with zipfile.ZipFile(io.BytesIO(inner)) as z:
        for name, digest in UCI_FILES.items():
            body = z.read(name)
            if digest is not None and hashlib.sha256(body).hexdigest() != digest:
                raise ValueError(f"{name}: контрольная сумма не совпала, набор на UCI изменился")
            (folder / name).write_bytes(body)
    print(f"{folder}: {', '.join(UCI_FILES)}")
