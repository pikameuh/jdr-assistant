"""Réponses factices de l'API OpenAI Responses, construites avec les vrais types du SDK."""

from openai.types.responses import (
    Response,
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputRefusal,
    ResponseOutputText,
    ResponseReasoningItem,
)
from openai.types.responses.response import IncompleteDetails


def reponse(*elements, status="completed", raison=None):
    return Response.model_construct(
        id="resp_test",
        status=status,
        output=list(elements),
        incomplete_details=IncompleteDetails.model_construct(reason=raison) if raison else None,
        error=None,
    )


def message(texte):
    return ResponseOutputMessage.model_construct(
        id="msg_test",
        type="message",
        role="assistant",
        status="completed",
        content=[ResponseOutputText.model_construct(type="output_text", text=texte, annotations=[])],
    )


def refus(texte="Je ne peux pas."):
    return ResponseOutputMessage.model_construct(
        id="msg_refus",
        type="message",
        role="assistant",
        status="completed",
        content=[ResponseOutputRefusal.model_construct(type="refusal", refusal=texte)],
    )


def appel(call_id, arguments, name="rechercher_regle"):
    return ResponseFunctionToolCall.model_construct(
        id=f"fc_{call_id}", type="function_call", call_id=call_id, name=name, arguments=arguments
    )


def raisonnement():
    return ResponseReasoningItem.model_construct(id="rs_test", type="reasoning", summary=[])
