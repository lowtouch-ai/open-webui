import json
import logging
from starlette.responses import StreamingResponse
from open_webui.utils.misc import (
    openai_chat_chunk_message_template,
    openai_chat_completion_message_template,
)

logger = logging.getLogger(__name__)

def convert_response_ollama_to_openai(ollama_response: dict) -> dict:
    """
    Non-streaming conversion:
    Convert a dict-based Ollama response into an OpenAI-compatible response.
    """
    model = ollama_response.get("model", "ollama")
    message_content = ollama_response.get("message", {}).get("content", "")
    return openai_chat_chunk_message_template(model, message_content)

async def convert_streaming_response_ollama_to_openai(ollama_streaming_response):
    """
    Converts an Ollama streaming response into an OpenAI-compatible streaming response
    in a line-based SSE format. Uses a fallback approach for "Chunk too big" errors so
    large images or data are not lost.

    Priority of iteration:
      1. content.iter_chunked() if available
      2. streaming_content if this is a StreamingResponse
      3. body_iterator
      4. Directly iterate over the response

    If we get ValueError("Chunk too big"), we preserve partial data in `buffer` and then
    collect the rest of the stream manually, processing it in smaller chunks. This way,
    the partial data is not lost, and the large payload is properly displayed.
    """
    CHUNK_SIZE = 65536  # 64 KB per chunk
    buffer = ""

    logger.debug("convert_streaming_response_ollama_to_openai: starting with CHUNK_SIZE=%d", CHUNK_SIZE)

    # 1) If response has content.iter_chunked()
    if hasattr(ollama_streaming_response, "content") and hasattr(ollama_streaming_response.content, "iter_chunked"):
        logger.debug("convert_streaming_response: using content.iter_chunked()")
        iterator = ollama_streaming_response.content.iter_chunked(CHUNK_SIZE)

    # 2) If response is a StreamingResponse with streaming_content
    elif isinstance(ollama_streaming_response, StreamingResponse) and hasattr(ollama_streaming_response, "streaming_content"):
        logger.debug("convert_streaming_response: using streaming_content from StreamingResponse")
        content_iter = ollama_streaming_response.streaming_content
        if callable(content_iter):
            content_iter = content_iter()
            logger.debug("convert_streaming_response: called streaming_content()")
        # If it's a synchronous iterator, wrap in async
        if not hasattr(content_iter, "__aiter__"):
            logger.debug("convert_streaming_response: wrapping sync streaming_content as async generator")
            async def async_gen(sync_iter):
                for item in sync_iter:
                    yield item
            iterator = async_gen(content_iter)
        else:
            iterator = content_iter

    # 3) Else if body_iterator is available
    elif hasattr(ollama_streaming_response, "body_iterator"):
        logger.debug("convert_streaming_response: using body_iterator (may trigger readuntil())")
        iterator = ollama_streaming_response.body_iterator

    # 4) Otherwise, iterate the response directly
    else:
        logger.debug("convert_streaming_response: using response directly as iterator")
        iterator = ollama_streaming_response

    try:
        # Normal iteration
        async for chunk in iterator:
            # Convert chunk to text
            if isinstance(chunk, bytes):
                chunk_size = len(chunk)
                text = chunk.decode("utf-8", errors="ignore")
            else:
                chunk_size = len(chunk.encode("utf-8", errors="ignore"))
                text = chunk

            logger.debug("convert_streaming_response: received chunk of size %d", chunk_size)
            buffer += text
            logger.debug("convert_streaming_response: buffer length now %d", len(buffer))

            # Process complete lines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                for output_line in _process_line(line):
                    yield output_line

    except ValueError as e:
        # If line-based reading hits "Chunk too big", fallback
        if str(e) == "Chunk too big":
            logger.warning("Caught 'Chunk too big'. Attempting fallback with partial data.")
            # partial_data -> what we already have in buffer
            partial_data = buffer.encode("utf-8", errors="ignore")
            buffer = ""
            all_chunks = [partial_data]  # preserve partial data we had

            try:
                # gather the rest from the same iterator
                async for chunk in iterator:
                    if isinstance(chunk, bytes):
                        all_chunks.append(chunk)
                    else:
                        all_chunks.append(chunk.encode("utf-8", errors="ignore"))

                full_body = b"".join(all_chunks)
                logger.debug("Fallback read: total size %d bytes", len(full_body))
                text = full_body.decode("utf-8", errors="ignore")

                # process text in CHUNK_SIZE slices
                for i in range(0, len(text), CHUNK_SIZE):
                    piece = text[i : i + CHUNK_SIZE]
                    buffer += piece
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        for output_line in _process_line(line):
                            yield output_line

            except Exception as ex:
                logger.exception("Fallback error reading all chunks: %s", ex)
                raise ex
    except aiohttp.ClientConnectionError as e:
        logger.warning("Remote side closed the connection unexpectedly: %s", e)
        # Optionally yield a final SSE line so the UI knows it ended abruptly:
        yield "data: [ERROR] Remote connection closed prematurely.\n\n"
        return
    # After the loop, if anything remains in buffer
    leftover = buffer.strip()
    if leftover:
        for output_line in _process_line(leftover):
            yield output_line

    logger.debug("convert_streaming_response: yielding final DONE signal.")
    yield "data: [DONE]\n\n"

def _process_line(line):
    """
    Parse a single line of JSON from Ollama, convert to
    an OpenAI chunk (SSE) format. This is a synchronous generator.
    """
    line = line.strip()
    if not line:
        return

    try:
        data = json.loads(line)
        logger.debug("_process_line: parsed JSON %s", data)
    except json.JSONDecodeError:
        logger.debug("_process_line: skipping invalid JSON line: %s", line)
        return

    model = data.get("model", "ollama")
    message_content = data.get("message", {}).get("content", "")
    done = data.get("done", False)

    usage = None
    if done:
        usage = {
            "response_token/s": (
                round(
                    (data.get("eval_count", 0) /
                     ((data.get("eval_duration", 0) / 10_000_000))) * 100, 2
                )
                if data.get("eval_duration", 0) > 0 else "N/A"
            ),
            "prompt_token/s": (
                round(
                    (data.get("prompt_eval_count", 0) /
                     ((data.get("prompt_eval_duration", 0) / 10_000_000))) * 100, 2
                )
                if data.get("prompt_eval_duration", 0) > 0 else "N/A"
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
        logger.debug("_process_line: usage: %s", usage)

    # Convert to OpenAI SSE chunk
    converted = openai_chat_chunk_message_template(
        model,
        message_content if not done else None,
        usage
    )
    output_line = f"data: {json.dumps(converted)}\n\n"
    logger.debug("_process_line: yielding: %s", output_line.strip())
    yield output_line
