"""
Training Wizard - Step-by-Step Training Workflow
순차적 워크플로우로 사용자가 단계별로 진행

REFACTORED: All components moved to training_wizard/ module
This file now imports from the modular structure

Steps:
1. Sensor Selection
2. Model Selection
3. Feature Configuration
4. Training Parameters
5. Execute Training
6. View Results

Route: /training-wizard
"""

# Import the main page from the refactored module
from .training_wizard import training_wizard_page

# Export for compatibility
__all__ = ["training_wizard_page"]
