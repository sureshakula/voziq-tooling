"""
Unit tests for routing core functionality.

Tests all Phase 1 routing functions with >80% coverage target.
"""

import json
import tempfile
from pathlib import Path

import pytest

from aipass.routing import (
    BranchAlreadyExistsError,
    BranchNotFoundError,
    InvalidPathError,
    RegistryNotFoundError,
    branch_exists,
    get_branch_info,
    get_registry_path,
    initialize_registry,
    list_branches,
    register_branch,
    reset_registry_path,
    resolve_branch,
    set_registry_path,
)


@pytest.fixture
def temp_registry(tmp_path):
    """Create a temporary registry for testing."""
    registry_path = tmp_path / "test_registry.json"
    set_registry_path(registry_path)
    initialize_registry()
    yield registry_path
    reset_registry_path()


@pytest.fixture
def sample_branches(tmp_path):
    """Create sample branch directories for testing."""
    branches = {}
    for name in ["agent1", "agent2", "service1"]:
        branch_dir = tmp_path / "branches" / name
        branch_dir.mkdir(parents=True, exist_ok=True)
        branches[name] = branch_dir
    return branches


class TestConfiguration:
    """Test registry configuration."""

    def test_default_registry_path(self):
        """Test default registry path is ~/.aipass/BRANCH_REGISTRY.json."""
        reset_registry_path()
        path = get_registry_path()
        assert path == Path.home() / ".aipass" / "BRANCH_REGISTRY.json"

    def test_set_custom_registry_path(self, tmp_path):
        """Test setting custom registry path."""
        custom_path = tmp_path / "custom_registry.json"
        set_registry_path(custom_path)
        assert get_registry_path() == custom_path
        reset_registry_path()

    def test_reset_registry_path(self, tmp_path):
        """Test resetting registry path to default."""
        custom_path = tmp_path / "custom_registry.json"
        set_registry_path(custom_path)
        reset_registry_path()
        path = get_registry_path()
        assert path == Path.home() / ".aipass" / "BRANCH_REGISTRY.json"


