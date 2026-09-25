from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends

from hone.core.workspace import Workspace, open_workspace


def get_workspace() -> Iterator[Workspace]:
    with open_workspace(allow_cross_thread=True) as workspace:
        yield workspace


WorkspaceDep = Annotated[Workspace, Depends(get_workspace)]
