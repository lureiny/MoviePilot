import shutil
from pathlib import Path
from typing import Any, List

from fastapi import APIRouter, Depends
from starlette.responses import FileResponse

from app import schemas
from app.core.config import settings
from app.core.security import verify_token
from app.log import logger
from app.utils.system import SystemUtils

router = APIRouter()


@router.get("/list", summary="所有插件", response_model=List[schemas.FileItem])
def list_path(path: str, _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    查询当前目录下所有目录和文件
    """
    if not path:
        path = "/"
    path_obj = Path(path)
    if not path_obj.exists():
        logger.error(f"目录不存在：{path}")
        return []
    ret_items = []
    # 如果是文件
    if path_obj.is_file():
        ret_items.append(schemas.FileItem(
            type="file",
            path=str(path_obj),
            name=path_obj.name,
            basename=path_obj.stem,
            extension=path_obj.suffix,
            size=path_obj.stat().st_size,
        ))
        return ret_items
    # 扁历所有目录
    for item in SystemUtils.list_sub_directory(path_obj):
        ret_items.append(schemas.FileItem(
            type="dir",
            path=str(item) + "/",
            name=item.name,
            basename=item.stem,
            extension=item.suffix,
        ))
    # 遍历所有文件，不含子目录
    for item in SystemUtils.list_sub_files(path_obj,
                                           settings.RMT_MEDIAEXT
                                           + settings.RMT_SUBEXT
                                           + [".jpg", ".png", ".nfo"]):
        ret_items.append(schemas.FileItem(
            type="file",
            path=str(item),
            name=item.name,
            basename=item.stem,
            extension=item.suffix,
            size=item.stat().st_size,
        ))
    return ret_items


@router.get("/mkdir", summary="创建目录", response_model=schemas.Response)
def mkdir(path: str, _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    创建目录
    """
    if not path:
        return schemas.Response(success=False)
    path_obj = Path(path)
    if path_obj.exists():
        return schemas.Response(success=False)
    path_obj.mkdir(parents=True, exist_ok=True)
    return schemas.Response(success=True)


@router.get("/delete", summary="删除文件或目录", response_model=schemas.Response)
def delete(path: str, _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    删除文件或目录
    """
    if not path:
        return schemas.Response(success=False)
    path_obj = Path(path)
    if not path_obj.exists():
        return schemas.Response(success=True)
    if path_obj.is_file():
        path_obj.unlink()
    else:
        shutil.rmtree(path_obj, ignore_errors=True)
    return schemas.Response(success=True)


@router.get("/download", summary="下载文件或目录")
def download(path: str, _: schemas.TokenPayload = Depends(verify_token)) -> Any:
    """
    下载文件或目录
    """
    if not path:
        return schemas.Response(success=False)
    path_obj = Path(path)
    if not path_obj.exists():
        return schemas.Response(success=False)
    if path_obj.is_file():
        # 做为文件流式下载
        return FileResponse(path_obj, headers={
            "Content-Disposition": f"attachment; filename={path_obj.name}"
        }, filename=path_obj.name)
    else:
        # 做为压缩包下载
        shutil.make_archive(base_name=path_obj.stem, format="zip", root_dir=path_obj)
        reponse = FileResponse(f"{path_obj.stem}.zip", headers={
            "Content-Disposition": f"attachment; filename={path_obj.stem}.zip"
        }, filename=f"{path_obj.stem}.zip")
        # 删除压缩包
        Path(f"{path_obj.stem}.zip").unlink()
        return reponse