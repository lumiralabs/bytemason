from lumos import lumos
from models import Intent


class MasterAgent:
    def __init__(self):
        pass

    def understand_intent(self, user_input: str) -> Intent:
        """
        Understand the user's intent from the user's input, and returns a more detailed intent with features, components, etc.
        """
        intent = lumos.call_ai(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that understands the user's intent from the user's input, and returns a more detailed intent with features, components, etc.",
                },
                {"role": "user", "content": user_input},
            ],
            response_format=Intent,
            model="gpt-4o-mini",
        )
        return intent

    def verify_with_user_loop(self, intent: Intent, max_attempts=3) -> Intent:
        """
        Verify the intent with the user, iterate with feedback and returns the final intent
        """
        return intent

    def create_spec(self, intent):
        """
        Create each individual spec from the intent, and then combine them into a single spec
        """
        # create each individual spec
        # openapi_spec = self.create_openapi_spec(intent)
        # frontend_spec = self.create_frontend_spec(intent)
        # backend_serving_spec = self.create_backend_serving_spec(intent)
        # supabase_spec = self.create_supabase_spec(intent)
        pass
