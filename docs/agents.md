---
Title: Available Blueberry Agents
---

We have the following agents:

1. Master Agent
- understand intent
- creates spec

```python
from blueberry.agents import MasterAgent

master_agent = MasterAgent()
intent = master_agent.understand_intent("I want to create a new project")

# verify with user the intent
final_intent = master_agent.verify_with_user_loop(intent, max_attempts=3)

spec = master_agent.create_spec(final_intent)
```

2. 