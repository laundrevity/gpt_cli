import subprocess
import asyncio
import openai
import json
import os
openai.api_key = os.getenv('OPENAI_API_KEY')

def execute_linux_commands(commands_json):

    commands = json.loads(commands_json)

    result_str = ''
    for command_json in commands:
        command = command_json['command']
        args = command_json.get('args', [])
        redirect_out = None
        
        if '>' in args:  # detect redirection
            redirect_index = args.index('>')
            redirect_out = args[redirect_index + 1]  # get output file 
            args = args[:redirect_index]  # remove '>' symbols 

        try:
            if redirect_out:
                with open(redirect_out, 'w') as fp:
                    result = subprocess.run([command] + args, stdout=fp)
                msg = f'REDIRECTED_TO_FILE: {redirect_out}\n' 
            else:
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

        result_str += msg + '\n'

    return result_str.strip()

FUNCTIONS = [
    {
        'name': 'execute_linux_commands',
        'description': 'execute list of Linux commands and return stdout for each',
        'parameters': {
            'type': 'object',
            'properties': {
                'commands_json': {
                    'type': 'string',
                    'description': 'stringified JSON of list of commands to execute. each element of the list needs a string attribute `command` and optional attribute `args` which is a list of arguments. Redirection should be an argument by itself'
                },
            }
        },
        'required': ['commands_json']
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
