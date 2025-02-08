---
Title: Spec Generation
---


The master agent will generate a spec file that will be used to generate the code. Throughout the project, the spec file will be updated with user flow, and be always validated by the verification tools.

The master agent creates the following spec files:

1. `frontend_spec.json`
```
{
    "name": "frontend",
    "description": "The frontend spec",
    "components/pages": [
        {
            "name": "page",
            "description": "The page spec",
            "components": []
        }
    ],
    "dependencies": [],
    "package.json details": {}
}
```

2. `backend_serving_spec.json`
This is the OpenAPI spec that is either implemented in the nextjs logic as `/api` or in the backend with fastapi code.
```

Here are more details:
![Spec Generation Flow](/images/spec-jay.png)
