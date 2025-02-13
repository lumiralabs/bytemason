# Code Generation from Scaffold and Specification

## Base Structure

```json
{
  "name": "boilerplate",
  "type": "next.js",
  "version": "1.0.0",
  "description": "Full-stack Next.js boilerplate with Supabase authentication, dashboard, and modern UI components",
  "structure": {
    "root": {
      "app": {
        "description": "Next.js app directory for routing and pages",
        "contents": {
          "api": {
            "type": "directory",
            "description": "API route handlers",
            "pattern": "Route handlers follow Next.js App Router conventions with route.ts files"
          },
          "dashboard": {
            "type": "directory",
            "description": "Dashboard pages and components",
            "contents": {
              "layout.tsx": {
                "type": "file",
                "description": "Dashboard layout with authentication protection",
                "features": [
                  "Protected routes",
                  "Navigation layout",
                  "User session handling"
                ]
              },
              "page.tsx": {
                "type": "file",
                "description": "Main dashboard page",
                "features": ["User data display", "Dashboard widgets"]
              }
            }
          }
        }
      },
      "components": {
        "description": "Reusable UI components",
        "contents": {
          "ui": {
            "type": "directory",
            "description": "UI component library",
            "styling": "Tailwind CSS with shadcn/ui components",
            "contents": {
              "button.tsx": "Styled button component",
              "input.tsx": "Form input component",
              "card.tsx": "Card container component",
              "dialog.tsx": "Modal dialog component"
            }
          }
        }
      }
    }
  }
}
```

## Project Specification

[DYNAMIC_SPECIFICATION]

## Implementation Requirements

1. Follow the scaffold's patterns and conventions while implementing the specification:

   - Use existing components and utilities
   - Follow the established file structure
   - Maintain consistent naming conventions
   - Utilize provided helper functions

2. Implement each section of the specification:

   - Create pages based on frontendStructure.pages
   - Implement components from frontendStructure.components
   - Set up API routes from apiRoutes
   - Configure database tables from supabaseConfig
   - Add all features from features.category

3. Ensure proper integration:

   - Authentication flows match scaffold's patterns
   - State management follows scaffold's approach
   - Error handling is consistent
   - Type safety is maintained

4. Quality Requirements:
   - All acceptance criteria must be met
   - Code must follow scaffold's patterns
   - Security measures must be implemented
   - Performance optimizations should be applied
   - Documentation must be updated

## Implementation Order

1. Project setup and configuration
2. Database schema and migrations
3. Authentication implementation
4. API routes and middleware
5. Frontend components and pages
6. Feature implementation
7. Testing and validation
