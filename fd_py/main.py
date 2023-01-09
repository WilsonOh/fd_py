from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
import re
import sys
from typing import ClassVar, Literal
from rich.tree import Tree
from rich.text import Text
from rich import print
from argparse import ArgumentParser
from dataclasses import dataclass


class PathFilter(ABC):
    @abstractmethod
    def filter(self, path: Path) -> bool:
        ...


@dataclass
class HiddenFilter(PathFilter):
    def filter(self, path: Path) -> bool:
        return path.name.startswith(".")

    def __repr__(self) -> str:
        return "HiddenFilter"


@dataclass
class FileExtensionFilter(PathFilter):
    file_extension: str

    def filter(self, path: Path) -> bool:
        return path.is_dir() or path.suffix.lstrip(".") == self.file_extension


@dataclass
class RegexFilter(PathFilter):
    pattern: str

    def filter(self, path: Path) -> bool:
        return bool(re.findall(self.pattern, str(path.absolute())))


@dataclass
class FiletypeFilter(PathFilter):
    filetype_map: ClassVar[dict[str, Callable[[Path], bool]]] = {
        "s": Path.is_socket,
        "f": Path.is_file,
        "d": Path.is_dir,
        "p": Path.is_fifo,
        "l": Path.is_symlink,
    }

    filetype: Literal["s", "x", "f", "d", "p"]

    def filter(self, path: Path) -> bool:
        return self.filetype_map[self.filetype](path)


@dataclass
class InverseFilter(PathFilter):
    pfilter: PathFilter

    def filter(self, path: Path) -> bool:
        return not self.pfilter.filter(path)


def ls(
    path: Path = Path("."),
    *,
    max_depth: int = 10,
    filters: list[PathFilter],
) -> Tree:
    tree = Tree(Text(path.name, style="blue"), guide_style="magenta")
    try:
        for file in Path(path).expanduser().iterdir():
            if all(pf.filter(file) for pf in filters):
                if file.is_dir() and max_depth > 0:
                    tree.add(ls(file, max_depth=max_depth - 1, filters=filters))
                else:
                    tree.add(Text(file.name, style=("blue" if file.is_dir() else "")))
    except PermissionError:
        print(f"access denied for file: {path}", file=sys.stderr)
    return tree


def main():
    parser = ArgumentParser(prog="fd_py", description="fd but written in python")
    parser.add_argument("path", default=".", nargs="?")
    parser.add_argument(
        "-H",
        "--hidden",
        action="store_false",
        help="show hidden files as well",
        default=True,
    )

    parser.add_argument(
        "-t",
        "--type",
        choices=("s", "f", "d", "p"),
        action="extend",
        help="filter the type of file shown",
    )

    parser.add_argument(
        "-p",
        "--pattern",
        help="list files that match the pattern",
        nargs="?",
        default=".*",
    )

    parser.add_argument(
        "-E",
        "--exclude",
        help="exclude files that match the pattern",
        action="append",
    )
    parser.add_argument(
        "--max-depth",
        help="maximum depth of recursion when listing files",
        type=int,
        nargs="?",
        default=10,
    )
    parser.add_argument(
        "-e", "--ext", help="only show files with the extension", action="append"
    )
    args = parser.parse_args()
    filters = []
    if args.hidden:
        filters.append(InverseFilter(HiddenFilter()))
    if args.type:
        for t in args.type:
            filters.append(FiletypeFilter(t))
    if args.pattern:
        filters.append(RegexFilter(args.pattern))
    if args.exclude:
        for e in args.exclude:
            filters.append(InverseFilter(RegexFilter(e)))
    if args.ext:
        for ext in args.ext:
            filters.append(FileExtensionFilter(ext))
    t = ls(Path(args.path), max_depth=args.max_depth, filters=filters)
    print(t)


if __name__ == "__main__":
    main()
