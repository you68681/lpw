import os
import gzip
import json
import openai
import jsonlines
import re
from typing import List
from transformers import GPT2Tokenizer, AutoTokenizer


openai.api_key = os.getenv("OPENAI_API_KEY")
IMPORT_HEADER = "from typing import *\nimport math\nfrom heapq import *\nimport itertools\nimport re\nimport typing\nimport heapq\n_str=str\nimport re\nimport hashlib\nimport heapq\nimport collections\nfrom collections import *\nfrom itertools import combinations\nfrom math import prod\nfrom itertools import combinations_with_replacement\nfrom  decimal import Decimal, getcontext\nimport numpy as np\n"


def prepare_function_from_generated_code(dataset_type, prompt, generated_program, entry_point, add_header = True):
    if dataset_type in ["HumanEval", "MBPP", "APPS", "CodeContests","LiveCode"]:
        if (prompt in generated_program) or (('def ' + entry_point + '(') in generated_program):
            # It has the function header, no need to add
            cur_func_impl = generated_program
        else:
            cur_func_impl = prompt + "\n" + generated_program
        # Add auxilary function
        cur_func_impl=filter_func(cur_func_impl)
        funcs = get_function(prompt)
        seed_funcs = [func[0] for func in get_function(generated_program)]
        for func in funcs:
            if func[0] not in seed_funcs:
                cur_func_impl = func[1] + "\n" + cur_func_impl
        # Add comments
        if not find_comment(cur_func_impl, entry_point):
            cur_func_impl = fix_func_impl_comments(cur_func_impl, prompt, entry_point)
    # Add import header
    if add_header and IMPORT_HEADER not in cur_func_impl:
        cur_func_impl = IMPORT_HEADER + cur_func_impl
    assert isinstance(cur_func_impl, str)
    return cur_func_impl




def capture_import_statements(code: str) -> list:
    """
    Capture all import statements from the given Python code.

    Args:
    code (str): The string containing the Python code.

    Returns:
    list: A list of import statements found in the code.
    """
    matches = re.findall(r'^\s*(import\s+\w+(\s*,\s*\w+)*|from\s+\w+(\.\w+)*\s+import\s+\w+(\s*,\s*\w+)*)', code,
                         re.MULTILINE)
    return [match[0] for match in matches]

def extract_docstring(function_str: str) -> str:
    # Regular expression to find the content between triple quotes
    docstring_pattern = re.compile(r'""".*?"""', re.DOTALL)

    # Search for the pattern in the function string
    match = docstring_pattern.search(function_str)

    if match:
        # Extract and clean up the docstring
        docstring = match.group(0)
        docstring = docstring.strip('"""')
        return docstring.strip()
    else:
        return ""

def contains_test_case(line: str) -> bool:
    # Define the regular expression pattern to search for "test case"
    test_case_pattern = re.compile(r'test case', re.IGNORECASE)

    # Check if the line is a print statement
    if line.strip().startswith('print('):
        return False

    # Search for the pattern in the line
    return bool(re.search(test_case_pattern, line))

def contains_assert(line: str) -> bool:
    # Define the regular expression pattern to search for "test case"
    assert_pattern = re.compile(r'assert', re.IGNORECASE)

    # Check if the line is a print statement
    if line.strip().startswith('print('):
        return False

    # Search for the pattern in the line
    return bool(re.search(assert_pattern, line))

def contains_fix(line: str) -> bool:
    # Define the regular expression pattern to search for "test case"
    start_fix_explanation=re.compile(r'Fixing Explanation',re.IGNORECASE)

    # Check if the line is a print statement
    if line.strip().startswith('print('):
        return False

    # Search for the pattern in the line
    return bool(re.search(start_fix_explanation, line))

def contains_adjust(line: str) -> bool:
    # Define the regular expression pattern to search for "test case"
    start_explanation_adjustments = re.compile(r'Explanation Adjustments', re.IGNORECASE)

    # Check if the line is a print statement
    if line.strip().startswith('print('):
        return False

    # Search for the pattern in the line
    return bool(re.search(start_explanation_adjustments, line))


