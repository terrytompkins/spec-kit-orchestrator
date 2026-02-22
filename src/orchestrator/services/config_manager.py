"""Configuration manager for loading admin configuration."""

from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from ..utils.yaml_parser import load_yaml
from ..utils.path_validation import normalize_macos_path


class ConfigManager:
    """Manages admin configuration from .specify/orchestrator/config.yml"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config manager.
        
        Args:
            config_path: Path to config file. If None, uses default location.
        """
        if config_path is None:
            # Default to .specify/orchestrator/config.yml in repo root
            repo_root = Path(__file__).parent.parent.parent.parent
            config_path = repo_root / '.specify' / 'orchestrator' / 'config.yml'
        
        self.config_path = config_path
        self._config: Optional[Dict[str, Any]] = None
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary. Returns defaults if file doesn't exist.
        """
        if self._config is not None:
            return self._config
        
        if not self.config_path.exists():
            # Return defaults
            self._config = self._get_defaults()
            return self._config
        
        try:
            self._config = load_yaml(self.config_path)
            # Merge with defaults to ensure all keys exist
            defaults = self._get_defaults()
            defaults.update(self._config)
            self._config = defaults
        except Exception as e:
            # If loading fails, use defaults
            self._config = self._get_defaults()
        
        return self._config
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            'workspace': {
                'base_directory': str(Path.home() / 'spec-kit-workspace')
            },
            'ai_agents': {
                # Default to common code agents (not AI models)
                'allowed_values': [
                    'copilot', 'claude', 'gemini', 'cursor-agent',
                    'qwen', 'opencode', 'codex', 'windsurf',
                    'kilocode', 'auggie', 'codebuddy', 'qoder',
                    'roo', 'q', 'amp', 'shai', 'bob'
                ]
            },
            'secrets': {
                'storage': 'environment',
                'mask_in_logs': True
            }
        }
    
    def get_base_directory(self) -> Path:
        """
        Get base workspace directory.
        
        Returns:
            Path to base directory (normalized to avoid macOS system volume issues)
        """
        config = self.load_config()
        base_dir = config.get('workspace', {}).get('base_directory')
        if base_dir:
            # Resolve and normalize to handle macOS system volume paths
            return normalize_macos_path(Path(base_dir).expanduser().resolve())
        default_path = Path(self._get_defaults()['workspace']['base_directory'])
        return normalize_macos_path(default_path.expanduser().resolve())
    
    def get_allowed_ai_agents(self) -> List[str]:
        """
        Get list of allowed AI agent values.
        
        Returns:
            List of allowed AI agent names
        """
        config = self.load_config()
        return config.get('ai_agents', {}).get('allowed_values', [])
    
    def is_ai_agent_allowed(self, agent: str) -> bool:
        """
        Check if an AI agent value is allowed.
        
        Args:
            agent: AI agent name to check
        
        Returns:
            True if allowed, False otherwise
        """
        allowed = self.get_allowed_ai_agents()
        return agent in allowed
    
    def should_mask_secrets_in_logs(self) -> bool:
        """
        Check if secrets should be masked in logs.
        
        Returns:
            True if secrets should be masked, False otherwise
        """
        config = self.load_config()
        return config.get('secrets', {}).get('mask_in_logs', True)

