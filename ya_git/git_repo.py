import sh
from sh.contrib import git
from pathlib import Path
from yautils import *
from typing import Optional
from datetime import datetime
import logging
from loguru import logger
import inspect

class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        if record.module == "sh":
            #if level == "DEBUG":
                return

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

class MergeConflictError(RuntimeError):
    def __init__(self, msg : str, git_repo : "GitRepo", sh_exception : sh.ErrorReturnCode ):
        super().__init__(msg)
        self.sh_exception = sh_exception
        self.git_repo = git_repo


class GitRepo:
    def __init__(self, path : Path ):
        self.path = path
        self.git = git.bake("-C",path)

    def is_dirty(self):
        out = self.git("status","-s")
        print(out)
        return len(out) != 0

    def auto_commit(self):
        self.git.add(".")
        self.git.commit("-m", "auto commit on " + datetime.now().isoformat())

    @staticmethod
    def is_git(path : Path):
        return path.exists() and (path / ".git").exists()

    @staticmethod
    def is_bare_git(path : Path):
        return path.exists() and (path / "objects").exists() and (path / "refs").exists()

    @staticmethod
    def create(path : Path, bare=False):    
        yassert(not path.exists()) #path should not exist
        path.mkdir(parents=True)
        args = ["-C", path, "init"]
        if bare:
            args.append("--bare")

        out = git(*args)
        return GitRepo(path)

    @property
    def remotes(self):
        return self.git("remote").split("\n")

    def has_remote(self, remote:str):
        for r in self.remotes:
            if r == remote:
                return True
        return False

    def add_remote(self, remote:str, path : str):
        yassert(not self.has_remote(remote))
        self.git.remote("add", remote, path)


    def fetch(self, remote : str, ref : Optional[str] = None):
        yassert(self.has_remote(remote))
        self.git.fetch(remote,ref)

    def push(self, remote : str, ref : str = "master"):
        yassert(self.has_remote(remote))
        self.git.push(remote, "-u", ref)

    def set_upstream_branch(self, remote : str, branch : str):
        self.git.branch("--set_upstream_branch", "{}/{}", remote, branch)

    def merge(self, branch : str):
        try:
            self.git.merge(branch)
        except sh.ErrorReturnCode as e:
            if e.stdout.find(b"CONFLICT")!=-1:
                raise MergeConflictError("Merge confict", self, e)
            else:
                raise e

    def diff(self, ref_a : str, ref_b : str):
        out = self.git("diff", ref_a, ref_b)
        if len(out) == 0:
            return False
        else:
            return True
            

    def sync(self, remote : str, branch : str = "master", r_branch : str = "master"):
        #TODO: failed and resume?
        #TODO: specify local and remote branch
        logger.info("Sync git repo at {}", self.path)
        if self.is_dirty():
            logger.info("Found changes, commit them first")
            self.auto_commit()
        yassert(not self.is_dirty())
        yassert(self.has_remote(remote))
        if r_branch is None:
            r_branch = branch
        logger.info("Fetch remote {}/{}", remote, r_branch)
        self.fetch(remote, r_branch)
        if self.diff( branch, f"{remote}/{r_branch}"):
            logger.info("Merge remote branch {}/{} to current branch", remote, branch)
            self.merge(f"{remote}/{branch}")

        if self.diff( branch, f"{remote}/{r_branch}"):
            logger.info("Push local change to remote")
            self.push(remote)

        
