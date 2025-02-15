import ast
import signal
import astunparse
# from .executor_utils import function_with_timeout
from .executor_utils import function_with_timeout_process
from .executor_utils import function_with_timeout_processpool_no_return
from typing import List
from .executor_types import ExecuteResult, Executor
from io import StringIO
import sys
sys.set_int_max_str_digits(100000)

class PyExecutor(Executor):
    def execute(self, func: str, tests: List[str], timeout: int = 60) -> ExecuteResult:

        rtns = function_with_timeout_process(func, tests, timeout)
        print("|| End Executing...")
        return ExecuteResult(*rtns)

    def evaluate(self, name: str, func: str, test: str, timeout: int = 600) -> bool:
        """
        Evaluates the implementation on Human-Eval Python.

        probably should be written in a dataset-agnostic way but not now
        """
        code = f"""{func}

{test}

check({name})
    """
        return function_with_timeout_processpool_no_return(code, timeout)

# TODO: to remove
def get_call_str(assert_statement: str) -> str:
    ast_parsed = ast.parse(assert_statement)
    try:
        call_str = ast_parsed.body[0].test.left # type: ignore
    except:
        call_str = ast_parsed.body[0].test # type: ignore

    return astunparse.unparse(call_str).strip()
