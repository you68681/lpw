from generators import PyGenerator, model_factory
from executors import PyExecutor
from filelock import FileLock
from collections import defaultdict
from utils import *
from transformers import GPT2Tokenizer
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

def plan_generation(item, model_name, max_iters, port):
    model = model_factory(model_name, port)
    gen = PyGenerator()
    cur_Exp=0
    dataset_type = item["task_id"].split("/")[0]
    tests_i = item['given_tests']
    tests_i = [test for test in tests_i if item['entry_point'] in test and 'assert False' not in test]
    tests_words=""
    for test in tests_i:
        tests_words+=test+"\n"

    if model.is_chat:
        messages = []
    else:
        messages = ""

    token_num=0
    token_num_plan=0
    token_num_evl = 0
    token_num_evl_check=0


    print("current plan generation iteration:", cur_Exp)
    generated_plan, message = gen.plan_generation(item["prompt"], item["entry_point"], model,
                                                   messages, dataset_type)

    token_num_plan += sum([len(tokenizer.tokenize(msg.content)) for msg in message])
    token_num_plan += sum([len(tokenizer.tokenize(msg)) for msg in generated_plan])

    token_num += token_num_plan

    plan_solution = solution_plan_filter(generated_plan)

    plan_results_list=set()
    while cur_Exp<max_iters:

        plan_verification, message=gen.plan_evaluation(item["prompt"], item["entry_point"], plan_solution, tests_words, model, messages,dataset_type)

        token_num_evl += sum([len(tokenizer.tokenize(msg.content)) for msg in message])
        token_num_evl += len(tokenizer.tokenize(plan_verification))

        token_num += token_num_evl

        # if there is no tag [Revised Solution Plan] in evaluation message, the evaluation success.
        if plan_verification.count("Verification for")==len(tests_i) and plan_verification.count("Revised Solution Plan")==0:

            # check [Verification for] tag
            plan_evaluation_for_each_test=evaluation_message_filter(plan_verification, tests_i)

            # re-check the evaluation message
            verification_check_message, message = gen.plan_evaluation_check(item["prompt"], item["entry_point"], plan_solution, plan_evaluation_for_each_test,
                                                     model, messages, dataset_type)

            token_num_evl_check += sum([len(tokenizer.tokenize(msg.content)) for msg in message])
            token_num_evl_check += len(tokenizer.tokenize(verification_check_message))
            token_num += token_num_evl_check


            # pass the self-check
            if verification_check_message.count("Correct Analysis")==len(tests_i):

                verification_list=process_evaluation_results(plan_verification)

                if len(verification_list) != len(tests_i):
                    cur_Exp += 1
                    continue
                plan_results_list=(plan_solution, plan_verification, verification_list)
                break

        elif (plan_verification.count("Verification for")>len(tests_i) and plan_verification.count("Revised Solution Plan")==0) or ( plan_verification.count("Verification for")<len(tests_i) and plan_verification.count("Revised Solution Plan")==0):
            cur_Exp+=1
            continue
        else:
            plan_solution=revised_solution_plan(plan_verification)

        cur_Exp += 1

    return plan_results_list, tests_i, token_num, token_num_plan, token_num_evl, token_num_evl_check


