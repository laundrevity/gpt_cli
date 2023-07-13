import subprocess
import asyncio
import openai
import json
import os
openai.api_key = os.getenv('OPENAI_API_KEY')

def execute_linux_command(command_json):

    command_json_d = json.loads(command_json)
    command = command_json_d['command']
    args = command_json_d.get('args', [])

    try:
        result = subprocess.check_output([command] + args, shell=False)
        msg = result.decode('utf-8')
    except subprocess.CalledProcessError as e:
        msg = f"Error executing command: {e.output.decode('utf-8')}"
        print(msg)
    except FileNotFoundError:
        msg = f"Command not found: {command}"
        print(msg)
    except Exception as e:
        msg = f"An unexpected error occurred: {e}"
        print(msg)
    return msg


FUNCTIONS = [
    {
        'name': 'execute_linux_command',
        'description': 'execute Linux command and return stdout',
        'parameters': {
            'type': 'object',
            'properties': {
                'command_json': {
                    'type': 'string',
                    'description': 'stringified JSON of command to execute. it needs a string attribute `command` and optional attribute `args` is a list of arguments'
                },
            }
        },
        'required': ['command_json']
    }
]


async def main():
    conversation_messages = []
    while True:
        prompt = input('> ')
        conversation_messages.append({'role': 'user', 'content': prompt})
        response = await openai.ChatCompletion.acreate(model='gpt-4', messages=conversation_messages, functions=FUNCTIONS)
        response_message = response['choices'][0]['message']

        if response_message.get('function_call'):
            func_name = response_message['function_call']['name']
            if func_name in globals():
                func = globals()[func_name]
                args = json.loads(response_message['function_call']['arguments'])
                print(f'----- Calling {func_name}({args}) -----')
                result = func(**args)
                conversation_messages.append(response_message)
                conversation_messages.append(
                    {
                        'role': 'function',
                        'name': func_name,
                        'content': result
                    }
                )

                second_response = await openai.ChatCompletion.acreate(model='gpt-4', messages=conversation_messages)
                second_response_message = second_response['choices'][0]['message']
                print(second_response_message['content'])
                conversation_messages.append(second_response_message)
        else:
            print(response_message['content'])
            conversation_messages.append(response_message)


if __name__ == '__main__':
    asyncio.run(main())