def filter_func(func_imp):
    problem_description=extract_docstring(func_imp)
    import_statements=capture_import_statements(func_imp)
    func_imp=func_imp.replace("```","")
    func_imp=func_imp[func_imp.find("def"):]
    func_lines=[]
    test_case_pattern = re.compile(r'test case', re.IGNORECASE)
    assert_pattern = re.compile(r'assert', re.IGNORECASE)
    start_program_pattern=re.compile(r'Start Program', re.IGNORECASE)
    end_program_pattern=re.compile(r'End Program', re.IGNORECASE)
    start_fixed_program_pattern=re.compile(r'Start Fixed Program', re.IGNORECASE)
    end_fixed_program_pattern=re.compile(r'End Fixed Program', re.IGNORECASE)
    start_fix_explanation=re.compile(r'Fixing Explanation',re.IGNORECASE)
    start_explanation_adjustments = re.compile(r'Explanation Adjustments', re.IGNORECASE)


    for line in func_imp.split("\n"):
        if re.search(start_program_pattern,line) or re.search(end_program_pattern,line) or re.search(start_fixed_program_pattern,line) or re.search(end_fixed_program_pattern,line):
            continue
        if line not in problem_description and (contains_test_case(line) or contains_assert(line) or contains_fix(line) or contains_adjust(line)):
            break
        func_lines.append(line)
    func_lines=import_statements+func_lines
    func_imp="\n".join(func_lines)
    return func_imp


def solution_plan_process(list_of_plan):
    modified_plan = []
    start_plan=r'\"*\[*(?i)Start Plan\]*\"*'
    end_plan=r'\"*\[*(?i)End Plan\]*\"*'
    for plan in list_of_plan:
        if re.search(start_plan,plan) and re.search(end_plan,plan):
            start_index = plan.find("[Start Plan]") + len("[Start Plan]")
            end_index = plan.find("[End Plan]")
            solution_plan = plan[start_index:end_index]
            modified_plan.append(solution_plan)
        else:
            tmp_plan = ""
            for line in plan.split("\n"):
                if line == "":
                    continue
                if line[0].isdigit():
                    tmp_plan += line + "\n"
            modified_plan.append(tmp_plan)
    return modified_plan

def solution_plan_filter(solution_plan):
    start_plan=r'\"*\[*(?i)Start Plan\]*\"*'
    end_plan=r'\"*\[*(?i)End Plan\]*\"*'
    if re.search(start_plan,solution_plan) and  re.search(end_plan,solution_plan):
        matches_start = re.finditer(start_plan, solution_plan)
        match_indices_start = [(match.start(), match.end()) for match in matches_start]

        start_index = 0
        if len(match_indices_start) != 0:
            start_index = match_indices_start[0][1]
        matches_end = re.finditer(end_plan, solution_plan)
        match_indices_end = [(match.start(), match.end()) for match in matches_end]
        end_index = len(solution_plan) - 1
        if len(match_indices_end) != 0:
                end_index = match_indices_end[0][0]
        solution_plan = solution_plan[start_index + 1:end_index]
    return solution_plan


def evaluation_message_filter(evaluation_message,tests_i):
    evaluation_regex=r'\"*\[*(?i)Verification for\]*\"*'
    evaluation_regex_2=r"(?i)Let's verify"
    evaluation_regex_3 = r'\"*\[*(?i)Correct Plan\]*\"*'
    evaluation_list=evaluation_message.split("\n")

    evaluation_save_list=[]

    count=0
    for each_line in evaluation_list:
        if re.search(evaluation_regex_2, each_line) or re.search(evaluation_regex_3,each_line):
            continue
        if re.search(evaluation_regex,each_line):
            evaluation_save_list.append(f"[Verification for {tests_i[count]}]")
            count+=1
        else:
            evaluation_save_list.append(each_line)

    return "\n".join(evaluation_save_list)






def program_analysis_filter(analysis_words):
    compare_results_regex=r'\"*\[*(?i)Compare Results\]*\"*'
    my_analysis_regex=r'\"*\[*(?i)My Analysis\]*\"*'
    matches_start = re.finditer(my_analysis_regex, analysis_words)
    match_indices_start = [(match.start(), match.end()) for match in matches_start]

    start_index=0
    if len(match_indices_start)!=0:
        start_index = match_indices_start[0][1]


    error_analysis=analysis_words[start_index:]
    return error_analysis

def explain_filter(explain):
    start_explain_regex=r'\"*\[*(?i)Start Explanation\]*\"*'
    end_explain_regex=r'\"*\[*(?i)End Explanation\]*\"*'
    matches_start = re.finditer(start_explain_regex, explain)
    match_indices_start = [(match.start(), match.end()) for match in matches_start]

    start_index=0
    if len(match_indices_start)!=0:
        start_index = match_indices_start[0][1]


    matches_end = re.finditer(end_explain_regex, explain)
    match_indices_end = [(match.start(), match.end()) for match in matches_end]

    end_index=len(explain)-1
    if len (match_indices_end)!=0:
        end_index = match_indices_end[0][0]

    program_explain=explain[start_index:end_index]

    return program_explain



