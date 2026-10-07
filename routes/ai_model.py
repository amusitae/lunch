from ollama import chat


def ask_ai(prompt):

    response = chat(
        model="qwen3:latest",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.message.content