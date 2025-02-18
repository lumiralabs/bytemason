## 1. List of Existing Files and Their Purposes

- **Root Files:**
  - `config.ts`: Likely contains configuration settings for the application.
  - `middleware.ts`: Contains middleware logic, possibly for handling requests or authentication.
  - `next-env.d.ts`: TypeScript environment definitions for Next.js.
  - `next.config.js`: Configuration file for Next.js, used to customize the build process.
  - `postcss.config.js`: Configuration for PostCSS, a tool for transforming CSS.
  - `tailwind.config.js`: Configuration for Tailwind CSS, a utility-first CSS framework.
- **Components Directory:**
  - `ButtonAccount.tsx`: A React component, likely a button related to user account actions.
  - `ButtonSignin.tsx`: A React component, likely a button for signing in.
  - `LayoutClient.tsx`: A React component, possibly defining the layout for client-side pages.
- **Libs Directory:**
  - `api.ts`: Contains API-related logic or functions.
  - `seo.tsx`: Contains SEO-related components or logic.
- **Types Directory:**
  - `config.ts`: Type definitions related to configuration.
  - `index.ts`: Central export file for types.
  - `next-auth.d.ts`: Type definitions related to authentication, possibly using NextAuth.js.
- **App Directory:**
  - `layout.tsx`: Defines the layout for the application, likely used by Next.js.
  - `page.tsx`: The main page component for the application.
- **Lib Directory:**
  - `utils.ts`: Utility functions used across the application.

### 2. Component Patterns and Their Usage

The components are organized in a `components` directory, with specific components like buttons and layout components. This suggests a pattern of reusable UI components, which is common in React applications to promote reusability and maintainability.

### 3. Current Routing Implementation

The `app` directory structure suggests the use of Next.js's App Router, where each subdirectory or file represents a route. For example, `app/dashboard` and `app/signin` likely correspond to `/dashboard` and `/signin` routes, respectively.

### 4. Authentication Setup

The presence of `next-auth.d.ts` in the `types` directory suggests the use of NextAuth.js for authentication. Additionally, `middleware.ts` might be used to handle authentication-related middleware logic.

### 5. Database Integration Details

The `libs/supabase` subdirectory suggests the use of Supabase, a backend-as-a-service platform, for database integration. This directory likely contains logic for interacting with Supabase's database services.

# Best practices for Next.js (v14)frontend development

STRICTLY FOLLOW THESE GUIDELINES. DO NOT USE ANY OTHER OLD PATTERNS.

## Project Structure

Use the App Router pattern instead of the Pages Router for better organization and features:

- Place all routes under `app/` directory instead of `pages/`
- Create route segments using folders (e.g. `app/dashboard/settings/`)
- Use `page.tsx` files to make routes publicly accessible
- Use `layout.tsx` for shared UI between routes
- Place route-specific components in the route folder
- Keep shared components in `components/`
- Use `loading.tsx` for suspense boundaries
- Use `error.tsx` for error handling
- Place API routes under `app/api/`

## Project Structure DOs and DON'Ts

✅ DO:
├── app/
│ ├── (auth)/ # Auth group routes
│ │ ├── login/
│ │ │ └── page.tsx
│ │ └── register/
│ │ └── page.tsx
│ ├── dashboard/ # Dashboard routes
│ │ ├── page.tsx
│ │ ├── layout.tsx
│ │ └── settings/
│ │ └── page.tsx
│ ├── api/ # API routes
│ │ └── users/
│ │ └── route.ts
│ ├── layout.tsx # Root layout
│ └── page.tsx # Home page
└── components/ # Shared components
├── Button.tsx
└── Header.tsx

❌ DON'T:
└── pages/ # Don't use Pages Router
├── \_app.tsx
├── index.tsx
├── login.tsx
├── api/
│ └── users.ts
└── components/ # Don't mix components with pages
├── Button.tsx
└── Header.tsx
