"""
Orchestration Package

This package contains the orchestration layer for the AI Employee system.

The orchestrator coordinates:
- Watcher processes
- Qwen Code processing
- Dashboard updates
- System health monitoring
"""

from .orchestrator import Orchestrator, OrchestratorConfig, load_config

__all__ = [
    'Orchestrator',
    'OrchestratorConfig',
    'load_config',
]

__version__ = '1.0.0'
