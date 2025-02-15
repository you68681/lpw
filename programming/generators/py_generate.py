from .model import ModelBase, Message
from .generator_utils import generate_plan, evaluation_plan, generate_code, generate_analysis, generate_program_with_print,generate_correct_program, generate_explain, evaluation_plan_check
from typing import Optional, List, Union
import ast
import re, random, time, json
from utils import IMPORT_HEADER
from .pwords import prompt_words


def print_message(messages: str, prefix = "") -> None:
    print("::CHAT MESSAGE::" +prefix)
    print(messages)
    print("==================")



class PyGenerator:

    def plan_generation(self, prompt: str, entry: str, model: ModelBase, messages: List[
        Message], dataset_type: str = "") -> str:
        prompts = prompt_words()
        plan, message= generate_plan(
        prompt=prompt,
        plan_system=prompts.PY_PlAN_GENERATE_SYSTEM,
        plan_user=prompts.PY_PlAN_GENERATE_USER,
        plan_examples=prompts.PY_PlAN_GENERATE_EXAMPLES,
        entry=entry,
        model=model,
        messages=messages,
        dataset_type=dataset_type
        )

        print_message(plan)
        return plan, message


    def plan_evaluation(self, prompt: str, entry: str, solution_plan:str, test: str, model: ModelBase, messages: List[
        Message], dataset_type: str = "") -> str:
        prompts = prompt_words()
        evaluation, message= evaluation_plan(
        prompt=prompt,
        test=test,
        solution_plan=solution_plan,
        evaluation_system=prompts.PY_PlAN_EVALUATION_SYSTEM,
        evaluation_user=prompts.PY_PlAN_EVALUATION_USER,
        evaluation_examples=prompts.PY_PlAN_EVALUATION_EXAMPLES,
        entry=entry,
        model=model,
        messages=messages,
        dataset_type=dataset_type
        )

        print_message(evaluation)
        return evaluation, message



    def plan_evaluation_check(self, prompt: str, entry: str, solution_plan:str, evaluation_message: str, model: ModelBase, messages: List[
        Message], dataset_type: str = "") -> str:
        prompts = prompt_words()
        evaluation_check, message= evaluation_plan_check(
        prompt=prompt,
        solution_plan=solution_plan,
        evaluation_message=evaluation_message,
        evaluation_check_system=prompts.PY_EVALUATION_CHECK_SYSTEM,
        evaluation_check_user=prompts.PY_EVALUATION_CHECK_USER,
        entry=entry,
        model=model,
        messages=messages,
        dataset_type=dataset_type
        )

        print_message(evaluation_check)
        return  evaluation_check, message


    def code_generation(self, prompt: str, entry: str, code_generation_prompt:str, code_generation_plan:str, model: ModelBase, messages: List[
        Message], dataset_type: str = "") -> str:
        prompts = prompt_words()
        program_imp, message= generate_code(
        program_system=prompts.PY_CODE_GENERATE_SYSTEM,
        program_user=prompts.PY_CODE_GENERATE_USER,
        program_examples=prompts.PY_CODE_GENERATE_EXAMPLES,
        program_generation_problem=prompt,
        program_generation_prompt=code_generation_prompt,
        program_generation_plan=code_generation_plan,
        entry=entry,
        model=model,
        messages=messages,
        dataset_type=dataset_type
        )

        print_message(program_imp)
        return program_imp,message

    def print_generation(self, cur_func_impl: str, code_generation_evaluation_prompt:str, model : ModelBase,messages: List[Message], dataset_type: str = ""):
        prompts = prompt_words()
        program_imp_with_print, message = generate_program_with_print(
            print_system=prompts.PY_PRINT_GENERATE_SYSTEM,
            print_user=prompts.PY_PRINT_GENERATE_USER,
            print_examples=prompts.PY_PRINT_GENERATE_EXAMPLES,
            program=cur_func_impl,
            code_generation_evaluation_prompt=code_generation_evaluation_prompt,
            model=model,
            messages=messages,
            dataset_type=dataset_type
        )

        print_message(program_imp_with_print)
        return program_imp_with_print, message


    def program_analysis(self, prompt: str, cur_func_impl: str,correct_analysis:str, failed_tests: str, printed_output:str, model: ModelBase, messages: List[
        Message], dataset_type: str = "") -> str:
        prompts = prompt_words()
        program_analysis, message= generate_analysis(
        prompt=prompt,
        analysis_system=prompts.PY_PROGRAM_ANALYSIS_SYSTEM,
        analysis_user=prompts.PY_PROGRAM_ANALYSIS_USER,
        analysis_examples=prompts.PY_PROGRAM_ANALYSIS_EXAMPLES,
        cur_func_impl=cur_func_impl,
        correct_analysis=correct_analysis,
        failed_tests=failed_tests,
        printed_output=printed_output,
        model=model,
        messages=messages,
        dataset_type=dataset_type
        )

        print_message(program_analysis)
        return program_analysis, message



    def program_explain(self, prompt: str, cur_func_impl:str, model: ModelBase, messages: List[
        Message], dataset_type: str = "") -> str:
        prompts = prompt_words()
        program_explain, message= generate_explain(
        prompt=prompt,
        explain_system=prompts.PY_PROGRAM_EXPLAIN_SYSTEM,
        explain_user=prompts.PY_PROGRAM_EXPLAIN_USER,
        cur_func_impl=cur_func_impl,
        model=model,
        messages=messages,
        dataset_type=dataset_type
        )

        print_message(program_explain)
        return program_explain, message



    def correct_program(self, prompt: str, cur_func_impl: str,program_explain:str, error_analysis:str, incorrect_history_prompt:str, model: ModelBase, messages: List[
        Message], dataset_type: str = "") -> str:
        prompts = prompt_words()
        program_analysis,message= generate_correct_program(
        prompt=prompt,
        program_correct_system=prompts.PY_PROGRAM_CORRECT_SYSTEM,
        program_correct_user=prompts.PY_PROGRAM_CORRECT_USER,
        cur_func_impl=cur_func_impl,
        program_explain=program_explain,
        error_analysis=error_analysis,
        incorrect_history_prompt=incorrect_history_prompt,
        model=model,
        messages=messages,
        dataset_type=dataset_type
        )

        print_message(program_analysis)
        return program_analysis,message