---
title: Base Scaffold
---

All our apps are built on top of a base scaffold. This ensures that all our apps are built on top of a consistent structure, and we can easily add new features to the base scaffold. The following files are pre-generated and edited by AI and the user on the go. We will be verifying that the code generated is always consistent with the base scaffold. Here is how to set up the base scaffold that just works:

```bash
blueberry base
```
that basically sets up 

1. package.json
 - remix 
2. supabase auth
 - google auth
 - github auth
3. secret `API_KEYS` management

and creates the following folder structure:
```
<name>
├── frontend/
│   ├── pages/...
│   ├── api/...
│   └── package.json
└── supabase/
    └── migration files
```