def print_information_filter(tokenizer, print_information):
    if len(print_information)>25000:
        total_tokenizer=0
        part_length = 2500
        part_information_ahead=[]
        print_information_list=print_information.split("\n")
        for line in  print_information_list:
            total_tokenizer+=len(tokenizer.tokenize(line))
            if total_tokenizer<=part_length:
                part_information_ahead.append(line)
            else:
                break

        part_information_ahead.append("...")
        part_information_tail=[]
        total_tokenizer=0
        for line in  reversed(print_information_list):
            total_tokenizer+=len(tokenizer.tokenize(line))
            if total_tokenizer<=part_length:
                part_information_tail.append(line)
            else:
                break
        print_information = "\n".join(part_information_ahead + part_information_tail[::-1])
        return print_information

    else:

        if len(tokenizer.tokenize(print_information))<=5000:
            return print_information
        else:
            total_tokenizer=0
            part_length = 2500
            part_information_ahead=[]
            print_information_list=print_information.split("\n")
            for line in  print_information_list:
                total_tokenizer+=len(tokenizer.tokenize(line))
                if total_tokenizer<=part_length:
                    part_information_ahead.append(line)
                else:
                    break

            part_information_ahead.append("...")
            part_information_tail=[]
            total_tokenizer=0
            for line in  reversed(print_information_list):
                total_tokenizer+=len(tokenizer.tokenize(line))
                if total_tokenizer<=part_length:
                    part_information_tail.append(line)
                else:
                    break

            print_information="\n".join(part_information_ahead+part_information_tail[::-1])

        return print_information



def revised_solution_plan(solution_plan):
    regex_pattern_start = r'(?i)\[*Start Revised Solution Plan]\]*'
    regex_pattern_end = r'(?i)\[*End Revised Solution Plan]\]*'
    if  not re.search(regex_pattern_start, solution_plan):
        assert "incorrect Revised Plan"

    matches_start = re.finditer(regex_pattern_start, solution_plan)
    match_indices_start = [(match.start(), match.end()) for match in matches_start]
    start_plan_index=0
    if len(match_indices_start)!=0:
        start_plan_index = match_indices_start[0][1]


    matches_end = re.finditer(regex_pattern_end, solution_plan)
    match_indices_end = [(match.start(), match.end()) for match in matches_end]
    end_plan_index=len(solution_plan)-1
    if len (match_indices_end)!=0:
        end_plan_index = match_indices_end[0][0]

    revised_plan = solution_plan[start_plan_index:end_plan_index]
    return revised_plan

def process_evaluation_results (message):

    evaluation_list=[]
    # regex_pattern = r'(?i)\[\"*?Verification for [\w\d\s\'()]+\"*\]'
    regex_pattern=r'(?i)\[+(Plan )?Verification for .*?\]+'
    compare_pattern=r'(?i)Results Compare'
    occurrences_verification = [m.start() for m in re.finditer(regex_pattern, message)]
    for i in range(len(occurrences_verification)):
        if i + 1 < len(occurrences_verification):
            evaluation_left_index = occurrences_verification[i]
            evaluation_right_index = occurrences_verification[i + 1]
            evaluation_information=message[evaluation_left_index:evaluation_right_index]
            evaluation_list_split=evaluation_information.split('\n')
            evaluation_temp_list=[]
            for each_line in evaluation_list_split:
                if re.search(regex_pattern,each_line):
                    continue
                if re.search(compare_pattern, each_line):
                    break
                evaluation_temp_list.append(each_line)
            part_evaluation_information="\n".join(evaluation_temp_list)
            evaluation_list.append(part_evaluation_information)

        else:
            evaluation_left_index=occurrences_verification[i]
            evaluation_information=message[evaluation_left_index:]

            evaluation_list_split=evaluation_information.split('\n')
            evaluation_temp_list=[]
            for each_line in evaluation_list_split:
                if re.search(regex_pattern,each_line):
                    continue
                if re.search(compare_pattern, each_line):
                    break
                evaluation_temp_list.append(each_line)
            part_evaluation_information="\n".join(evaluation_temp_list)
            evaluation_list.append(part_evaluation_information)

    return evaluation_list