class TestRegistryInitialization:
    """Test registry initialization."""

    def test_initialize_creates_registry(self, tmp_path):
        """Test initialize_registry creates valid registry file."""
        registry_path = tmp_path / "new_registry.json"
        set_registry_path(registry_path)

        initialize_registry()

        assert registry_path.exists()
        with open(registry_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert "branches" in data
        assert isinstance(data["branches"], dict)
        assert "metadata" in data

        reset_registry_path()

    def test_initialize_idempotent(self, temp_registry):
        """Test initialize_registry is idempotent (safe to call multiple times)."""
        # First initialization done by fixture
        first_content = temp_registry.read_text()

        # Second initialization should not change anything
        initialize_registry()
        second_content = temp_registry.read_text()

        assert first_content == second_content


class TestBranchRegistration:
    """Test branch registration functionality."""

    def test_register_branch_basic(self, temp_registry, sample_branches):
        """Test basic branch registration."""
        branch_path = sample_branches["agent1"]
        register_branch("agent1", str(branch_path), "agent")

        # Verify branch was added
        with open(temp_registry, encoding="utf-8") as f:
            data = json.load(f)

        assert "agent1" in data["branches"]
        branch = data["branches"]["agent1"]
        assert branch["name"] == "agent1"
        assert Path(branch["path"]) == branch_path
        assert branch["type"] == "agent"
        assert branch["status"] == "active"
        assert "created" in branch

    def test_register_branch_with_path_object(self, temp_registry, sample_branches):
        """Test branch registration with Path object."""
        branch_path = sample_branches["agent1"]
        register_branch("agent1", branch_path, "agent")

        assert branch_exists("agent1")

    def test_register_branch_duplicate_raises_error(self, temp_registry, sample_branches):
        """Test registering duplicate branch raises error."""
        branch_path = sample_branches["agent1"]
        register_branch("agent1", str(branch_path), "agent")

        with pytest.raises(BranchAlreadyExistsError):
            register_branch("agent1", str(branch_path), "agent")

    def test_register_branch_nonexistent_path_raises_error(self, temp_registry):
        """Test registering nonexistent path raises error."""
        fake_path = "/nonexistent/path/to/branch"

        with pytest.raises(InvalidPathError):
            register_branch("fake_branch", fake_path, "agent")

    def test_register_branch_file_not_directory_raises_error(self, temp_registry, tmp_path):
        """Test registering a file instead of directory raises error."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        with pytest.raises(InvalidPathError):
            register_branch("bad_branch", str(file_path), "agent")

    def test_register_branch_auto_initializes_registry(self, tmp_path):
        """Test registering branch auto-initializes registry if it doesn't exist."""
        registry_path = tmp_path / "new_registry.json"
        set_registry_path(registry_path)

        # Registry doesn't exist yet
        assert not registry_path.exists()

        # Register branch should auto-initialize
        branch_path = tmp_path / "agent"
        branch_path.mkdir()
        register_branch("agent", str(branch_path), "agent")

        # Registry should now exist
        assert registry_path.exists()
        assert branch_exists("agent")

        reset_registry_path()


class TestBranchResolution:
    """Test branch resolution functionality."""

    def test_resolve_branch_with_at_prefix(self, temp_registry, sample_branches):
        """Test resolving branch with @ prefix."""
        branch_path = sample_branches["agent1"]
        register_branch("agent1", str(branch_path), "agent")

        resolved = resolve_branch("@agent1")
        assert Path(resolved) == branch_path

    def test_resolve_branch_without_at_prefix(self, temp_registry, sample_branches):
        """Test resolving branch without @ prefix."""
        branch_path = sample_branches["agent1"]
        register_branch("agent1", str(branch_path), "agent")

        resolved = resolve_branch("agent1")
        assert Path(resolved) == branch_path

    def test_resolve_branch_not_found_raises_error(self, temp_registry):
        """Test resolving nonexistent branch raises error."""
        with pytest.raises(BranchNotFoundError):
            resolve_branch("@nonexistent")

    def test_resolve_branch_no_registry_raises_error(self, tmp_path):
        """Test resolving branch without registry raises error."""
        registry_path = tmp_path / "missing_registry.json"
        set_registry_path(registry_path)

        with pytest.raises(RegistryNotFoundError):
            resolve_branch("@agent1")

        reset_registry_path()


class TestBranchExists:
    """Test branch existence checking."""

    def test_branch_exists_true(self, temp_registry, sample_branches):
        """Test branch_exists returns True for registered branch."""
        branch_path = sample_branches["agent1"]
        register_branch("agent1", str(branch_path), "agent")

        assert branch_exists("@agent1")
        assert branch_exists("agent1")

    def test_branch_exists_false(self, temp_registry):
        """Test branch_exists returns False for unregistered branch."""
        assert not branch_exists("@nonexistent")
        assert not branch_exists("nonexistent")

    def test_branch_exists_no_registry_returns_false(self, tmp_path):
        """Test branch_exists returns False when registry doesn't exist."""
        registry_path = tmp_path / "missing_registry.json"
        set_registry_path(registry_path)

        assert not branch_exists("@agent1")

        reset_registry_path()


class TestBranchInfo:
    """Test branch metadata retrieval."""

    def test_get_branch_info_basic(self, temp_registry, sample_branches):
        """Test getting branch info."""
        branch_path = sample_branches["agent1"]
        register_branch("agent1", str(branch_path), "agent")

        info = get_branch_info("@agent1")

        assert info["name"] == "agent1"
        assert Path(info["path"]) == branch_path
        assert info["type"] == "agent"
        assert info["status"] == "active"
        assert "created" in info

    def test_get_branch_info_without_at_prefix(self, temp_registry, sample_branches):
        """Test getting branch info without @ prefix."""
        branch_path = sample_branches["agent1"]
        register_branch("agent1", str(branch_path), "agent")

        info = get_branch_info("agent1")
        assert info["name"] == "agent1"

    def test_get_branch_info_not_found_raises_error(self, temp_registry):
        """Test getting info for nonexistent branch raises error."""
        with pytest.raises(BranchNotFoundError):
            get_branch_info("@nonexistent")


class TestListBranches:
    """Test branch listing functionality."""

    def test_list_branches_all(self, temp_registry, sample_branches):
        """Test listing all branches."""
        register_branch("agent1", str(sample_branches["agent1"]), "agent")
        register_branch("agent2", str(sample_branches["agent2"]), "agent")
        register_branch("service1", str(sample_branches["service1"]), "service")

        branches = list_branches()

        assert "@agent1" in branches
        assert "@agent2" in branches
        assert "@service1" in branches
        assert len(branches) == 3

    def test_list_branches_by_type(self, temp_registry, sample_branches):
        """Test listing branches filtered by type."""
        register_branch("agent1", str(sample_branches["agent1"]), "agent")
        register_branch("agent2", str(sample_branches["agent2"]), "agent")
        register_branch("service1", str(sample_branches["service1"]), "service")

        agents = list_branches(branch_type="agent")
        services = list_branches(branch_type="service")

        assert "@agent1" in agents
        assert "@agent2" in agents
        assert "@service1" not in agents
        assert len(agents) == 2

        assert "@service1" in services
        assert "@agent1" not in services
        assert len(services) == 1

    def test_list_branches_empty_registry(self, temp_registry):
        """Test listing branches with empty registry."""
        branches = list_branches()
        assert branches == []

    def test_list_branches_no_registry(self, tmp_path):
        """Test listing branches when registry doesn't exist."""
        registry_path = tmp_path / "missing_registry.json"
        set_registry_path(registry_path)

        branches = list_branches()
        assert branches == []

        reset_registry_path()


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_corrupt_registry_raises_error(self, tmp_path):
        """Test corrupted registry file raises error."""
        registry_path = tmp_path / "corrupt_registry.json"
        registry_path.write_text("invalid json {{{")

        set_registry_path(registry_path)

        with pytest.raises(Exception):  # RegistryCorruptError or similar
            resolve_branch("@agent1")

        reset_registry_path()

    def test_missing_branches_field_raises_error(self, tmp_path):
        """Test registry missing 'branches' field raises error."""
        registry_path = tmp_path / "bad_registry.json"
        registry_path.write_text(json.dumps({"version": "1.0"}))

        set_registry_path(registry_path)

        with pytest.raises(Exception):  # RegistryCorruptError
            resolve_branch("@agent1")

        reset_registry_path()


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow: initialize → register → resolve → list → exists."""
        # Setup
        registry_path = tmp_path / "registry.json"
        set_registry_path(registry_path)
        initialize_registry()

        # Create branch directories
        agent1_path = tmp_path / "agent1"
        agent1_path.mkdir()
        agent2_path = tmp_path / "agent2"
        agent2_path.mkdir()

        # Register branches
        register_branch("agent1", str(agent1_path), "agent")
        register_branch("agent2", str(agent2_path), "agent")

        # Verify existence
        assert branch_exists("@agent1")
        assert branch_exists("@agent2")
        assert not branch_exists("@agent3")

        # Resolve paths
        resolved1 = resolve_branch("@agent1")
        resolved2 = resolve_branch("agent2")
        assert Path(resolved1) == agent1_path
        assert Path(resolved2) == agent2_path

        # Get info
        info = get_branch_info("@agent1")
        assert info["name"] == "agent1"
        assert info["type"] == "agent"

        # List branches
        branches = list_branches()
        assert len(branches) == 2
        assert "@agent1" in branches
        assert "@agent2" in branches

        # Cleanup
        reset_registry_path()
