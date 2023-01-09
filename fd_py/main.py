from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
import re
import sys
from typing import Literal
from rich.tree import Tree
from rich.text import Text
from rich import print


class PathFilter(ABC):
    @abstractmethod
    def filter(self, path: Path) -> bool:
        ...


class HiddenFilter(PathFilter):
    def filter(self, path: Path) -> bool:
        return path.name.startswith(".")


class FileExtensionFilter(PathFilter):
    def __init__(self, file_extension: str) -> None:
        self.file_extension = file_extension

    def filter(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lstrip(".") == self.file_extension


class RegexFilter(PathFilter):
    def __init__(self, pattern: str) -> None:
        self.pattern = pattern

    def filter(self, path: Path) -> bool:
        return bool(re.findall(self.pattern, str(path.absolute())))


class FiletypeFilter(PathFilter):
    filetype_map: dict[str, Callable[[Path], bool]] = {
        "s": Path.is_socket,
        "f": Path.is_file,
        "d": Path.is_dir,
        "p": Path.is_fifo,
        "l": Path.is_symlink,
    }

    def __init__(self, filetype: Literal["s", "x", "f", "d", "p"]) -> None:
        self.filetype = filetype

    def filter(self, path: Path) -> bool:
        return self.filetype_map[self.filetype](path)


class InverseFilter(PathFilter):
    def __init__(self, pfilter: PathFilter) -> None:
        self.pfilter = pfilter

    def filter(self, path: Path) -> bool:
        return not self.pfilter.filter(path)


def ls(
    path: Path = Path("."),
    *,
    max_depth: int = 10,
    filters: list[PathFilter] | None = None,
) -> Tree:
    tree = Tree(Text(path.name, style="blue"))
    try:
        for file in Path(path).expanduser().iterdir():
            if file.is_dir() and max_depth > 0:
                tree.add(ls(file, max_depth=max_depth - 1, filters=filters))
            if filters is not None and all(pf.filter(file) for pf in filters):
                tree.add(file.name)
    except PermissionError:
        print(f"access denied for file: {path}", file=sys.stderr)
    return tree


filters = []
filters.append(FiletypeFilter("f"))
# filters.append(FileExtensionFilter("py"))
# filters.append(FileExtensionFilter("pyc"))
# filters.append(InverseFilter(RegexFilter("lib")))
t = ls(Path("/etc"), max_depth=3, filters=filters)
print(t)
