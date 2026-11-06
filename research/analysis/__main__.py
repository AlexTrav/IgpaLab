import argparse
import json
from pathlib import Path

from . import eda
from .figures import all_figures
from .report import build


def main(argv=None):
    parser = argparse.ArgumentParser(prog="analysis", description="Анализ синтетического датасета IgpaLab")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--data", default="/repo/data/synthetic")
    parser.add_argument("--out", default="results")
    args = parser.parse_args(argv)

    data = eda.load(Path(args.data) / args.version)
    out = Path(args.out) / args.version
    text, numbers = build(data, args.version)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(text, encoding="utf-8")
    (out / "numbers.json").write_text(json.dumps(numbers, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for lang in ("ru", "en"):
        all_figures(data, out / "figures" / lang, lang)
    print(f"{out}: отчёт, числа и рисунки ru/en готовы")


if __name__ == "__main__":
    main()
