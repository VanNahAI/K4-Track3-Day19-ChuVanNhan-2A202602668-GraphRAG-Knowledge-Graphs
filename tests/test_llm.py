import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.llm import MeteredLLM, pick_provider


class OllamaCloudTests(unittest.TestCase):
    def test_cloud_chat_keeps_embeddings_separate(self):
        chat = Mock()
        chat.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )
        embed = Mock()
        env = {"OLLAMA_API_KEY": "test-ollama", "OPENAI_API_KEY": "test-openai"}
        with patch.dict(os.environ, env, clear=True), patch("openai.OpenAI", side_effect=[chat, embed]) as client:
            self.assertEqual(pick_provider("LLM_PROVIDER", False), "ollama")
            self.assertEqual(pick_provider("EMBEDDING_PROVIDER", True), "openai")
            llm = MeteredLLM()
            self.assertEqual(llm.chat("Return JSON", json_mode=True), '{"ok": true}')
            self.assertEqual(client.call_args_list[0].kwargs,
                             {"api_key": "test-ollama", "base_url": "https://ollama.com/v1"})
            self.assertIs(llm._embed_client, embed)
            self.assertEqual(llm.embed_model_id, "text-embedding-3-small")
            chat.chat.completions.create.assert_called_once_with(
                model="gpt-oss:120b", messages=[{"role": "user", "content": "Return JSON"}],
                temperature=0, response_format={"type": "json_object"},
            )
            self.assertEqual(llm.usage.input_tokens, 10)
            self.assertEqual(llm.usage.output_tokens, 5)
            self.assertEqual(llm.usage.usd, 0)

    def test_cloud_is_not_an_embedding_provider(self):
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "ollama", "OLLAMA_API_KEY": "test"}, clear=True):
            with self.assertRaises(RuntimeError):
                pick_provider("EMBEDDING_PROVIDER", True)

    def test_existing_openai_selection_is_unchanged(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=True):
            self.assertEqual(pick_provider("LLM_PROVIDER", False), "openai")


if __name__ == "__main__":
    unittest.main()
