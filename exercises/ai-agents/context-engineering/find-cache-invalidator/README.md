Este código deveria aproveitar o cache, mas `cache_read_input_tokens` volta sempre zero.

```python
def build_system(manual, user_profile):
    return [
        {
            "type": "text",
            "text": f"{manual}\n\nPerfil: {json.dumps(user_profile)}",
            "cache_control": {"type": "ephemeral"},
        }
    ]
```

O `manual` é o mesmo sempre, e o `user_profile` é o mesmo dicionário. Corrija `build_system` para que o prefixo fique estável entre chamadas.

Mantenha o perfil no prompt: ele precisa estar lá.