def fix_func_impl_comments(func_impl: str, prompt: str, entry) -> str:
    # extract comments from prompt and insert them into func_impl after the function header
    if prompt.find('\"\"\"') != -1:
        comments = prompt.split('\"\"\"')[1]
    elif prompt.find('\'\'\'') != -1:
        comments = prompt.split('\'\'\'')[1]
    # Get the function header
    func_impl_lines = func_impl.split('\n')
    for i, line in enumerate(func_impl_lines):
        if line.startswith('def') and entry in line:
            break
    # Insert comments after the function header
    func_impl_lines.insert(i+1, '    \"\"\"' + comments + '\"\"\"')
    return '\n'.join(func_impl_lines)

def insert_comment(func_impl: str, comment: str, entry: str) -> str:
    func_impl_lines = func_impl.split('\n')
    for i, line in enumerate(func_impl_lines):
        if line.startswith('def ' + entry + '('):
            break
    func_impl_lines.insert(i + 1, '    \"\"\"' + comment + '\"\"\"')
    return '\n'.join(func_impl_lines)


def find_comment(func_impl: str, entry: str ) -> bool:
    func_impl_lines = func_impl.split('\n')
    for i, line in enumerate(func_impl_lines):
        if line.startswith('def ' + entry + "("):
            break
    func_body = "\n".join(func_impl_lines[i:])
    if func_body.find('\"\"\"') != -1 or func_body.find('\'\'\'') != -1:
        return True
    return False

def get_function(prompt):
    lines = prompt.split('\n')
    cur_func = ""
    funcs = []
    for i, l in enumerate(lines):
        if l.startswith("def "):
            if cur_func == "":
                cur_func = l
            else:
                funcs.append([func_name, cur_func])
                cur_func = l
            func_name = l.split("def ")[1].split("(")[0]
        elif cur_func != "":
            cur_func += "\n" + l
    return funcs




def read_jsonl(path: str) -> List[dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File `{path}` does not exist.")
    elif not path.endswith(".jsonl"):
        raise ValueError(f"File `{path}` is not a jsonl file.")
    items = []
    with jsonlines.open(path) as reader:
        for item in reader:
            items += [item]
    return items

def read_jsonl_map(path: str) -> List[dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File `{path}` does not exist.")
    elif not path.endswith(".jsonl"):
        raise ValueError(f"File `{path}` is not a jsonl file.")
    items = {}
    with jsonlines.open(path) as reader:
        for item in reader:
            items[item['task_id']] = item
    return items

def write_jsonl(path: str, data: List[dict], append: bool = False):
    with jsonlines.open(path, mode='a' if append else 'w') as writer:
        for item in data:
            writer.write(item)


def read_jsonl_gz(path: str) -> List[dict]:
    if not path.endswith(".jsonl.gz"):
        raise ValueError(f"File `{path}` is not a jsonl.gz file.")
    with gzip.open(path, "rt") as f:
        data = [json.loads(line) for line in f]
    return data



def replace_test(item, items_test):
    if item['task_id'] in items_test:
        item['given_tests'] = items_test[item['task_id']]['given_tests']
    else:
        item['given_tests'] = []
    return item

def enumerate_resume(dataset, results_path, testfile=None):
    items_test = {}

    if testfile is not None:
        print("testfile", testfile)
        items_test = read_jsonl_map(testfile)

    exist_items = []
    if os.path.exists(results_path):
        print(results_path)
        with jsonlines.open(results_path) as reader:
            for item in reader:
                exist_items.append(item['task_id'])

    for i, item in enumerate(dataset):

        # if item['task_id'] in exist_items:
        #     continue
        item = replace_test(item, items_test)
        yield i, item

def replace_seed_test(item, items_seed, items_test):
    if item['task_id'] in items_seed:
        item['seed'] = items_seed[item['task_id']]['solution']
        if 'is_passing' in items_seed[item['task_id']]:
            item['is_passing'] = items_seed[item['task_id']]['is_passing']
        else:
            item['is_passing'] = False
    else:
        item['seed'] = ""
    if item['task_id'] in items_test:
        item['given_tests'] = items_test[item['task_id']]['given_tests']
    else:
        item['given_tests'] = []
    return item



def count_solved(logpath) -> float:
    solved = 0
    count = 0
    dataset = open(logpath, "r")
    for l in dataset:
        item = json.loads(l)
        count += 1
        if "is_solved" in item and item["is_solved"]:
            solved += 1
    return float(solved) / count




