"""Immediate allocation ownership and narrow cleanup before identity completion."""
import errno
import os
import pathlib
import stat
PREFIX='mixer-toggle-xctest-'


def prepare(h,lifecycle,returned,parent):
    # Record the exact successful allocation before resolve/chmod/stat or receipt
    # operations can fail. No identity is inferred from mkdtemp's return value.
    raw=str(returned)
    lifecycle['ephemeralAllocation']=dict(path=raw,parent=str(parent),allocator='tempfile.mkdtemp',prefix=PREFIX,identityComplete=False)
    path=pathlib.Path(raw)
    validate(h,lifecycle['ephemeralAllocation'])
    h.require(path.resolve()==path,'Allocated workspace canonical path changed')
    path.chmod(0o700)
    info=path.stat()
    h.require(stat.S_ISDIR(info.st_mode) and not path.is_symlink() and info.st_uid==os.geteuid() and stat.S_IMODE(info.st_mode)==0o700,'Allocated workspace identity/permission mismatch')
    lifecycle['ephemeralWorkspace']=dict(path=raw,device=info.st_dev,inode=info.st_ino,uid=info.st_uid)
    lifecycle['ephemeralAllocation']['identityComplete']=True
    return path


def validate(h,allocation):
    path=pathlib.Path(allocation['path']);parent=pathlib.Path(allocation['parent'])
    expected=pathlib.Path(h.tempfile.gettempdir()).resolve()
    h.require(allocation['allocator']=='tempfile.mkdtemp' and allocation['prefix']==PREFIX,'Unknown workspace allocator')
    h.require(parent==expected and parent.resolve()==parent and path.is_absolute() and path.parent==parent and str(path)==allocation['path'] and path.name.startswith(PREFIX) and len(path.name)>len(PREFIX) and path.name not in ['.','..'],'Allocated workspace outside exact temporary parent/name')
    return path,parent


def absent_at(parent_fd,name):
    try:os.stat(name,dir_fd=parent_fd,follow_symlinks=False)
    except FileNotFoundError:return True
    return False


def remove(h,lifecycle):
    allocation=lifecycle.get('ephemeralAllocation')
    h.require(allocation is not None,'Allocated workspace ownership record missing')
    path,parent=validate(h,allocation)
    lifecycle['ephemeralWorkspaceAbsent']=False
    if allocation['identityComplete'] is True:
        expected=lifecycle.get('ephemeralWorkspace')
        h.require(expected is not None and expected['path']==allocation['path'],'Completed workspace identity missing or changed')
        # Retain the reviewed identity/mode-aware cleanup for the populated
        # capability workspace. Prove absence independently after it returns.
        try:h.remove_ephemeral(lifecycle)
        except BaseException:
            lifecycle['ephemeralWorkspaceAbsent']=False
            raise
        lifecycle['ephemeralWorkspaceAbsent']=False
    else:
        # The allocation is known but no verified inode identity is available.
        # Never recurse, unlink a file/symlink, or remove any child in this path.
        parent_fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            if not absent_at(parent_fd,path.name):
                info=os.stat(path.name,dir_fd=parent_fd,follow_symlinks=False)
                h.require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.geteuid(),'Pre-identity workspace is not an owned directory; preserve it')
                os.rmdir(path.name,dir_fd=parent_fd)
            h.require(absent_at(parent_fd,path.name),'Pre-identity allocated workspace still present after rmdir')
        finally:os.close(parent_fd)
        lifecycle['ephemeralPreIdentityCleanup']=dict(method='exact-empty-directory-rmdir',identityInferred=False,recursive=False)
    parent_fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:h.require(absent_at(parent_fd,path.name),'Allocated workspace remains after cleanup')
    finally:os.close(parent_fd)
    lifecycle['ephemeralWorkspaceAbsent']=True
