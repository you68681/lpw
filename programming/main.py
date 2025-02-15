import os
import argparse
from LPW import run_lpw
from utils import read_jsonl, read_jsonl_gz

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_dir", type=str,
                        help="The root logging directory", default="root")
    parser.add_argument("--dataset_path", type=str,
                        help="The path to the benchmark dataset", default="root")
    parser.add_argument("--strategy", type=str,
                        help="Strategy: 'lpw' ")
    parser.add_argument("--model", type=str, 
                        help="OpenAI models only for now. For best results, use GPT-4o")
    parser.add_argument("--max_iters", type=int,
                        help="The maximum number of plan, plan verification, and code refinements iterations", default=12)

    parser.add_argument("--testfile", type=str, help="test instances", default="")
    parser.add_argument("--name", type=str,
                        help="identification", default='')
    parser.add_argument("--port", type=str, help="tests for debugging", default="8000")

    parser.add_argument("--verbose", action='store_true',
                        help="To print live logs")
    args = parser.parse_args()
    return args


def strategy_factory(strategy: str):
    def kwargs_wrapper_gen(func, delete_keys=[], add_keys={}):
        def kwargs_wrapper(**kwargs):
            for key in delete_keys:
                del kwargs[key]
            for key in add_keys:
                kwargs[key] = add_keys[key]
            return func(**kwargs)
        return kwargs_wrapper
    

    if strategy == "lpw":
        return kwargs_wrapper_gen(run_lpw)
    else:
        raise ValueError(f"Strategy `{strategy}` is not supported")


def main(args):
    # check if the root dir exists and create it if not
    if not os.path.exists(args.root_dir):
        os.makedirs(args.root_dir)

    # get the dataset name
    dataset_name = os.path.basename(args.dataset_path).replace("jsonl", "")
    identification=args.name
    # check if log path already exists
    log_dir = os.path.join(args.root_dir, args.strategy)
    log_path = os.path.join(
        log_dir, f"{dataset_name}_{args.max_iters}_{args.model}_identification_{identification}.jsonl")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # check if the strategy is valid
    run_strategy = strategy_factory(args.strategy)

    # print starting message
    if args.verbose:
        print(f"""
Starting run with the following parameters:
strategy: {args.strategy}
""")
    else:
        print(f"Logs will be saved in `{log_dir}`")

    # load the dataset
    print(f'Loading the dataset...')
    if args.dataset_path.endswith(".jsonl"):
        dataset = read_jsonl(args.dataset_path)
    elif args.dataset_path.endswith(".jsonl.gz"):
        dataset = read_jsonl_gz(args.dataset_path)
    else:
        raise ValueError(
            f"Dataset path `{args.dataset_path}` is not supported")

    print(f"Loaded {len(dataset)} examples")
    # start the run
    # evaluate with pass@k
    run_strategy(
        dataset=dataset,
        model_name=args.model,
        max_iters=args.max_iters,
        log_path=log_path,
        verbose=args.verbose,
        testfile=args.testfile,
        port=args.port,
    )

    print(f"Done! Check out the logs in `{log_path}`")


if __name__ == "__main__":
    args = get_args()
    main(args)
