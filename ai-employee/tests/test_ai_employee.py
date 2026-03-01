"""
AI Employee Test Suite

Bronze Tier Test Cases

This module contains unit tests and integration tests for the AI Employee system.
Run with: pytest tests/ -v
"""

import pytest
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


# ===========================================
# Fixtures
# ===========================================

@pytest.fixture
def temp_vault():
    """Create a temporary vault for testing."""
    vault_path = Path(tempfile.mkdtemp())
    
    # Create folder structure
    folders = [
        'Inbox',
        'Needs_Action',
        'Plans',
        'Done',
        'Pending_Approval',
        'Approved',
        'Rejected',
        'Logs',
        'Briefings',
        'Accounting',
        '.cache'
    ]
    
    for folder in folders:
        (vault_path / folder).mkdir(parents=True, exist_ok=True)
    
    yield vault_path
    
    # Cleanup
    shutil.rmtree(vault_path)


@pytest.fixture
def sample_email_content():
    """Sample email action file content."""
    return """---
type: email
from: test@example.com
subject: Test Email
received: 2026-02-28T10:00:00
priority: high
status: pending
---

## Content

This is a test email for testing purposes.

## Suggested Actions
- [ ] Reply to sender
- [ ] Archive after processing
"""


@pytest.fixture
def sample_plan_content():
    """Sample plan file content."""
    return """---
type: plan
created: 2026-02-28T10:00:00
status: pending
---

# Plan

## Action Items
- [ ] Test item 1
- [ ] Test item 2
"""


# ===========================================
# Base Watcher Tests
# ===========================================

class TestBaseWatcher:
    """Tests for BaseWatcher class."""
    
    def test_base_watcher_initialization(self, temp_vault):
        """Test BaseWatcher initializes correctly."""
        from watchers.base_watcher import BaseWatcher
        
        # Can't instantiate abstract class directly
        with pytest.raises(TypeError):
            BaseWatcher(str(temp_vault))
    
    def test_base_watcher_creates_needs_action(self, temp_vault):
        """Test that Needs_Action folder is created."""
        from watchers.base_watcher import BaseWatcher
        
        # Create a concrete implementation for testing
        class TestWatcher(BaseWatcher):
            def check_for_updates(self):
                return []
            
            def create_action_file(self, item):
                return None
        
        watcher = TestWatcher(str(temp_vault))
        assert (temp_vault / 'Needs_Action').exists()
    
    def test_generate_filename(self, temp_vault):
        """Test filename generation."""
        from watchers.base_watcher import BaseWatcher
        
        class TestWatcher(BaseWatcher):
            def check_for_updates(self):
                return []
            
            def create_action_file(self, item):
                return None
        
        watcher = TestWatcher(str(temp_vault))
        filename = watcher._generate_filename('TEST', 'abc123')
        
        assert filename.startswith('TEST_abc123_')
        assert filename.endswith('.md')
    
    def test_create_action_file_content(self, temp_vault):
        """Test action file content generation."""
        from watchers.base_watcher import BaseWatcher
        
        class TestWatcher(BaseWatcher):
            def check_for_updates(self):
                return []
            
            def create_action_file(self, item):
                return None
        
        watcher = TestWatcher(str(temp_vault))
        
        metadata = {'type': 'test', 'status': 'pending'}
        content = 'Test content'
        actions = ['Action 1', 'Action 2']
        
        result = watcher._create_action_file_content(metadata, content, actions)
        
        assert '---' in result
        assert 'type: test' in result
        assert '## Content' in result
        assert '## Suggested Actions' in result
        assert '- [ ] Action 1' in result


# ===========================================
# Filesystem Watcher Tests
# ===========================================

class TestFilesystemWatcher:
    """Tests for FilesystemWatcher class."""
    
    def test_filesystem_watcher_initialization(self, temp_vault):
        """Test FilesystemWatcher initializes correctly."""
        from watchers.filesystem_watcher import FilesystemWatcher
        
        watcher = FilesystemWatcher(str(temp_vault))
        assert watcher is not None
        assert watcher.watch_folder.exists()
    
    def test_check_for_updates_empty(self, temp_vault):
        """Test check_for_updates with no files."""
        from watchers.filesystem_watcher import FilesystemWatcher
        
        watcher = FilesystemWatcher(str(temp_vault))
        updates = watcher.check_for_updates()
        
        assert isinstance(updates, list)
        assert len(updates) == 0
    
    def test_check_for_updates_with_file(self, temp_vault):
        """Test check_for_updates detects new files."""
        from watchers.filesystem_watcher import FilesystemWatcher
        
        # Create a test file
        test_file = temp_vault / 'Inbox' / 'test.txt'
        test_file.write_text('Test content')
        
        watcher = FilesystemWatcher(str(temp_vault))
        updates = watcher.check_for_updates()
        
        assert len(updates) == 1
        assert updates[0]['name'] == 'test.txt'
    
    def test_create_action_file(self, temp_vault):
        """Test action file creation."""
        from watchers.filesystem_watcher import FilesystemWatcher
        
        # Create a test file
        test_file = temp_vault / 'Inbox' / 'test.txt'
        test_file.write_text('Test content')
        
        watcher = FilesystemWatcher(str(temp_vault))
        
        item = {
            'path': str(test_file),
            'name': 'test.txt',
            'hash': 'abc123'
        }
        
        filepath = watcher.create_action_file(item)
        
        assert filepath.exists()
        assert filepath.parent == temp_vault / 'Needs_Action'
        assert 'FILE_' in filepath.name


