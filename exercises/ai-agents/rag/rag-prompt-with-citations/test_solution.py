from solution import build_rag_prompt

CHUNKS = [("manual.md", "O prazo é de 30 dias."), ("faq.md", "A garantia cobre defeitos.")]
INSTRUCTION = (
    "Responda apenas com base nas fontes acima. Cite a fonte usada no formato [N]. "
    "Se as fontes não responderem, diga que não há informação suficiente."
)


def test_sources_are_numbered_from_one():
    prompt = build_rag_prompt("Qual o prazo?", CHUNKS)
    assert "[1] manual.md: O prazo é de 30 dias." in prompt
    assert "[2] faq.md: A garantia cobre defeitos." in prompt


def test_prompt_structure_and_order():
    prompt = build_rag_prompt("Qual o prazo?", CHUNKS)
    lines = prompt.split("\n")
    assert lines[0] == "Fontes:"
    assert lines[3] == ""
    assert lines[4] == INSTRUCTION
    assert lines[-1] == "Pergunta: Qual o prazo?"


def test_question_comes_after_the_sources():
    prompt = build_rag_prompt("Qual o prazo?", CHUNKS)
    assert prompt.index("Fontes:") < prompt.index("Pergunta:")


def test_no_chunks():
    assert build_rag_prompt("Qual o prazo?", []) == "Não há fontes disponíveis para responder."
