import argparse
import time
from pathlib import Path

from .common import load_config
from .export import write_csv
from .pipeline import generate, write_version


def main(argv=None):
    parser = argparse.ArgumentParser(prog="generator", description="Синтетический датасет стенда IgpaLab")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="сгенерировать версию датасета")
    gen.add_argument("--out", help="папка версии, по умолчанию synthetic/<version>")
    gen.add_argument("--students", type=int)
    gen.add_argument("--seed", type=int)
    gen.add_argument("--version")
    gen.add_argument("--rules", help="набор правил igpa для срезов: default или eduscore")
    gen.add_argument("--config")
    csv = sub.add_parser("csv", help="выгрузить таблицы версии в CSV для просмотра")
    csv.add_argument("--dir", default="synthetic/v1")
    sub.add_parser("open", help="скачать открытые данные для серии S5 (UCI Student Performance) в open/uci")
    args = parser.parse_args(argv)

    if args.command == "open":
        from .open_data import download_uci
        download_uci(Path("open/uci"))
        return
    if args.command == "csv":
        write_csv(Path(args.dir))
        return
    cfg = load_config(args.config, students=args.students, seed=args.seed, version=args.version, rules=args.rules)
    out = Path(args.out or f"synthetic/{cfg['version']}")
    start = time.perf_counter()
    data = generate(cfg)
    write_version(out, data, cfg)
    print(f"{out}: студентов {len(data['students'])}, истинных записей {len(data['records_true'])}, "
          f"в АСУ {len(data['records_asu'])}, за {time.perf_counter() - start:.0f} с")


if __name__ == "__main__":
    main()