# ===========================================
# Agent Skills Tests
# ===========================================

class TestProcessEmail:
    """Tests for process_email skill."""
    
    def test_read_frontmatter(self):
        """Test frontmatter parsing."""
        from skills.process_email import read_frontmatter
        
        content = """---
type: email
from: test@example.com
subject: Test
---

Body content
"""
        frontmatter = read_frontmatter(content)
        
        assert frontmatter['type'] == 'email'
        assert frontmatter['from'] == 'test@example.com'
        assert frontmatter['subject'] == 'Test'
    
    def test_analyze_email_financial(self):
        """Test email analysis for financial emails."""
        from skills.process_email import analyze_email
        
        frontmatter = {
            'from': 'vendor@example.com',
            'subject': 'Invoice #123',
            'priority': 'medium'
        }
        content = "Please find attached invoice for $750. Payment required immediately."
        
        analysis = analyze_email(frontmatter, content)
        
        assert analysis['category'] == 'financial'
        # Note: requires_approval is True for financial emails with urgency
        assert analysis['urgency_score'] > 0  # Has urgency keywords
    
    def test_analyze_email_urgent(self):
        """Test email analysis for urgent emails."""
        from skills.process_email import analyze_email
        
        frontmatter = {
            'from': 'client@example.com',
            'subject': 'URGENT: Need help',
            'priority': 'medium'
        }
        content = "This is urgent, need response ASAP"
        
        analysis = analyze_email(frontmatter, content)
        
        assert analysis['priority'] == 'high'
        assert analysis['urgency_score'] > 0
    
    def test_process_email_success(self, temp_vault, sample_email_content):
        """Test successful email processing."""
        from skills.process_email import process_email
        
        # Create email file
        email_file = temp_vault / 'Needs_Action' / 'EMAIL_test_20260228.md'
        email_file.write_text(sample_email_content)
        
        result = process_email(str(email_file), str(temp_vault))
        
        assert result['success'] == True
        assert result['plan_file'] is not None
        assert Path(result['plan_file']).exists()


class TestLogAction:
    """Tests for log_action skill."""
    
    def test_log_action_creates_entry(self, temp_vault):
        """Test that log_action creates an entry."""
        from skills.log_action import log_action, load_log_entries
        
        entry = log_action(
            vault_path=str(temp_vault),
            action_type='test_action',
            actor='test',
            target='test_target',
            result='success'
        )
        
        assert entry is not None
        assert entry.action_type == 'test_action'
        
        # Verify in file
        entries = load_log_entries(str(temp_vault))
        assert len(entries) == 1
        assert entries[0]['action_type'] == 'test_action'
    
    def test_get_recent_logs(self, temp_vault):
        """Test getting recent logs."""
        from skills.log_action import log_action, get_recent_logs
        
        # Create multiple entries
        for i in range(5):
            log_action(
                vault_path=str(temp_vault),
                action_type=f'test_{i}',
                actor='test',
                target='test',
                result='success'
            )
        
        recent = get_recent_logs(str(temp_vault), limit=3)
        assert len(recent) == 3


class TestUpdateDashboard:
    """Tests for update_dashboard skill."""
    
    def test_update_dashboard_creates_file(self, temp_vault):
        """Test dashboard update creates file."""
        from skills.update_dashboard import update_dashboard
        
        result = update_dashboard(str(temp_vault))
        
        assert result['success'] == True
        assert (temp_vault / 'Dashboard.md').exists()
    
    def test_update_dashboard_counts(self, temp_vault):
        """Test dashboard counts files correctly."""
        from skills.update_dashboard import update_dashboard
        
        # Create some test files
        (temp_vault / 'Needs_Action' / 'test1.md').write_text('test')
        (temp_vault / 'Needs_Action' / 'test2.md').write_text('test')
        (temp_vault / 'Pending_Approval' / 'test3.md').write_text('test')
        
        result = update_dashboard(str(temp_vault))
        
        assert result['counts']['pending_items'] == 2
        assert result['counts']['pending_approval'] == 1


