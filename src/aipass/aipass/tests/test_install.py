# =================== AIPass ====================
# Name: test_install.py
# Description: Tests for aipass install — one-command bootstrap (DPLAN-0233)
# Version: 1.0.0
# Created: 2026-07-05
# Modified: 2026-07-05
# =============================================

"""Tests for the aipass install module (DPLAN-0233)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aipass.aipass.apps.modules.install import (
    DEFAULT_HOME,
    DEFAULT_PROJECT,
    TOTAL_STEPS,
    _clone_repo,
    _handoff_to_init,
    _looks_like_aipass_tree,
    _resolve_home,
    _resolve_project_dir,
    _run_setup,
    _should_run_init,
    handle_command,
    print_help,
    print_introspection,
    run_install,
)

_MOD = "aipass.aipass.apps.modules.install"


class TestLooksLikeAipassTree:
    """Detecting whether a directory already holds an AIPass source tree."""

    def test_setup_sh_present(self, tmp_path: Path) -> None:
        """A directory with setup.sh reads as an AIPass tree."""
        (tmp_path / "setup.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        assert _looks_like_aipass_tree(tmp_path) is True

    def test_registry_present(self, tmp_path: Path) -> None:
        """A directory with a *_REGISTRY.json reads as an AIPass tree."""
        (tmp_path / "MYPROJ_REGISTRY.json").write_text("{}", encoding="utf-8")
        assert _looks_like_aipass_tree(tmp_path) is True

    def test_empty_dir(self, tmp_path: Path) -> None:
        """An empty directory is not an AIPass tree."""
        assert _looks_like_aipass_tree(tmp_path) is False

    def test_missing_dir(self, tmp_path: Path) -> None:
        """A non-existent path is not an AIPass tree."""
        assert _looks_like_aipass_tree(tmp_path / "nope") is False


class TestResolveHome:
    """Resolving the install home from flags, env, and defaults."""

    def test_here_returns_cwd(self, tmp_path: Path) -> None:
        """--here resolves to the current working directory."""
        with patch(f"{_MOD}.Path.cwd", return_value=tmp_path):
            assert _resolve_home(None, here=True, non_interactive=False) == tmp_path.resolve()

    def test_explicit_path(self, tmp_path: Path) -> None:
        """An explicit --path is expanded and resolved."""
        target = tmp_path / "tools" / "aipass"
        assert _resolve_home(str(target), here=False, non_interactive=False) == target.resolve()

    def test_non_interactive_defaults(self) -> None:
        """With no AIPASS_HOME, non-interactive falls back to DEFAULT_HOME."""
        with patch.dict("os.environ", {"AIPASS_HOME": ""}, clear=False):
            assert _resolve_home(None, here=False, non_interactive=True) == DEFAULT_HOME.resolve()

    def test_uses_valid_env(self, tmp_path: Path) -> None:
        """A valid AIPASS_HOME pointing at a real tree is honoured."""
        (tmp_path / "setup.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        with patch.dict("os.environ", {"AIPASS_HOME": str(tmp_path)}, clear=False):
            assert _resolve_home(None, here=False, non_interactive=True) == tmp_path.resolve()

    def test_ignores_invalid_env(self, tmp_path: Path) -> None:
        """An AIPASS_HOME that is not an AIPass tree is ignored for the default."""
        with patch.dict("os.environ", {"AIPASS_HOME": str(tmp_path)}, clear=False):
            assert _resolve_home(None, here=False, non_interactive=True) == DEFAULT_HOME.resolve()


class TestCloneRepo:
    """Fetching the framework into the home via git clone."""

    def test_dry_run_no_subprocess(self, tmp_path: Path) -> None:
        """Dry-run reports success without shelling out."""
        with patch(f"{_MOD}.subprocess.run") as run:
            assert _clone_repo(tmp_path / "home", dry_run=True) is True
            run.assert_not_called()

    def test_refuses_non_empty_dir(self, tmp_path: Path) -> None:
        """A non-empty target is refused rather than clobbered."""
        (tmp_path / "existing.txt").write_text("x", encoding="utf-8")
        with patch(f"{_MOD}.subprocess.run") as run:
            assert _clone_repo(tmp_path, dry_run=False) is False
            run.assert_not_called()

    def test_missing_git(self, tmp_path: Path) -> None:
        """Absent git means clone fails cleanly without calling subprocess."""
        with patch(f"{_MOD}.shutil.which", return_value=None), patch(f"{_MOD}.subprocess.run") as run:
            assert _clone_repo(tmp_path / "home", dry_run=False) is False
            run.assert_not_called()

    def test_success(self, tmp_path: Path) -> None:
        """A zero-exit git clone returns success."""
        with (
            patch(f"{_MOD}.shutil.which", return_value="/usr/bin/git"),
            patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=0)) as run,
        ):
            assert _clone_repo(tmp_path / "home", dry_run=False) is True
            run.assert_called_once()

    def test_nonzero_exit(self, tmp_path: Path) -> None:
        """A non-zero git clone exit reports failure."""
        with (
            patch(f"{_MOD}.shutil.which", return_value="/usr/bin/git"),
            patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=1)),
        ):
            assert _clone_repo(tmp_path / "home", dry_run=False) is False


class TestRunSetup:
    """Running the repo setup.sh."""

    def test_dry_run_no_subprocess(self, tmp_path: Path) -> None:
        """Dry-run reports success without running setup.sh."""
        (tmp_path / "setup.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        with patch(f"{_MOD}.subprocess.run") as run:
            assert _run_setup(tmp_path, dry_run=True) is True
            run.assert_not_called()

    def test_missing_script(self, tmp_path: Path) -> None:
        """A missing setup.sh reports failure."""
        assert _run_setup(tmp_path, dry_run=False) is False

    def test_success(self, tmp_path: Path) -> None:
        """A zero-exit setup.sh returns success."""
        (tmp_path / "setup.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        with patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=0)) as run:
            assert _run_setup(tmp_path, dry_run=False) is True
            run.assert_called_once()

    def test_no_symlink_flag_forwarded(self, tmp_path: Path) -> None:
        """--no-symlink passes through to setup.sh (#660)."""
        (tmp_path / "setup.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        with patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=0)) as run:
            assert _run_setup(tmp_path, dry_run=False, no_symlink=True) is True
        argv = run.call_args[0][0]
        assert "--no-symlink" in argv
        assert "--force-symlink" not in argv

    def test_force_symlink_flag_forwarded(self, tmp_path: Path) -> None:
        """--force-symlink passes through to setup.sh (#660)."""
        (tmp_path / "setup.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        with patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=0)) as run:
            assert _run_setup(tmp_path, dry_run=False, force_symlink=True) is True
        argv = run.call_args[0][0]
        assert "--force-symlink" in argv

    def test_symlink_flags_absent_by_default(self, tmp_path: Path) -> None:
        """No symlink flags forwarded unless requested (#660)."""
        (tmp_path / "setup.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        with patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=0)) as run:
            assert _run_setup(tmp_path, dry_run=False) is True
        argv = run.call_args[0][0]
        assert "--no-symlink" not in argv
        assert "--force-symlink" not in argv


class TestRunInstall:
    """The four-step orchestrator."""

    def test_dry_run_is_side_effect_free(self) -> None:
        """Dry-run walks all steps and touches no subprocess."""
        with patch(f"{_MOD}.subprocess.run") as run:
            rc = run_install(non_interactive=True, dry_run=True)
        assert rc == 0
        run.assert_not_called()

    def test_aborts_when_clone_fails(self, tmp_path: Path) -> None:
        """A failed fetch aborts before the setup step runs."""
        home = tmp_path / "AIPass"
        with (
            patch(f"{_MOD}._resolve_home", return_value=home),
            patch(f"{_MOD}._clone_repo", return_value=False),
            patch(f"{_MOD}._run_setup") as setup,
        ):
            rc = run_install(non_interactive=True, dry_run=False)
        assert rc == 1
        setup.assert_not_called()

    def test_full_happy_path(self, tmp_path: Path) -> None:
        """Clone + setup + verify + next-steps returns success."""
        home = tmp_path / "AIPass"
        with (
            patch(f"{_MOD}._resolve_home", return_value=home),
            patch(f"{_MOD}.is_throwaway_path", return_value=False),
            patch(f"{_MOD}._clone_repo", return_value=True),
            patch(f"{_MOD}._run_setup", return_value=True),
            patch(f"{_MOD}._verify_binaries", return_value={"drone": "/x/drone", "aipass": "/x/aipass"}),
            patch(f"{_MOD}._handoff_to_init") as nxt,
        ):
            rc = run_install(non_interactive=True, dry_run=False)
        assert rc == 0
        nxt.assert_called_once()


class TestShouldRunInit:
    """Deciding whether the install chains into init."""

    def test_no_init_wins(self) -> None:
        """--no-init disables the handoff even alongside --with-init."""
        assert _should_run_init(non_interactive=False, with_init=True, no_init=True) is False

    def test_with_init_forces_headless(self) -> None:
        """--with-init runs init even when the install was headless."""
        assert _should_run_init(non_interactive=True, with_init=True, no_init=False) is True

    def test_headless_defaults_off(self) -> None:
        """A plain headless install stops before init."""
        assert _should_run_init(non_interactive=True, with_init=False, no_init=False) is False

    def test_interactive_defaults_on(self) -> None:
        """A plain interactive install chains into init."""
        assert _should_run_init(non_interactive=False, with_init=False, no_init=False) is True


class TestResolveProjectDir:
    """Resolving where the first project scaffolds."""

    def test_explicit_project(self, tmp_path: Path) -> None:
        """An explicit --project is expanded and resolved."""
        target = tmp_path / "proj"
        assert _resolve_project_dir(str(target), non_interactive=True) == target.resolve()

    def test_headless_defaults(self) -> None:
        """Headless with no --project falls back to DEFAULT_PROJECT."""
        assert _resolve_project_dir(None, non_interactive=True) == DEFAULT_PROJECT.resolve()


class TestHandoffToInit:
    """The init handoff step."""

    def test_skips_when_not_running(self, tmp_path: Path) -> None:
        """run_it=False prints next steps and launches nothing."""
        with patch(f"{_MOD}.subprocess.run") as run:
            _handoff_to_init(tmp_path, "/x/aipass", non_interactive=True, dry_run=False, project=None, run_it=False)
        run.assert_not_called()

    def test_dry_run_no_subprocess(self, tmp_path: Path) -> None:
        """Dry-run announces the launch but does not spawn init."""
        with patch(f"{_MOD}.subprocess.run") as run:
            _handoff_to_init(
                tmp_path, "/x/aipass", non_interactive=True, dry_run=True, project=str(tmp_path / "p"), run_it=True
            )
        run.assert_not_called()

    def test_launches_init_headless(self, tmp_path: Path) -> None:
        """A real headless handoff launches `aipass init run --non-interactive` in the project dir."""
        project = tmp_path / "proj"
        with patch(f"{_MOD}.subprocess.run") as run:
            _handoff_to_init(
                tmp_path, "/x/aipass", non_interactive=True, dry_run=False, project=str(project), run_it=True
            )
        run.assert_called_once()
        cmd = run.call_args.args[0]
        assert cmd == ["/x/aipass", "init", "run", "--non-interactive"]
        assert run.call_args.kwargs["cwd"] == str(project)

    def test_missing_binary_warns_not_crashes(self, tmp_path: Path) -> None:
        """No aipass binary → warn, don't launch, don't raise."""
        with patch(f"{_MOD}.subprocess.run") as run:
            _handoff_to_init(
                tmp_path, None, non_interactive=True, dry_run=False, project=str(tmp_path / "p"), run_it=True
            )
        run.assert_not_called()


class TestHandleCommand:
    """Command routing for `aipass install`."""

    def test_ignores_other_commands(self) -> None:
        """A non-install command is not handled here."""
        assert handle_command("doctor", []) is False

    def test_help(self) -> None:
        """--help is handled without exiting."""
        assert handle_command("install", ["--help"]) is True

    def test_info(self) -> None:
        """--info is handled without exiting."""
        assert handle_command("install", ["--info"]) is True

    def test_runs_and_exits(self) -> None:
        """A run request calls run_install and exits with its code."""
        with patch(f"{_MOD}.run_install", return_value=0) as run:
            with pytest.raises(SystemExit) as exc:
                handle_command("install", ["--dry-run", "--non-interactive"])
        assert exc.value.code == 0
        run.assert_called_once()

    def test_passes_path_flag(self) -> None:
        """--path and --non-interactive are threaded into run_install."""
        target = str(Path.home() / "custom-aipass-home")
        with patch(f"{_MOD}.run_install", return_value=0) as run:
            with pytest.raises(SystemExit):
                handle_command("install", ["--path", target, "--non-interactive"])
        _, kwargs = run.call_args
        assert kwargs["path"] == target
        assert kwargs["non_interactive"] is True

    def test_passes_init_flags(self) -> None:
        """--with-init / --no-init / --project are threaded into run_install."""
        with patch(f"{_MOD}.run_install", return_value=0) as run:
            with pytest.raises(SystemExit):
                handle_command("install", ["--with-init", "--no-init", "--project", "/x/proj"])
        _, kwargs = run.call_args
        assert kwargs["with_init"] is True
        assert kwargs["no_init"] is True
        assert kwargs["project"] == "/x/proj"


class TestSmoke:
    """Help/introspection render and constants hold."""

    def test_print_help_runs(self) -> None:
        """print_help renders without error."""
        print_help()

    def test_print_introspection_runs(self) -> None:
        """print_introspection renders without error."""
        print_introspection()

    def test_total_steps_constant(self) -> None:
        """The install flow advertises four steps."""
        assert TOTAL_STEPS == 4


# ---------------------------------------------------------------------------
# Throwaway-path gate (#688)
# ---------------------------------------------------------------------------


class TestThrowawayGate:
    """Install refuses throwaway homes unless --force-global-home."""

    def test_refuses_tmp_home(self, tmp_path) -> None:
        """run_install returns 1 when home resolves to a temp path."""
        with (
            patch(
                "aipass.aipass.apps.modules.install._resolve_home",
                return_value=tmp_path,
            ),
            patch("aipass.aipass.apps.modules.install.sys.argv", ["aipass", "install"]),
        ):
            result = run_install(non_interactive=True, no_init=True)
        assert result == 1

    def test_force_flag_overrides(self, tmp_path) -> None:
        """--force-global-home lets a temp home proceed past the gate."""
        with (
            patch(
                "aipass.aipass.apps.modules.install._resolve_home",
                return_value=tmp_path,
            ),
            patch(
                "aipass.aipass.apps.modules.install.sys.argv",
                ["aipass", "install", "--force-global-home"],
            ),
            patch(
                "aipass.aipass.apps.modules.install._looks_like_aipass_tree",
                return_value=True,
            ),
            patch(
                "aipass.aipass.apps.modules.install._run_setup",
                return_value=True,
            ),
            patch(
                "aipass.aipass.apps.modules.install._verify_binaries",
                return_value={"drone": "x", "aipass": "x"},
            ),
            patch("aipass.aipass.apps.modules.install._handoff_to_init"),
        ):
            result = run_install(non_interactive=True, no_init=True)
        assert result == 0
