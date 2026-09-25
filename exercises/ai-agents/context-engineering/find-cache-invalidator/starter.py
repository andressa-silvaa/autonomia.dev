import json


def build_system(manual, user_profile):
    return [
        {
            "type": "text",
            "text": f"{manual}\n\nPerfil: {json.dumps(user_profile)}",
            "cache_control": {"type": "ephemeral"},
        }
    ]
