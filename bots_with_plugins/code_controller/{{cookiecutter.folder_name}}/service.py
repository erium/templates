import asyncio
from contextlib import redirect_stdout, redirect_stderr
from flask import Flask, request, jsonify
import io
from ipykernel.kernelapp import IPKernelApp
import os
import re
import shlex
import subprocess
from subprocess import PIPE, STDOUT
import time



app = Flask(__name__)


class MyIPKernelApp(IPKernelApp):
    def init_signal(self):
        pass


@app.route('/start_kernel', methods=['POST'])
def start_kernel():
    """
    Starts the IPython kernel.

    Returns:
        dict: A dictionary containing the result status of the request (success or error).
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        kernel = MyIPKernelApp.instance()
        kernel.initialize([])
        return jsonify({'success': 'Kernel started! '}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/stop_kernel', methods=['POST'])
def stop_kernel():
    """
    Stops the IPython kernel.

    Returns:
        tuple: A tuple containing the result of the request and the status code.
    """
    try:
        kernel = IPKernelApp.instance()
        kernel.close()
        return jsonify({'success': 'Kernel stopped! '}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/execute_kernel_command', methods=['POST'])
def execute_kernel_command():
    """
    Executes a command in a running IPython kernel. Always include a return statement in your code!

    Args:
        command (str): the shell command that should be run in the IPython Kernel (e.g.: ls)

    Returns:
        tuple: A tuple containing the result of the command and the status code.
    """

    # Initialize buffers for capturing stdout and stderr
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    try:
        # Parse the JSON data from the request
        data = request.get_json()
        # Check if 'command' is present and not empty
        if 'command' in data and data['command']:
            command = data['command']
            kernel = IPKernelApp.instance()
            if kernel.shell is None:
                return jsonify({'error': f'kernel has to be started first!'})

            # Redirect stdout and stderr to the buffers
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                # Execute the command
                result = kernel.shell.run_cell(command)

                # Check for errors and write them to the stderr buffer
                if not result.success:
                    if result.error_before_exec is not None:
                        print(str(result.error_before_exec), file=stderr_buffer)
                    if result.error_in_exec is not None:
                        print(str(result.error_in_exec), file=stderr_buffer)

                # If execution was successful and there is a result, write it to stdout buffer
                if result.result and result.success:
                    print(str(result.result), file=stdout_buffer)

            # Extract the contents of the buffers
            stdout = stdout_buffer.getvalue()
            stderr = stderr_buffer.getvalue()

            # Return the appropriate response
            return jsonify({'status': f'{"success" if result.success else "failed"}',
                            'output': stdout if not stderr else stderr}), 200
        else:
            # If 'command' is not provided in the request
            return jsonify({'error': 'No command provided'}), 400
    except Exception as e:
        # Catch and report any unexpected errors during execution
        return jsonify({'error': str(e)}), 500


@app.route('/alive', methods=['POST'])
def alive():
    """
    Returns a simple "Hello World!" message to see if the service is running.

    Returns:
        tuple: A tuple containing the message and the status code.
    """
    return 'Hello World!', 200


@app.route('/execute_command', methods=['POST'])
def execute_command():
    """
    Executes a command in the shell (i.e. bash).

    Args:
        command (str): the shell command, for example ls -lach or wget -b http://example.com/beefy-file.tar.gz

    Returns:
        tuple: A tuple containing the result of the command and the status code.
    """
    try:
        # Parse the JSON data from the request
        data = request.get_json()
        if 'command' in data:
            command = shlex.split(data['command'])

            # open subprocess and pipe stdout and stderr
            with subprocess.Popen(command, stdout=PIPE, stderr=PIPE) as proc:
                stdout, stderr = proc.communicate()
                exit_code = proc.returncode

                if exit_code != 0:
                    output = 'ERROR: ' + stderr.decode() + '\nEXIT CODE: ' + str(exit_code)
                else:
                    output = "Success: " + stdout.decode()

            return jsonify({'output': output}), 200
        else:
            return jsonify({'error': 'No command provided'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/pip_install', methods=['POST'])
def pip_install():
    """
    Installs python packages via pip (package installer for python).

    Args:
        package (str): The python package, module or library that should be installed

    Returns:
        tuple: A tuple containing the result of the command and the status code.
    """
    try:
        data = request.get_json()
        if 'package' in data:
            package = data['package']
            #command = f"pip install -q {package}"
            command = ["pip", "install", "-q", package]

            # open subprocess and pipe stdout and stderr
            with subprocess.Popen(command, stdout=PIPE, stderr=PIPE) as proc:
                stdout, stderr = proc.communicate()
                exit_code = proc.returncode

                if exit_code != 0:
                    output = 'ERROR: ' + stderr.decode() + '\nEXIT CODE: ' + str(exit_code)
                else:
                    output = stdout.decode()

            return jsonify({'output': output}), 200
        else:
            return jsonify({'error': 'No package name provided'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/apt_get_install', methods=['POST'])
def apt_get_install():
    """
    Downloads and installs software via the advanced package tool.
    This CANNOT be used for python packages. Use pip instead.

    Args:
        package (str): the package that should be installed. 

    Returns:
        tuple: A tuple containing the result of the command and the status code.
    """
    try:
        # Parse the JSON data from the request
        data = request.get_json()
        if 'package' in data:

            # apt-get update
            update = ['sudo', 'apt-get', 'update']
            with subprocess.Popen(update, stdout=PIPE, stderr=PIPE) as update_proc:
                update_stdout, update_stderr = update_proc.communicate()
                update_exit_code = update_proc.returncode

                if update_exit_code != 0:
                    update_output = 'ERROR: ' + update_stderr.decode() + '\nEXIT CODE: ' + str(update_exit_code)

                    return jsonify({'apt-get update error': update_output}), 200

            
            # apt-get install
            package = data['package']
            command = ['sudo', 'apt-get', 'install', '-y', package]
            with subprocess.Popen(command, stdout=PIPE, stderr=PIPE) as proc:
                stdout, stderr = proc.communicate()
                exit_code = proc.returncode

                if exit_code != 0:
                    output = 'ERROR: ' + stderr.decode() + '\nEXIT CODE: ' + str(exit_code)
                else:
                    output = "Success: " + stdout.decode()

            return jsonify({'output': output}), 200
        else:
            return jsonify({'error': 'No command provided'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/write_to_file', methods=['POST'])
def write_to_file():
    """
    Creates a file and writes the given contents to it.

    Args:
        contents (any): the contents of the file (e.g. "Hey there! This will be a text file").
        filename (str): the filename of the file without the fileextension (e.g.: hello_world).
        filetype (str): the filetype of the file (e.g.: txt).

    Returns:
        tuple: A tuple containing the result of the command and the status code.
    """
    try:
        data = request.get_json()
        if 'contents' in data and 'filetype' in data and 'filename' in data:
            with open(f"{data['filename']}.{data['filetype']}", 'w') as f:
                f.write(data['contents'])
            return jsonify({'output': f'Successfully wrote contents to file {data["filename"]}.{data["filetype"]}!'}), 200
        else:
            return jsonify({'error': 'Missing parameters'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_apps_url', methods=['POST'])
def get_apps_url():
    """
    Returns the URL of Apps running from Halerium.

    Returns:
        tuple: A tuple containing the URL and the status code.
    """
    try:
        apps_url = f"{os.getenv('HALERIUM_BASE_URL')}/apps/{os.getenv('HALERIUM_ID')}/<your port between 8497 and 8499 (public) or 8501 and 8509 (private)>"
        return jsonify({'output': apps_url}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/start_streamlit_app', methods=['POST'])
def start_streamlit_app():
    """
    Starts a Streamlit app.

    Args:
        filename (str): the filename of the streamlit app (for example: "app.py").

    Returns:
        tuple: A tuple containing the result of the command and the status code.
    """
    try:
        # parse request
        data = request.get_json()
        if 'filename' in data:
            filename = data['filename']
            if os.path.exists(filename):

                # start streamlit process
                result = subprocess.Popen(["python", "-m" "streamlit", "run",
                                           filename], stderr=PIPE, text=True)

                time.sleep(3)  # let process startup

                # Check if the process has terminated
                if result.poll() is not None:
                    # read the stderr for any errors
                    stderr_output = result.stderr.read()
                    if stderr_output:
                        return jsonify({f"app startup error": stderr_output}), 200
                    else:
                        return jsonify({"app error": "Process terminated unexpectedly without error output."}), 200
                else:
                    port = 8501
                    runner_id = os.getenv('HALERIUM_ID')
                    base_url = os.getenv('HALERIUM_BASE_URL')
                    app_url = base_url + "/apps/" + runner_id + "/" + str(port)
                    return jsonify({'output': f'Streamlit app is running! You can use it at {app_url}'}), 200
            else:
                return jsonify({'error': f'File not found: {filename}.'}), 400
        else:
            return jsonify({'error': 'No filename provided'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8498)

