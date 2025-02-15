
def timeout_handler(_, __):
    raise TimeoutError()


from threading import Thread
class PropagatingThread(Thread):
    def run(self):
        self.exc = None
        try:
            if hasattr(self, '_Thread__target'):
                # Thread uses name mangling prior to Python 3.
                self.ret = self._Thread__target(*self._Thread__args, **self._Thread__kwargs)
            else:
                self.ret = self._target(*self._args, **self._kwargs)
        except Exception as e:
            self.exc = e

    def join(self, timeout=None):
        super(PropagatingThread, self).join(timeout)
        if self.exc:
            raise self.exc
        if self.is_alive():
            return None
        return self.ret
    
    def terminate(self):
        self._stop()



import ast
import astunparse

def get_call_str(assert_statement: str) -> str:
    ast_parsed = ast.parse(assert_statement)
    try:
        call_str = ast_parsed.body[0].test.left # type: ignore
    except:
        call_str = ast_parsed.body[0].test # type: ignore

    return astunparse.unparse(call_str).strip()



import multiprocessing
import sys
from io import StringIO


def function_with_timeout(func, args, timeout):
    result_container = []

    def wrapper():
        result_container.append(func(*args))

    try:
        thread = PropagatingThread(target=wrapper)
        thread.start()
        thread.join(timeout)

        if thread.is_alive(): # timeout
            return -1, None
        else: # correctly run
            return 0, result_container[0] # list of sometime
    except Exception as e:
        return -2, e # incorrectly run



def exec_ast_fn(code, ast, timeout):
    # run code + completed one ast
    # consider timeout
    # extract stdout

    imports = 'from typing import *'
    code = f'{imports}\n{code}\n{ast}'

    try:
        rtn = function_with_timeout(exec, (code, globals()), timeout)
    except Exception as e:
        rtn = (-2, e)
    finally:
        if rtn[0] == -1:
            return rtn[0], ast
        elif rtn[0] == -2: # incorrect result
            return rtn[0], ast
        else:
            return 0, ast

def eval_ast_fn(code, ast, timeout):
    original_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        exec(f"from typing import *\n{code}", globals())
        ast_func_call = get_call_str(ast)
        rtn = function_with_timeout(eval, (ast_func_call, globals()), timeout)

    except Exception as e:
        rtn = (-2, e)
    finally:
        sys.stdout.flush()
        captured_output = sys.stdout.getvalue()
        sys.stdout = original_stdout

        if rtn[0] == -1:
            return "TIMEOUT", captured_output + "\n TIMEOUT", ast
        elif rtn[0] == -2:  # such as OOIndex
            return str(rtn[1]), captured_output + "\n " + str(rtn[1]), ast
        else:  # can run, but wrong results
            return str(rtn[1]), captured_output, ast

def find_syntax_error(code):
    try:
        exec(code)
        return None
    except SyntaxError as e:
        error_message=""
        try:
            error_message = f'  File "{e.filename}", line {e.lineno}\n'
        except:
            pass
        try:
            error_message += f'    {e.text.strip()}\n'
        except:
            pass
        try:
            error_message += ' ' * (e.offset + 3) + '^\n'
        except:
            pass
        try:
            error_message += f"{e.__class__.__name__}: {e.msg}\n"
        except:
            pass
        return error_message
    except Exception as e:
        return None

def function_with_timeout_process(code_str, asserts, timeout):
    result=find_syntax_error(code_str)
    # syntax_error
    if result!=None:
        return False, [f"{asserts[0]} # Real Execution Output: {result}"], None, 0, None, [0], [result]
    with multiprocessing.Pool(processes = multiprocessing.cpu_count() - 2) as pool:
        tasks = [(code_str, ast, timeout) for ast in asserts]
        pool_results = pool.starmap(exec_ast_fn, tasks)
        
        reward = sum(map(lambda x: 1 if x[0] == 0 else 0, pool_results))
        
        # failed_tests_list: the indexes of the assertions that are failed or timeout
        failed_tests_list = [i for i, x in enumerate(pool_results) if x[0] < 0]
        timeout_list = [i for i, x in enumerate(pool_results) if x[0] == -1]

        is_passing = True
        if len(failed_tests_list):
            is_passing = False
        timeout_flag=False
        if len(timeout_list):
            timeout_flag=True

    with multiprocessing.Pool(processes=multiprocessing.cpu_count() - 2) as pool:
        failed_and_timeout_tests = [x[1] for x in pool_results if x[0] < 0]
        tasks = [(code_str, ast, timeout) for ast in failed_and_timeout_tests]
        pool_results = pool.starmap(eval_ast_fn, tasks)
        
        failed_printed_output_list = [x[1] for x in pool_results]
        failed_tests = ["{} # Real Execution Output: {}".format(x[2], x[0]) for x in pool_results]

    return is_passing, failed_tests, None, reward, timeout_flag, failed_tests_list, failed_printed_output_list


def function_with_timeout_processpool_no_return(code_str, timeout):
    with multiprocessing.Pool(processes = 1) as pool:
        tasks = [(code_str, "", timeout)]
        pool_results = pool.starmap(exec_ast_fn, tasks)
        return pool_results[0][0] == 0, pool_results[0][0]==-1
