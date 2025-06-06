from typing import List, Union, Optional, Literal
import dataclasses
import os
# from vllm import LLM, SamplingParams
from tenacity import (
    retry,
    stop_after_attempt,  # type: ignore
    wait_random_exponential,  # type: ignore
)
from openai import OpenAI
from transformers import GPT2Tokenizer, AutoTokenizer
import random
import  time

MessageRole = Literal["system", "user", "assistant"]

@dataclasses.dataclass()
class Message():
    role: MessageRole
    content: str


def message_to_str(message: Message) -> str:
    return f"{message.role}: {message.content}"


def messages_to_str(messages: List[Message]) -> str:
    return "\n".join([message_to_str(message) for message in messages])


def change_messages(tokenizer, messages, max_len):
    if isinstance(messages, str):
        message_lines = messages.split("\n")
        acc_msg_len = 0
        new_messages = ""
        for l in reversed(message_lines):
            acc_msg_len += len(tokenizer.tokenize(l))
            if acc_msg_len < max_len:
                new_messages = l + "\n" + new_messages
            else:
                break
        new_messages = new_messages.strip()
        return new_messages
    else:
        original_messages = messages
        new_messages = messages[:1]
        total_msg_len = len(tokenizer.tokenize(messages[0].content))
        rest_messages = []
        for msg in reversed(messages[1:]):
            msg_len = len(tokenizer.tokenize(msg.content))
            if msg_len + total_msg_len < max_len:
                rest_messages = [msg] + rest_messages
                total_msg_len += msg_len
            else:
                break
        messages = new_messages + rest_messages
    return messages

class ModelBase():
    def __init__(self, name: str):
        self.name = name
        self.is_chat = False

    def __repr__(self) -> str:
        return f'{self.name}'

    def generate_chat(self, messages: List[Message], max_tokens: int = 1024, temperature: float = 0.2, num_comps: int = 1) -> Union[List[str], str]:
        raise NotImplementedError

    def generate(self, prompt: str, max_tokens: int = 1024, stop_strs: Optional[List[str]] = None, temperature: float = 0.0, num_comps=1) -> Union[List[str], str]:
        raise NotImplementedError


