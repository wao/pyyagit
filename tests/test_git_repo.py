from yagit.git_repo import GitRepo, MergeConflictError
import pytest
from loguru import logger
import sh
from pathlib import Path
from upath import UPath

def test_hello():
    assert True



def do_simple_git_create(tmp_path:Path):
    logger.info("simple git path {}", tmp_path)
    git_root2 = tmp_path / "git12"
    git_root2.mkdir()
    assert git_root2.exists()
    assert not GitRepo.is_git(git_root2)

    git_root = tmp_path / "git1"
    assert not GitRepo.is_git(git_root)
    GitRepo.create(git_root)
    assert GitRepo.is_git(git_root)
    assert not  GitRepo.is_bare_git(git_root)

    git_root3 = tmp_path / "git2"
    assert not GitRepo.is_git(git_root3)
    GitRepo.create(git_root3, True)
    assert not GitRepo.is_git(git_root3)
    assert GitRepo.is_bare_git(git_root3)

def test_git_create(tmp_path):
    do_simple_git_create(tmp_path)

def test_ssh_git_create(tmp_path):
    do_simple_git_create(UPath(f"ssh://127.0.0.1{tmp_path}"))

@pytest.fixture
def git_repo(tmp_path):
    git_root = tmp_path / "git1"
    return GitRepo.create(git_root)

@pytest.fixture
def ssh_git_repo(tmp_path):
    git_root = UPath( f"ssh://127.0.0.1/{tmp_path}") / "sshgit1"
    return GitRepo.create(git_root)

@pytest.fixture
def git_repo2(tmp_path):
    git_root = tmp_path / "git2"
    return  GitRepo.create(git_root)

@pytest.fixture
def ssh_git_repo2(tmp_path):
    git_root = UPath( f"ssh://127.0.0.1/{tmp_path}") / "sshgit2"
    return  GitRepo.create(git_root)

@pytest.fixture
def bare_repo(tmp_path):
    git_root = tmp_path / "bare"
    return  GitRepo.create(git_root, True)

@pytest.fixture
def ssh_bare_repo(tmp_path):
    git_root = UPath( f"ssh://127.0.0.1/{tmp_path}") / "sshbare"
    return  GitRepo.create(git_root, True)


def do_test_git_dirty(git_repo):
    assert not git_repo.is_dirty()
    (git_repo.path / "test.txt").write_text("hello world!")
    assert git_repo.is_dirty()

def test_git_dirty(git_repo, ssh_git_repo):
    do_test_git_dirty(git_repo)
    do_test_git_dirty(ssh_git_repo)

def do_fetch_push(git_repo, git_repo2, bare_repo):
    git_repo.add_remote("origin", bare_repo.path)
    git_repo2.add_remote("origin", bare_repo.path)
    (git_repo.path / "test.txt").write_text("hello world!")
    git_repo.auto_commit()
    assert not git_repo.is_dirty()
    git_repo.push("origin", set_upstream=True)
    target = git_repo2.path/"test.txt"
    assert not target.exists()
    git_repo2.fetch("origin")
    git_repo2.merge("origin/master") 
    git_repo2.set_upstream_branch("origin", "master")
    assert target.exists()

def test_fetch_push(git_repo, git_repo2, bare_repo):
    do_fetch_push(git_repo, git_repo2, bare_repo)

def test_ssh_fetch_push(ssh_git_repo, ssh_git_repo2, ssh_bare_repo):
    do_fetch_push(ssh_git_repo, ssh_git_repo2, ssh_bare_repo)

def test_conflict(git_repo, git_repo2, bare_repo):
    do_fetch_push(git_repo, git_repo2, bare_repo)
    (git_repo.path / "test.txt").write_text("hello world2!")
    git_repo.auto_commit()
    git_repo.push("origin")
    assert not git_repo.diff("master", "origin/master")
    (git_repo2.path / "test.txt").write_text("hello world3!")
    git_repo2.auto_commit()
    git_repo2.fetch("origin")
    with pytest.raises(MergeConflictError):
        git_repo2.merge("origin/master") 
    with pytest.raises(MergeConflictError):
        git_repo2.auto_commit()

def test_diff(git_repo, git_repo2, bare_repo):
    git_repo.add_remote("origin", bare_repo.path)
    git_repo2.add_remote("origin", bare_repo.path)
    (git_repo.path / "test.txt").write_text("hello world!")
    git_repo.auto_commit()
    git_repo.push("origin")
    assert not git_repo.diff("master", "origin/master")
    (git_repo.path / "test.txt").write_text("hello world2!")
    git_repo.auto_commit()
    assert git_repo.diff("master", "origin/master")
    git_repo.push("origin")
    assert not git_repo.diff("master", "origin/master")


def test_status(git_repo, git_repo2, bare_repo):
    s1 = git_repo.status()
    assert not s1.is_track
    assert not s1.is_dirty
    do_fetch_push(git_repo, git_repo2, bare_repo)
    s1 = git_repo.status()
    assert s1.is_track
    assert s1.track_info.remote == "origin"
    assert s1.track_info.remote_branch == "master"
    assert s1.track_info.patch_count == 0
    assert not s1.is_dirty
    (git_repo.path / "test.txt").write_text("hello world2!")
    s1 = git_repo.status()
    assert s1.is_track
    assert s1.is_dirty
    git_repo.auto_commit()
    s1 = git_repo.status()
    assert not s1.is_dirty
    assert s1.track_info.patch_count == 1 
    git_repo.push("origin")
    s1 = git_repo.status()
    assert s1.track_info.patch_count == 0
    git_repo2.fetch("origin")
    print(git_repo2.path)
    s1 = git_repo2.status()
    assert s1.track_info.patch_count == -1
