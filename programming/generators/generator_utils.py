from generators.model import ModelBase, Message
import random

from typing import Union, List, Optional, Callable

def generate_plan(
        prompt: str,
        plan_system: str,
        plan_user: str,
        plan_examples:str,
        entry: str,
        model: ModelBase,
        messages: List[Message],
        dataset_type: str = ""
) -> str:
    if model.is_chat:
        messages = [
            Message(
                role="system",
                content=plan_system,
            ),
            Message(
                role="user",
                content=f'{plan_examples}\n\n{plan_user}\n\n[Start problem]:\n\n{prompt}',
                ),
        ]
    plan = model.generate_chat(messages=messages, num_comps=1, temperature=0.0)
    return plan,messages  # type: ignore



def evaluation_plan(
        prompt: str,
        test:str,
        solution_plan: str,
        evaluation_system: str,
        evaluation_user: str,
        evaluation_examples:str,
        entry: str,
        model: ModelBase,
        messages: List[Message],
        dataset_type: str = ""
) -> str:
    if model.is_chat:
        messages = [
            Message(
                role="system",
                content=evaluation_system,
            ),
            Message(
                role="user",
                content=f"{evaluation_examples}\n\n{evaluation_user}\n\n[Problem Description]:\n\n {prompt}\n\n[Solution Plan]:\n\n{solution_plan}\n\n[Test Cases]:\n\n{test}\n\nLet's verify the plan",
                ),
        ]
    evaluation = model.generate_chat(messages=messages, num_comps=1, temperature=0)
    return evaluation, messages  # type: ignore




def evaluation_plan_check(
        prompt: str,
        solution_plan: str,
        evaluation_message:str,
        evaluation_check_system: str,
        evaluation_check_user: str,
        entry: str,
        model: ModelBase,
        messages: List[Message],
        dataset_type: str = ""
) -> str:
    if model.is_chat:
        messages = [
            Message(
                role="system",
                content=evaluation_check_system,
            ),
            Message(
                role="user",
                content=f'{evaluation_check_user}\n\n[Problem Description]:\n\n {prompt}\n\n[Solution Plan]:\n\n{solution_plan}\n\n{evaluation_message}\n\n "Let\'s evaluate the logic analysis"',
                ),
        ]
    evaluation_check = model.generate_chat(messages=messages, num_comps=1, temperature=0)
    return evaluation_check, messages  # type: ignore



def generate_code(
        program_system: str,
        program_user: str,
        program_examples:str,
        program_generation_problem:str,
        program_generation_prompt:str,
        program_generation_plan:str,
        entry: str,
        model: ModelBase,
        messages: List[Message],
        dataset_type: str = ""
) -> str:

    if model.is_chat:
        messages = [
            Message(
                role="system",
                content=program_system,
            ),
            Message(
                role="user",
                content=f'{program_examples}\n\n{program_user}\n\n[Problem Description]\n\n{program_generation_problem}\n\n[Solution Plan]\n\n{program_generation_plan}\n\n{program_generation_prompt}\n\n "Let\'s generate the program"',
                ),
        ]
    program_imp = model.generate_chat(messages=messages, num_comps=1, temperature=0)
    return program_imp, messages  # type: ignore



def generate_program_with_print(
        print_system: str,
        print_user: str,
        print_examples:str,
        program:str,
        code_generation_evaluation_prompt:str,
        model: ModelBase,
        messages: List[Message],
        dataset_type: str = ""
) -> str:

    if model.is_chat:
        messages = [
            Message(
                role="system",
                content=print_system,
            ),
            Message(
                role="user",
                content=f'{print_examples}\n\n{print_user}\n\n[Python Program]\n\n{program}\n\n {code_generation_evaluation_prompt}\n\n "Let\'s add print statements"',
                ),
        ]
    program_imp_with_print = model.generate_chat(messages=messages, num_comps=1, temperature=0)
    return program_imp_with_print, messages  # type: ignore




def generate_analysis(
        prompt: str,
        analysis_system: str,
        analysis_user: str,
        analysis_examples: str,
        cur_func_impl: str,
        correct_analysis:str,
        failed_tests: str,
        printed_output: str,
        model: ModelBase,
        messages: List[Message],
        dataset_type: str = ""
) -> str:

    if model.is_chat:
        messages = [
            Message(
                role="system",
                content=analysis_system,
            ),
            Message(
                role="user",
                content=f'{analysis_examples}\n\n{analysis_user}\n\n [Problem Description]\n\n {prompt} \n\n[Error Program]\n\n{cur_func_impl}\n\n[Error Execution Trace for Test Case {failed_tests}]\n\n{printed_output}\n\n[Correct Logic Reasoning Process for Test Case {failed_tests}]\n\n{correct_analysis}\n\n "Let\'s do analysis"',
                ),
        ]
    analysis_result = model.generate_chat(messages=messages, num_comps=1, temperature=0)
    return analysis_result, messages  # type: ignore




def generate_correct_program(
        prompt: str,
        program_correct_system: str,
        program_correct_user: str,
        cur_func_impl: str,
        program_explain:str,
        error_analysis: str,
        incorrect_history_prompt:str,
        model: ModelBase,
        messages: List[Message],
        dataset_type: str = ""
) -> str:

    if model.is_chat:
        messages = [
            Message(
                role="system",
                content=program_correct_system,
            ),
            Message(
                role="user",
                content=f'{program_correct_user}\n\n[Problem Description]\n\n {prompt} \n\n {incorrect_history_prompt}\n\n[Error Program]\n\n{cur_func_impl}\n\n[Error Program Explanation]\n\n{program_explain}\n\n[Error Analysis]\n\n{error_analysis}\n\n"Let\'s correct the program"',
                ),
        ]
    correct_program = model.generate_chat(messages=messages, num_comps=1, temperature=0)
    return correct_program, messages  # type: ignore




def generate_explain(
        prompt: str,
        explain_system: str,
        explain_user: str,
        cur_func_impl: str,
        model: ModelBase,
        messages: List[Message],
        dataset_type: str = ""
) -> str:

    if model.is_chat:
        messages = [
            Message(
                role="system",
                content=explain_system,
            ),
            Message(
                role="user",
                content=f'{explain_user}\n\n[Problem Description]\n\n {prompt} \n\n [Python Program]\n\n{cur_func_impl}\n\n"Let\'s generate the explanation"',
                ),
        ]
    correct_program = model.generate_chat(messages=messages, num_comps=1, temperature=0)
    return correct_program, messages  # type: ignore


def sample_n_random(items: List[str], n: int) -> List[str]:
    """Sample min(n, len(items)) random items from a list"""
    assert n >= 0
    if n >= len(items):
        return items
    return random.sample(items, n)

def print_messages(system_message_text: str, user_message_text: str) -> None:
    print(f"""----------------------- SYSTEM MESSAGE -----------------------)
{system_message_text}
----------------------------------------------
----------------------- USER MESSAGE -----------------------
{user_message_text}
----------------------------------------------
""", flush=True)

def print_generated_func_body(func_body_str: str) -> None:
    print(f"""--------------------- GENERATED FUNC BODY ---------------------
{func_body_str}
------------------------------------------""")
