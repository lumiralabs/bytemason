from lumos import lumos
from blueberry.models import Intent
import httpx


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


class TestAgent:
    def __init__(self, spec):
        self.spec = spec

    def backend_serving_test(self):
        """
        Hits each endpoint in the backend serving spec, and verifies everything works as expected
        """

        # create a test client
        # hit each endpoint
        # verify the response
        # return the results
        client = httpx.Client()
        for endpoint in self.spec.endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            assert response.json() == {"message": "Hello, World!"}
        pass


# class Sandbox(BaseModel):
#     filesystem: Any
#     terminal: Any
#     code_editor: Any


#     def execute(self, code_input: str):
#         """
#         Executes the code commands in the terminal and returns the output
#         """
#         pass


class RepairAgent:
    def __init__(self, spec):
        self.spec = spec

    def repair(self, terminal_output: str, code_input: str):
        """
        Repairs the code based on the outputs of the terminal results
        """
        pass
