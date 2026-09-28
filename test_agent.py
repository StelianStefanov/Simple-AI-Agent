import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from openai import APIConnectionError
from openai.types.chat import ChatCompletion

from agent_loop import agent_loop
from ai_api_call import AgentError, api_call
from call_function import call_function


def tool(name, arguments):
    return SimpleNamespace(id="call_1", function=SimpleNamespace(name=name, arguments=arguments))


def response(*, content="Done", calls=None, usage=True, reason="stop"):
    return ChatCompletion.model_validate({
        "id": "test", "created": 0, "model": "test", "object": "chat.completion",
        "choices": [{"index": 0, "finish_reason": reason, "message": {
            "role": "assistant", "content": content, "tool_calls": calls,
        }}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15} if usage else None,
    })


class DispatchTests(unittest.TestCase):
    def test_invalid_calls_return_errors(self):
        for name, args in (
            ("function_name", "{}"), ("unknown", "{}"), ("write_file", "{"),
            ("write_file", "[]"), ("write_file", "null"), ("write_file", "{}"),
            ("get_file_content", '{"file_path": 1}'),
            ("get_file_content", '{"file_path":"file", "working_directory":"/"}'),
            ("run_python_file", '{"file_path":"file.py", "args":[1]}'),
        ):
            with self.subTest(name=name, args=args):
                result = call_function(tool(name, args))
                self.assertEqual(result["tool_call_id"], "call_1")
                self.assertTrue(result["content"].startswith("Error:"))

    def test_workspace_is_independent_of_current_directory(self):
        with tempfile.TemporaryDirectory() as root, patch("call_function.WORKING_DIRECTORY", Path(root)):
            (Path(root) / "file").write_text("hello")
            with contextlib.chdir("/"):
                result = call_function(tool("get_file_content", '{"file_path":"file"}'))
            self.assertEqual(result["content"], "hello")

    def test_arguments_and_results_are_not_logged(self):
        with tempfile.TemporaryDirectory() as root, patch("call_function.WORKING_DIRECTORY", Path(root)):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                call_function(tool("write_file", json.dumps({"file_path": "file", "content": "secret-content"})), verbose=True)
            self.assertNotIn("secret-content", output.getvalue())
            self.assertEqual(output.getvalue().count("Calling tool"), 1)


class ResponseTests(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.messages = [{"role": "user", "content": "hello"}]

    def test_final_response_and_missing_usage(self):
        self.client.chat.completions.create.return_value = response(usage=False)
        with contextlib.redirect_stdout(io.StringIO()):
            result = api_call(self.client, self.messages, verbose=True)
        self.assertTrue(result.finished)
        self.assertEqual(result.text, "Done")
        self.assertGreater(result.tokens_used, 0)

    def test_empty_and_incomplete_responses_stop(self):
        for content, reason in ((None, "stop"), ("", "stop"), ("partial", "length"), (None, "content_filter")):
            with self.subTest(content=content, reason=reason):
                self.client.chat.completions.create.return_value = response(content=content, reason=reason)
                with self.assertRaises(AgentError):
                    api_call(self.client, self.messages)
        empty = response()
        empty.choices = []
        self.client.chat.completions.create.return_value = empty
        with self.assertRaises(AgentError):
            api_call(self.client, self.messages)

    def test_budget_prevents_api_request(self):
        with self.assertRaises(AgentError):
            api_call(self.client, self.messages, remaining_tokens=1)
        with patch("ai_api_call.MAX_HISTORY_CHARS", 1), self.assertRaises(AgentError):
            api_call(self.client, self.messages)
        self.client.chat.completions.create.assert_not_called()

    def test_tool_error_preserves_protocol_and_allows_next_turn(self):
        self.client.chat.completions.create.return_value = response(content=None, reason="tool_calls", calls=[{
            "id": "call_1", "type": "function", "function": {"name": "get_file_content", "arguments": "{"},
        }])
        result = api_call(self.client, self.messages)
        self.assertFalse(result.finished)
        self.assertEqual(self.messages[-1]["tool_call_id"], "call_1")
        self.assertTrue(self.messages[-1]["content"].startswith("Error:"))
        self.client.chat.completions.create.return_value = response()
        self.assertTrue(api_call(self.client, self.messages).finished)

    def test_excessive_tool_calls_do_not_execute(self):
        calls = [{"id": f"call_{i}", "type": "function", "function": {"name": "get_files_info", "arguments": "{}"}} for i in range(9)]
        self.client.chat.completions.create.return_value = response(content=None, reason="tool_calls", calls=calls)
        with patch("ai_api_call.call_function") as dispatch, self.assertRaises(AgentError):
            api_call(self.client, self.messages)
        dispatch.assert_not_called()

    def test_loop_reports_api_failure_without_sensitive_details(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())
        output = io.StringIO()
        with patch("agent_loop.create_client", return_value=client), contextlib.redirect_stderr(output):
            self.assertEqual(agent_loop(["hello"]), 1)
        self.assertIn("APIConnectionError", output.getvalue())

    def test_loop_returns_final_text(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.chat.completions.create.return_value = response()
        output = io.StringIO()
        with patch("agent_loop.create_client", return_value=client), contextlib.redirect_stdout(output):
            self.assertEqual(agent_loop(["hello"]), 0)
        self.assertEqual(output.getvalue(), "Done\n")


if __name__ == "__main__":
    unittest.main()
