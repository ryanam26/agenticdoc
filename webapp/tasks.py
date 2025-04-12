from typing import Dict, Optional
import uuid
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    status: TaskStatus
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
    
    def create_task(self) -> str:
        """Create a new task and return its ID."""
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = Task(
            id=task_id,
            status=TaskStatus.PENDING
        )
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID."""
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, status: TaskStatus, result: Optional[dict] = None, error: Optional[str] = None):
        """Update a task's status and result."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = status
            task.result = result
            task.error = error
            task.updated_at = datetime.now()
    
    def delete_task(self, task_id: str):
        """Delete a task by its ID."""
        if task_id in self.tasks:
            del self.tasks[task_id]

# Create a global task manager instance
task_manager = TaskManager() 