class TestCreateApprovalRequest:
    """Tests for create_approval_request skill."""
    
    def test_create_approval_request(self, temp_vault):
        """Test approval request creation."""
        from skills.create_approval_request import create_approval_request
        
        result = create_approval_request(
            vault_path=str(temp_vault),
            action_type='email_send',
            action_details={
                'to': 'client@example.com',
                'subject': 'Test Email',
                'body': 'Test content'
            }
        )
        
        assert result['success'] == True
        assert result['file_path'] is not None
        assert Path(result['file_path']).exists()


class TestMoveToDone:
    """Tests for move_to_done skill."""
    
    def test_move_to_done(self, temp_vault, sample_email_content):
        """Test moving file to Done."""
        from skills.move_to_done import move_to_done
        
        # Create test file
        src_file = temp_vault / 'Needs_Action' / 'test.md'
        src_file.write_text(sample_email_content)
        
        result = move_to_done(str(src_file), str(temp_vault))
        
        assert result['success'] == True
        assert result['new_path'] is not None
        assert Path(result['new_path']).exists()
        assert not src_file.exists()  # Original removed


# ===========================================
# Orchestrator Tests
# ===========================================

class TestOrchestrator:
    """Tests for Orchestrator class."""
    
    def test_orchestrator_initialization(self, temp_vault):
        """Test Orchestrator initializes correctly."""
        from orchestration.orchestrator import Orchestrator, OrchestratorConfig
        
        config = OrchestratorConfig(
            vault_path=str(temp_vault),
            dry_run=True
        )
        
        orchestrator = Orchestrator(config)
        assert orchestrator is not None
        assert orchestrator.vault_path == temp_vault
    
    def test_check_needs_action(self, temp_vault):
        """Test checking Needs_Action folder."""
        from orchestration.orchestrator import Orchestrator, OrchestratorConfig
        import time
        
        # Create a test file
        test_file = temp_vault / 'Needs_Action' / 'test.md'
        test_file.write_text('test')
        
        # Wait to ensure file age > 5 seconds
        time.sleep(6)
        
        config = OrchestratorConfig(
            vault_path=str(temp_vault),
            dry_run=True
        )
        
        orchestrator = Orchestrator(config)
        files = orchestrator.check_needs_action()
        
        assert len(files) == 1
    
    def test_update_dashboard(self, temp_vault):
        """Test dashboard update through orchestrator."""
        from orchestration.orchestrator import Orchestrator, OrchestratorConfig
        
        config = OrchestratorConfig(
            vault_path=str(temp_vault),
            dry_run=True
        )
        
        orchestrator = Orchestrator(config)
        orchestrator.update_dashboard()
        
        assert orchestrator.last_dashboard_update is not None


# ===========================================
# Integration Tests
# ===========================================

class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_email_flow(self, temp_vault):
        """Test complete email processing flow."""
        from watchers.filesystem_watcher import FilesystemWatcher
        from skills.process_email import process_email
        from skills.update_dashboard import update_dashboard
        
        # Step 1: Create email file (simulating watcher)
        email_content = """---
type: email
from: client@example.com
subject: Project Inquiry
received: 2026-02-28T10:00:00
priority: medium
status: pending
---

## Content

Hi, I'm interested in your services.

## Suggested Actions
- [ ] Reply to sender
"""
        
        email_file = temp_vault / 'Needs_Action' / 'EMAIL_test.md'
        email_file.write_text(email_content)
        
        # Step 2: Process email
        result = process_email(str(email_file), str(temp_vault))
        assert result['success'] == True
        
        # Step 3: Update dashboard
        dashboard_result = update_dashboard(str(temp_vault))
        assert dashboard_result['success'] == True
        
        # Verify files exist
        assert (temp_vault / 'Plans').iterdir()  # Plan created
        assert (temp_vault / 'Dashboard.md').exists()
    
    def test_approval_flow(self, temp_vault):
        """Test approval request and execution flow."""
        from skills.create_approval_request import create_approval_request
        from skills.move_to_done import move_to_done
        
        # Step 1: Create approval request
        result = create_approval_request(
            vault_path=str(temp_vault),
            action_type='email_send',
            action_details={
                'to': 'client@example.com',
                'subject': 'Test',
                'body': 'Test content'
            }
        )
        
        assert result['success'] == True
        approval_file = Path(result['file_path'])
        assert approval_file.exists()
        
        # Step 2: Simulate approval (move to Approved)
        approved_file = temp_vault / 'Approved' / approval_file.name
        shutil.move(str(approval_file), str(approved_file))
        
        # Step 3: Execute approved action (move to Done)
        done_result = move_to_done(str(approved_file), str(temp_vault))
        assert done_result['success'] == True


# ===========================================
# Run Tests
# ===========================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
