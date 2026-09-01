from unittest.mock import MagicMock, patch

from app.services.llm_service import LLMService


@patch("app.services.llm_service.Groq")
def test_llm_service_initializes(mock_groq):
    service = LLMService()

    assert service.model == "openai/gpt-oss-120b"
    mock_groq.assert_called_once()


@patch("app.services.llm_service.Groq")
def test_llm_service_generate(mock_groq):
    mock_client = MagicMock()

    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "I can offer you a better price."
    )

    mock_client.chat.completions.create.return_value = (
        mock_response
    )

    mock_groq.return_value = mock_client

    service = LLMService()

    result = service.generate(
        system_prompt="You are a negotiation agent.",
        user_prompt="Respond to this buyer.",
    )

    assert result == "I can offer you a better price."

    mock_client.chat.completions.create.assert_called_once()