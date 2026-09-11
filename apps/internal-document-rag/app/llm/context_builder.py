from collections.abc import Sequence

from app.llm.exceptions import EmptyContextError
from app.models.schemas import DocumentChunk


class ContextBuilder:
    """Formats retrieved document chunks into a single consistent context string."""

    @staticmethod
    def build_context(retrieved_chunks: Sequence[DocumentChunk]) -> str:
        """
        Convert a list of DocumentChunks into a formatted string.
        Raises EmptyContextError if there are no chunks or they are all empty.
        """
        if not retrieved_chunks:
            raise EmptyContextError(
                "Retrieved context must contain at least one chunk."
            )

        if any(not str(chunk.content).strip() for chunk in retrieved_chunks):
            raise EmptyContextError("Retrieved chunks must contain non-empty content.")

        context_blocks = []
        for index, item in enumerate(retrieved_chunks, start=1):
            chunk = item[0] if isinstance(item, (list, tuple)) else item
            metadata = getattr(chunk, "metadata", None)
            ctype = getattr(metadata, "chunk_type", "text") if metadata else "text"
            chunk_type_label = str(getattr(ctype, "value", ctype))
            type_tag = f"[{chunk_type_label.upper()}]"
            source_file = (
                getattr(metadata, "source_file", "unknown") if metadata else "unknown"
            )
            page_number = getattr(metadata, "page_number", 1) if metadata else 1
            content_str = str(getattr(chunk, "content", chunk))

            context_blocks.append(
                "\n".join(
                    [
                        f"[Context {index}] {type_tag}",
                        f"Source: {source_file}",
                        f"Page: {page_number}",
                        content_str,
                    ]
                )
            )

        return "\n\n".join(context_blocks)
