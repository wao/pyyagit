from yagit.git_repo import BranchDivertError, NoBranchError, StatusResult
import pytest

MSG_NO_COMMIT = "## No commits yet on master"
MSG_NO_REMOTE = "## master"
MSG_SAME_REMOTE = "## master...origin/master"
MSG_AHEAD_REMOTE = "## master...origin/master [ahead 1]"
MSG_BEHIND_REMOTE = "## react_pdf_js...origin/master [behind 38]"
MSG_DIVERT_REMOTE = "## master...origin/master [ahead 1, behind 1]"
MSG_DETACH = "## HEAD (no branch)"
MSG_WITH_DOT = "## v5.6.4.2...origin/v5.6.4.2"


def test_status_result():
    s1 = StatusResult.from_stdout(MSG_NO_REMOTE)
    assert not s1.is_track 
    assert not s1.is_dirty
    assert s1.local_branch == "master"
    with pytest.raises(AssertionError):
        s1.track_info

    s1 = StatusResult.from_stdout(MSG_NO_COMMIT)
    assert not s1.is_track 
    assert not s1.is_dirty
    assert s1.local_branch == "master"

    s1 = StatusResult.from_stdout(MSG_SAME_REMOTE)
    assert s1.is_track 
    assert s1.track_info.patch_count == 0
    assert not s1.is_dirty
    assert s1.local_branch == "master"
    assert s1.track_info.remote == "origin"
    assert s1.track_info.remote_branch == "master"

    s1 = StatusResult.from_stdout(MSG_AHEAD_REMOTE)
    assert s1.is_track 
    assert s1.track_info.patch_count == 1
    assert not s1.is_dirty
    assert s1.local_branch == "master"
    assert s1.track_info.remote == "origin"
    assert s1.track_info.remote_branch == "master"

    s1 = StatusResult.from_stdout(MSG_BEHIND_REMOTE)
    assert s1.is_track 
    assert not s1.track_info.is_ahead
    assert s1.track_info.is_behind
    assert not s1.track_info.is_divert 
    assert s1.track_info.patch_count == -38
    assert not s1.is_dirty
    assert s1.local_branch == "react_pdf_js"
    assert s1.track_info.remote == "origin"
    assert s1.track_info.remote_branch == "master"

    s1 = StatusResult.from_stdout(MSG_DIVERT_REMOTE)
    assert s1.is_track 
    assert s1.track_info.is_divert 
    with pytest.raises(BranchDivertError):
        s1.track_info.patch_count
    with pytest.raises(BranchDivertError):
        s1.track_info.is_ahead
    with pytest.raises(BranchDivertError):
        s1.track_info.is_behind
    assert not s1.is_dirty
    assert s1.local_branch == "master"
    assert s1.track_info.remote == "origin"
    assert s1.track_info.remote_branch == "master"

    s1 = StatusResult.from_stdout("\n".join([MSG_NO_REMOTE, "M xxx"]))
    assert not s1.is_track 
    assert s1.is_dirty
    assert s1.local_branch == "master"

def test_name_with_dot():
    s1 = StatusResult.from_stdout(MSG_WITH_DOT)
    assert s1.is_track 
    assert s1.local_branch == "v5.6.4.2"
    assert s1.track_info.remote == "origin"
    assert s1.track_info.remote_branch == "v5.6.4.2"

def test_name_detach():
    s1 = StatusResult.from_stdout(MSG_DETACH)
    assert not s1.is_track 
    assert s1.is_detach
    with pytest.raises(NoBranchError):
        s1.local_branch
