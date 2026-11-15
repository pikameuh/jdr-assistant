"""Fixtures partagées : messages de l'API Anthropic factices (vrais types du SDK)."""

import pytest
from anthropic.types import CitationCharLocation, Message, TextBlock, ThinkingBlock, Usage


def _citation(document_index, cited_text, titre="Doc"):
    return CitationCharLocation(
        type="char_location",
        cited_text=cited_text,
        document_index=document_index,
        document_title=titre,
        start_char_index=0,
        end_char_index=len(cited_text),
    )


def _message(blocs, stop_reason="end_turn"):
    """`blocs` : liste de (texte, [(document_index, texte_cité), ...]) ou chaîne seule."""
    content = [ThinkingBlock(type="thinking", thinking="", signature="sig")]
    for bloc in blocs:
        texte, citations = (bloc, []) if isinstance(bloc, str) else bloc
        content.append(
            TextBlock(
                type="text",
                text=texte,
                citations=[_citation(i, t) for i, t in citations] or None,
            )
        )
    return Message(
        id="msg_test",
        type="message",
        role="assistant",
        model="claude-opus-4-8",
        content=content,
        stop_reason=stop_reason,
        stop_sequence=None,
        usage=Usage(input_tokens=1, output_tokens=1),
    )


@pytest.fixture
def message_factice():
    return _message
