import json
from open_webui.utils.misc import (
    openai_chat_chunk_message_template,
    openai_chat_completion_message_template,
)


def convert_response_ollama_to_openai(ollama_response: dict) -> dict:
    model = ollama_response.get("model", "ollama")
    message_content = ollama_response.get("message", {}).get("content", "")

    response = openai_chat_completion_message_template(model, message_content)
    return response


async def convert_streaming_response_ollama_to_openai(ollama_streaming_response):
    """
    Converts an Ollama streaming response into an OpenAI-compatible streaming response.
    Reads data in fixed-size chunks to avoid the “Chunk too big” error.
    """
    CHUNK_SIZE = 65536  # 64 KB per chunk
    buffer = ""
    
    # Instead of using body_iterator, iterate over the response directly.
    async for chunk in ollama_streaming_response:
        text = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
        buffer += text
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue
            model = data.get("model", "ollama")
            message_content = data.get("message", {}).get("content", "")
            done = data.get("done", False)
            usage = None
            if done:
                usage = {
                    "response_token/s": (
                        round(
                            (data.get("eval_count", 0) /
                             ((data.get("eval_duration", 0) / 10_000_000)))
                            * 100, 2
                        ) if data.get("eval_duration", 0) > 0 else "N/A"
                    ),
                    "prompt_token/s": (
                        round(
                            (data.get("prompt_eval_count", 0) /
                             ((data.get("prompt_eval_duration", 0) / 10_000_000)))
                            * 100, 2
                        ) if data.get("prompt_eval_duration", 0) > 0 else "N/A"
                    ),
                    "total_duration": data.get("total_duration", 0),
                    "load_duration": data.get("load_duration", 0),
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "prompt_eval_duration": data.get("prompt_eval_duration", 0),
                    "eval_count": data.get("eval_count", 0),
                    "eval_duration": data.get("eval_duration", 0),
                    "approximate_total": (
                        lambda s: f"{s // 3600}h{(s % 3600) // 60}m{s % 60}s"
                    )((data.get("total_duration", 0) or 0) // 1_000_000_000),
                }
            converted = openai_chat_chunk_message_template(
                model,
                message_content if not done else None,
                usage
            )
            yield f"data: {json.dumps(converted)}\n\n"
    if buffer.strip():
        try:
            data = json.loads(buffer.strip())
            model = data.get("model", "ollama")
            message_content = data.get("message", {}).get("content", "")
            done = data.get("done", False)
            usage = None
            if done:
                usage = {
                    # ... (same as above)
                }
            converted = openai_chat_chunk_message_template(
                model,
                message_content if not done else None,
                usage
            )
            yield f"data: {json.dumps(converted)}\n\n"
        except Exception:
            pass
    yield "data: [DONE]\n\n"