class GPTChat(ModelBase):
    def __init__(self, model_name: str, key: str = ""):
        self.name = model_name
        self.is_chat = True
        self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        if key != "":
            self.client = OpenAI(api_key=key)
        else:
            self.client = OpenAI()
    
    def gpt_chat(
        self,
        messages,
        stop: List[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        num_comps=1,
    ) -> Union[List[str], str]:
        try:
            new_messages = change_messages(self.tokenizer, messages, 18000)
            messages = new_messages
            response = self.client.chat.completions.create(
                model=self.name,
                messages=[dataclasses.asdict(message) for message in messages],
                temperature=temperature,
                top_p=1,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                n=num_comps,
                stop=stop
            )
        except Exception as e:
            print("GPT Error:", str(e))
            if "context_length_exceeded" in str(e):
                messages = change_messages(self.tokenizer, messages, 16200)
                print("AFTER CHANGE MESSAGE LEN:", len(messages))
                print(messages)
                response = self.client.chat.completions.create(
                    model=self.name,
                    messages=[dataclasses.asdict(message) for message in messages],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=1,
                    frequency_penalty=0.0,
                    presence_penalty=0.0,
                    n=num_comps,
                )
            else:
                assert False, "GPT API error: " + str(e)
        if num_comps == 1:
            return response.choices[0].message.content  # type: ignore
        return [choice.message.content for choice in response.choices]  # type: ignore

    def generate_chat(self, messages: List[Message], stop: List[str] = None, max_tokens: int = 1024, temperature: float = 0.0, num_comps: int = 1) -> Union[List[str], str]:
        res = self.gpt_chat(messages, stop, max_tokens, temperature, num_comps)
        return res


class GPT4o(GPTChat):
    def __init__(self, key):
        super().__init__("gpt-4o-2024-05-13", key)

class GPT4o_mini(GPTChat):
    def __init__(self, key):
        super().__init__("gpt-4o-mini-2024-07-18", key)

class GPT4(GPTChat):
    def __init__(self, key):
        super().__init__("gpt-4-1106-preview", key)

class GPT35(GPTChat):
    def __init__(self, key):
        super().__init__("gpt-3.5-turbo-0613", key)

class GPT3512(GPTChat):
    def __init__(self, key):
        super().__init__("gpt-3.5-turbo-0125", key)


class VLLMModelBase(ModelBase):
    """
    Base for huggingface chat models
    """

    def __init__(self, model, port="8000"):
        super().__init__(model)
        self.model = model
        self.vllm_client = OpenAI(api_key="EMPTY", base_url=f"http://localhost:{port}/v1")
        self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        self.max_length = 8000

    def vllm_chat(
            self,
            prompt: str,
            stop: List[str] = [""],
            max_tokens: int = 8192,
            temperature: float = 0.0,
            num_comps=1,
    ) -> Union[List[str], str]:
        max_length = self.max_length
        Internal_Server_Error = 0
        request_timeout = 0
        timeout = 1800
        while True:
            prompt = change_messages(self.tokenizer, prompt, max_length)  # StarCoder max length
            try:
                responses = self.vllm_client.chat.completions.create(
                    model=self.model,
                    messages=[dataclasses.asdict(message) for message in prompt],
                    max_tokens=max_tokens,
                    temperature=0,
                    top_p=1,
                    stop=stop,
                    frequency_penalty=0.0,
                    presence_penalty=0.0,
                    n=num_comps,
                    timeout=timeout,
                )
            except Exception as e:
                print("VLLM Error:", str(e))
                if "Internal Server Error" in str(e):
                    if Internal_Server_Error <= 5:
                        print("try again Server Error")
                        num = round(random.uniform(0, 2), 4)
                        time.sleep(num + Internal_Server_Error)
                        Internal_Server_Error += 1
                        continue

                    else:
                        print("try 5 times Internal Server Error")
                        assert False, "VLLM API error: " + str(e)
                if "Request timed out" in str(e):
                    if request_timeout <= 5:
                        max_tokens = 8192 - 1024
                        print("try again Request timed out")
                        num = round(random.uniform(0, 2), 4)
                        time.sleep(num + request_timeout)
                        request_timeout += 1
                        continue
                    else:
                        print("try 5 Request timed out")
                        assert False, "VLLM API error: " + str(e)
                if "maximum context length" in str(e):
                    max_length -= 2000
                else:
                    assert False, "VLLM API error: " + str(e)
            else:
                break
        if num_comps == 1:
            return responses.choices[0].message.content  # type: ignore
        return [responses.choices[0].message.content for response in responses]  # type: ignore

    def generate_completion(self, messages: str, stop: List[str] = [""], max_tokens: int = 8192,
                            temperature: float = 0.0, num_comps: int = 1) -> Union[List[str], str]:
        ret = self.vllm_chat(messages, stop, max_tokens, temperature, num_comps)
        return ret

    def generate_chat(self, messages: List[Message], stop: List[str] = None, max_tokens: int = 8192,
                      temperature: float = 0.0, num_comps: int = 1) -> Union[List[str], str]:
        res = self.generate_completion(messages, stop, max_tokens, temperature, num_comps)
        return res

    def prepare_prompt(self, messages: List[Message]):
        prompt = ""
        for i, message in enumerate(messages):
            prompt += message.content + "\n"
            if i == len(messages) - 1:
                prompt += "\n"
        return prompt

    def extract_output(self, output: str) -> str:
        return output



class Phi3(VLLMModelBase):
    def __init__(self, port=""):
        super().__init__("phi-3", port)


class Llama(VLLMModelBase):
    def __init__(self, port=""):
        super().__init__("Llama3.0", port)
