def build_chat_prompt(user_query: str, retrieved_context: str) -> str:
    return (
        "You are a personal finance assistant.\n\n"
        "Answer the user's question using only the retrieved financial context provided below.\n\n"
        f"Context:\n{retrieved_context}\n\n"
        f"User Question:\n{user_query}\n\n"
        "Rules:\n"
        "1 Keep answers concise and fact-based.\n"
        "2 Quote relevant numbers directly from the context when possible.\n"
        "3 If the question asks for a summary, synthesize the retrieved chunks clearly.\n"
        "4 If the data is insufficient, say so explicitly.\n"
        "5 Do not invent merchants, dates, categories, or totals.\n"
        "6 Respond in plain text only.\n"
        "7 Do not use tables, markdown, bullet points, numbered lists, code blocks, or HTML.\n"
        "8 Use only normal sentences, short paragraphs, and numerals where needed.\n"
    )
