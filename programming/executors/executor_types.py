from typing import NamedTuple, List, Tuple
from abc import ABC, abstractmethod

class ExecuteResult(NamedTuple):
    is_passing: bool
    feedback: str
    printed_output: str
    reward: int
    # state: Tuple[str]
    state: bool
    failed_tests_list: list
    failed_printed_output_list :list

class Executor(ABC):
    @abstractmethod
    def execute(self, func: str, tests: List[str], timeout: int = 5) -> ExecuteResult:
        ...

    @abstractmethod
    def evaluate(self, name: str, func: str, test: str, timeout: int = 5) -> bool:
        ...