def code_generation(i, item, log_path, model_name, max_iters, plan_results_list, test_cases, token_num, token_num_plan, token_num_evl,token_num_evl_check, port):
    exe = PyExecutor()
    model = model_factory(model_name, port)
    is_solved = False
    dataset_type = item["task_id"].split("/")[0]
    item['solve_by_modify']=False
    item['pass_by_modify']=False
    item['program generated plan'] = ''
    item['program generate evaluation'] = ''
    item['error program'] = ''
    item['plan failed case'] = ''
    item['correct program information'] = ''
    item['example test time out'] = False
    item['real test time out'] = False
    item['token_num_plan'] = token_num_plan
    item["token_num_evl"]=token_num_evl
    item['token_num_evl_check'] = token_num_evl_check

    cur_Exp=0
    token_num_generate_code=0
    token_num_add_print=0
    token_num_generate_error_analysis=0
    token_num_generate_code_explain=0



    if len(plan_results_list) == 0:
        item["is_passing"] = False
        item["is_solved"] = False
        item["generated_test"] = test_cases
        item["debug_iter"] = 0
        item["solution"] = ''
        with FileLock(log_path + ".lock"):
            write_jsonl(log_path, [item], append=True)
        return


    plan_evaluation_dict ={"plan":plan_results_list[0],"verification_message": plan_results_list[1]}
    item['plan_verification_list']=plan_evaluation_dict


    gen = PyGenerator()

    if model.is_chat:
        messages = []
    else:
        messages = ""

    incorrect_program_record=[]

    code_generation_plan = plan_results_list[0]
    code_generation_verification_list = plan_results_list[2]

    code_generation_evaluation_prompt = "\n".join(
        [f"[Plan Verification for {test_cases[i]}]\n\n{code_generation_verification_list[i]}" for i in
         range(len(code_generation_verification_list))])

    generated_program, message = gen.code_generation(item["prompt"], item["entry_point"],
                                                     code_generation_evaluation_prompt, code_generation_plan,
                                                     model, messages, dataset_type)

    token_num_generate_code += sum([len(tokenizer.tokenize(msg.content)) for msg in message])
    token_num_generate_code += len(tokenizer.tokenize(generated_program))
    token_num += token_num_generate_code

    cur_func_impl_without_print = prepare_function_from_generated_code(dataset_type, item["prompt"],
                                                                       generated_program, item["entry_point"],
                                                                       add_header=False)

    # add print statement for each line
    generated_program, message = gen.print_generation(cur_func_impl_without_print, code_generation_evaluation_prompt,
                                                      model,
                                                      messages, dataset_type)

    token_num_add_print += sum([len(tokenizer.tokenize(msg.content)) for msg in message])
    token_num_add_print += len(tokenizer.tokenize(generated_program))
    token_num += token_num_add_print

    cur_func_impl_with_print = prepare_function_from_generated_code(dataset_type, item["prompt"],
                                                                    generated_program, item["entry_point"])

    while cur_Exp < max_iters:
        # evaluate on sample tests
        is_passing, failed_tests, printed_output, reward, timeout_example_test, failed_tests_list, failed_printed_output_list = exe.execute(
            cur_func_impl_with_print, test_cases)

        # add time out check
        if timeout_example_test:
            item['example test time out'] = True

        if is_passing:
            print(f'{item["task_id"]} pass generated tests, check real tests')
            print("cur_Exp", cur_Exp)
            item["solution"] = cur_func_impl_with_print
            item['program generated plan'] = plan_results_list[0]
            item['program generate evaluation'] = plan_results_list[1]
            if cur_Exp>0:
                item['pass_by_modify'] = True
            is_solved, timeout_real_test = exe.evaluate(item["entry_point"], cur_func_impl_with_print, item["test"])
            if timeout_real_test:
                item['real test time out'] = True
            if is_solved:
                if cur_Exp>0:
                    item['solve_by_modify'] = True
                item["solution"] = cur_func_impl_with_print  # TODO: why with print?
            break  # TODO: cannot support pass@k, when k > 1
        else:
            # retry the verification for the first failed test case
            correct_verification=plan_results_list[2][failed_tests_list[0]]

            failed_tests_case = test_cases[failed_tests_list[0]]

            # retry the execution trace for the first failed test case
            failed_printed_output = print_information_filter(model.tokenizer,failed_printed_output_list[0])

            # generate the code explain
            generated_program_explain, message =gen.program_explain(item["prompt"], cur_func_impl_without_print, model, messages, dataset_type)

            token_num_generate_code_explain += sum([len(tokenizer.tokenize(msg.content)) for msg in message])
            token_num_generate_code_explain += len(tokenizer.tokenize(generated_program_explain))
            token_num += token_num_generate_code_explain


            program_explain=explain_filter(generated_program_explain)

            # generate the refinement suggestion
            program_analysis, message = gen.program_analysis(item["prompt"], cur_func_impl_with_print, correct_verification,
                                                    failed_tests_case, failed_printed_output, model, messages, dataset_type)

            token_num_generate_error_analysis += sum([len(tokenizer.tokenize(msg.content)) for msg in message])
            token_num_generate_error_analysis += len(tokenizer.tokenize(program_analysis))

            token_num += token_num_generate_error_analysis


            error_analysis = program_analysis_filter(program_analysis)

            # record the incorrect code history (remove it to save token); its effect needs additional experiments.
            incorrect_history_prompt = "[Incorrect History]\n\n"
            for kvs in incorrect_program_record:
                incorrect_history_prompt += f"[History Error Program]\n\n{kvs}\n\n"


            # generate the refined program
            correct_func_impl_without_print, message = gen.correct_program(item["prompt"], cur_func_impl_without_print,program_explain, error_analysis,
                                                                incorrect_history_prompt, model, messages, dataset_type)

            token_num_generate_code += sum([len(tokenizer.tokenize(msg.content)) for msg in message])
            token_num_generate_code += len(tokenizer.tokenize(correct_func_impl_without_print))
            token_num+=token_num_generate_code


            correct_func_impl_without_print = prepare_function_from_generated_code(dataset_type, item["prompt"],
                                                                                   correct_func_impl_without_print, item["entry_point"])

            code_generation_verification_list = plan_results_list[2]

            code_generation_evaluation_prompt = "\n".join(
                [f"[Plan Verification for {test_cases[i]}]\n\n{code_generation_verification_list[i]}" for i in
                 range(len(code_generation_verification_list))])


            correct_func_impl_with_print, message = gen.print_generation(correct_func_impl_without_print,code_generation_evaluation_prompt, model,
                                                                messages, dataset_type)

            token_num_add_print += sum([len(tokenizer.tokenize(msg.content)) for msg in message])
            token_num_add_print += len(tokenizer.tokenize(correct_func_impl_with_print))
            token_num += token_num_add_print


            correct_func_impl_with_print = prepare_function_from_generated_code(dataset_type, item["prompt"], 
                                                                                correct_func_impl_with_print, item["entry_point"])
            cur_func_impl_without_print = correct_func_impl_without_print
            cur_func_impl_with_print = correct_func_impl_with_print

        cur_Exp += 1

    item['token_num_generate_code'] = token_num_generate_code
    item['token_num_add_print'] = token_num_add_print
    item['token_num_generate_error_analysis'] = token_num_generate_error_analysis
    item['token_num_generate_code_explain'] = token_num_generate_code_explain
    item['token_num'] = token_num
    item["is_passing"] = is_passing
    item["is_solved"] = is_solved
    item["generated_test"] = test_cases
    item["debug_iter"] = cur_Exp
    with FileLock(log_path + ".lock"):
        write_jsonl(log_path, [item], append=True)







def programming_task(i, item, log_path, model_name, max_iters, port):

    plan_results_list, test_cases,token_num, token_num_plan,token_num_evl, token_num_evl_check = plan_generation(item, model_name, max_iters, port)

    code_generation(i, item, log_path, model_name, max_iters, plan_results_list, test_cases,token_num, token_num_plan,token_num_evl, token_num_evl_check, port)



def run_lpw(
        dataset: List[dict],
        model_name: str,
        max_iters: int,
        log_path: str,
        verbose: bool,
        testfile: str = None,
        port: str = "",
) -> None:
    num_items = len(dataset)
    args = iter([(i, item, log_path, model_name, max_iters, port) for i, item in
                 enumerate_resume(dataset, log_path,testfile)])
    for item in args:
        print(f'==start {item[0]+1}/{num_items}')
        programming_task(*item)
    print("Accuracy:", count_solved(log_path))
